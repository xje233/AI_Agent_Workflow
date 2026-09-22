"""分层 Tool Routing：注册表卡片 → 确定性过滤 → 业务域粗分 → 混合检索 → 候选绑定。"""
from __future__ import annotations

import asyncio
import logging
import math
import time
from collections.abc import Collection, Sequence
from dataclasses import dataclass

from app.agent.tools import analyze_doc, query_db, run_python, search_tool, send_email
from app.config import get_settings
from app.rag.retriever import get_embeddings

logger = logging.getLogger(__name__)

ALL_TOOLS_REQUEST_KEYWORDS = ("所有工具", "全部工具", "所有功能", "全部功能")
CONFIRMATION_KEYWORDS = ("确认发送", "确认发邮件", "确认外发", "确认通知", "已确认发送")
FULL_ACCESS_SCOPES = frozenset({"*"})


@dataclass(frozen=True)
class ToolCard:
    """工具卡片：路由、风险过滤、检索索引和执行期鉴权共用的唯一注册信息。"""

    name: str
    tool: object
    namespace: str
    category: str
    risk: str
    read_only: bool
    requires_confirmation: bool
    required_scope: str
    environments: tuple[str, ...]
    when_to_use: str
    when_not_to_use: str
    tags: tuple[str, ...]
    keywords: tuple[str, ...]

    @property
    def index_text(self) -> str:
        """向量索引文本：名称、业务域、描述、标签、关键词与正向边界。"""
        return "\n".join(
            (
                self.namespace,
                self.name,
                self.category,
                self.tool.description or "",
                " ".join(self.tags),
                " ".join(self.keywords),
                self.when_to_use,
            )
        )


# environments 默认全量放开（dev/prod）：本仓库的 DEBUG 在本地同样是 false，不能当作生产判据，
# 按环境下线工具属于运营配置，改单张卡片的 environments 即可，判定逻辑在 filter_cards。
TOOL_CARDS: tuple[ToolCard, ...] = (
    ToolCard(
        name="search_tool",
        tool=search_tool,
        namespace="knowledge.search",
        category="knowledge",
        risk="low",
        read_only=True,
        requires_confirmation=False,
        required_scope="knowledge:read",
        environments=("dev", "prod"),
        when_to_use="需要企业制度、流程、规范等文档内容的语义检索时",
        when_not_to_use="需要统计数据库记录时改用 query_db；需要做数值计算时改用 run_python",
        tags=("知识库", "检索", "文档", "RAG", "只读"),
        keywords=("知识库", "资料", "搜索", "检索"),
    ),
    ToolCard(
        name="query_db",
        tool=query_db,
        namespace="data.query_readonly",
        category="data",
        risk="medium",
        read_only=True,
        requires_confirmation=False,
        required_scope="data:read",
        environments=("dev", "prod"),
        when_to_use="需要按白名单表统计或筛选会话、消息、文档记录时",
        when_not_to_use="需要文档内容时改用 search_tool；需要写入或删除数据时本工具只读",
        tags=("数据库", "SQL", "统计", "只读"),
        keywords=("sql", "数据库", "统计", "查询数据"),
    ),
    ToolCard(
        name="analyze_doc",
        tool=analyze_doc,
        namespace="document.inspect",
        category="document",
        risk="low",
        read_only=True,
        requires_confirmation=False,
        required_scope="document:read",
        environments=("dev", "prod"),
        when_to_use="已知具体文件名，需要结构化摘要、关键信息提取或风险项识别时",
        when_not_to_use="文件名未知、需要先在知识库中按语义查找时改用 search_tool",
        tags=("文档", "摘要", "风险分析", "只读"),
        keywords=("分析文档", "文档分析", "解读文件"),
    ),
    ToolCard(
        name="run_python",
        tool=run_python,
        namespace="compute.python_sandbox",
        category="compute",
        risk="medium",
        read_only=True,
        requires_confirmation=False,
        required_scope="compute:execute",
        environments=("dev", "prod"),
        when_to_use="需要数值计算、数据转换或格式处理时",
        when_not_to_use="需要查询数据库记录时改用 query_db；需要生成非 Python 代码时",
        tags=("计算", "脚本", "数据处理", "沙箱"),
        keywords=("python", "计算", "脚本", "运行代码"),
    ),
    ToolCard(
        name="send_email",
        tool=send_email,
        namespace="notification.send_email",
        category="notification",
        risk="high",
        read_only=False,
        requires_confirmation=True,
        required_scope="notification:send",
        environments=("dev", "prod"),
        when_to_use="用户明确要求把结果或通知外发给指定对象，且本轮已给出确认时",
        when_not_to_use="用户只是描述需求、未要求外发或未确认时；缺少收件人或正文时先追问",
        tags=("邮件", "通知", "外发", "副作用"),
        keywords=("邮件", "通知", "发送"),
    ),
)

CARDS_BY_NAME: dict[str, ToolCard] = {card.name: card for card in TOOL_CARDS}


@dataclass(frozen=True)
class RoutingContext:
    """本次请求的路由上下文：权限、环境、工具可用状态与高风险确认。"""

    scopes: frozenset[str] = FULL_ACCESS_SCOPES
    environment: str = "dev"
    unavailable_tools: frozenset[str] = frozenset()
    confirmed: bool = False


def active_environment() -> str:
    """运行环境：调试模式视为开发环境。"""
    return "dev" if get_settings().debug else "prod"


def has_confirmation(question: str) -> bool:
    """高风险操作的确认信号来自本轮用户消息。"""
    text = question.lower()
    return any(keyword in text for keyword in CONFIRMATION_KEYWORDS)


def scope_allowed(required: str, scopes: frozenset[str]) -> bool:
    return "*" in scopes or required in scopes


def filter_cards(
    cards: Sequence[ToolCard], context: RoutingContext
) -> tuple[list[ToolCard], list[dict[str, str]]]:
    """先鉴权再召回：返回 (允许暴露的卡片, 丢弃记录)。每张卡片只记录第一个命中的原因。"""
    allowed: list[ToolCard] = []
    dropped: list[dict[str, str]] = []
    for card in cards:
        if card.name in context.unavailable_tools:
            reason = "unavailable"
        elif context.environment not in card.environments:
            reason = "environment_mismatch"
        elif not scope_allowed(card.required_scope, context.scopes):
            reason = "missing_scope"
        elif card.requires_confirmation and not context.confirmed:
            reason = "requires_confirmation"
        else:
            allowed.append(card)
            continue
        dropped.append({"name": card.name, "reason": reason})
    return allowed, dropped


def classify_domains(question: str, cards: Sequence[ToolCard]) -> tuple[str, ...]:
    """规则层粗分：关键词或业务域命中即归入该域，多标签、偏召回、不判断风险。"""
    text = question.lower()
    matched = {
        card.category
        for card in cards
        if any(term in text for term in card.keywords) or card.category in text
    }
    return tuple(sorted(matched))


def _card_terms(card: ToolCard) -> frozenset[str]:
    return frozenset(term.lower() for term in (*card.keywords, *card.tags) if term)


_TERM_IDF: dict[str, float] = {}


def _build_term_idf() -> None:
    """在整张注册表上预计算 idf：sql / python 这类稀有词权重高，通用词权重低。"""
    document_count = len(TOOL_CARDS)
    frequencies: dict[str, int] = {}
    for card in TOOL_CARDS:
        for term in _card_terms(card):
            frequencies[term] = frequencies.get(term, 0) + 1
    _TERM_IDF.clear()
    _TERM_IDF.update(
        {
            term: math.log(1.0 + document_count / max(frequency, 1))
            for term, frequency in frequencies.items()
        }
    )


def lexical_scores(question: str, cards: Sequence[ToolCard]) -> dict[str, float]:
    """加权关键词匹配：命中卡片词表的 idf 之和。中文无需分词，直接子串匹配。"""
    text = question.lower()
    return {
        card.name: round(
            sum(_TERM_IDF.get(term, 0.0) for term in _card_terms(card) if term in text), 6
        )
        for card in cards
    }


_CARD_VECTORS: dict[str, list[float]] | None = None
_DENSE_DISABLED = False


def _ensure_card_vectors() -> dict[str, list[float]]:
    """惰性构建并缓存全部卡片向量；同步实现，调用方需移出事件循环。"""
    global _CARD_VECTORS
    if _CARD_VECTORS is None:
        vectors = get_embeddings().embed_documents([card.index_text for card in TOOL_CARDS])
        if len(vectors) != len(TOOL_CARDS):
            raise ValueError(f"embedding 返回 {len(vectors)} 条向量，期望 {len(TOOL_CARDS)} 条")
        _CARD_VECTORS = {
            card.name: list(vector) for card, vector in zip(TOOL_CARDS, vectors)
        }
    return _CARD_VECTORS


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """纯 Python 余弦相似度；维度不一致或存在零向量时返回 0.0。"""
    if len(left) != len(right):
        return 0.0
    dot = norm_left = norm_right = 0.0
    for a, b in zip(left, right):
        dot += a * b
        norm_left += a * a
        norm_right += b * b
    if norm_left <= 0.0 or norm_right <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_left) * math.sqrt(norm_right))


async def dense_scores(
    question: str, cards: Sequence[ToolCard]
) -> dict[str, float] | None:
    """向量召回分数；不可用时返回 None，并在本进程内永久降级为纯词法。"""
    global _DENSE_DISABLED
    if _DENSE_DISABLED:
        return None
    timeout = get_settings().tool_route_embedding_timeout_seconds
    try:
        vectors = await asyncio.wait_for(asyncio.to_thread(_ensure_card_vectors), timeout)
        query_vector = await asyncio.wait_for(
            asyncio.to_thread(get_embeddings().embed_query, question), timeout
        )
    except Exception:
        # Embedding 端点配置错误时不应给每个请求都加一次超时等待。
        _DENSE_DISABLED = True
        logger.warning("tool_route_dense_unavailable", exc_info=True)
        return None
    return {
        card.name: max(0.0, _cosine(query_vector, vectors[card.name]))
        for card in cards
        if card.name in vectors
    }


@dataclass(frozen=True)
class ScoredCard:
    card: ToolCard
    lexical: float
    dense: float
    score: float


async def hybrid_retrieve(
    question: str, cards: Sequence[ToolCard], top_k: int, embedding_weight: float
) -> tuple[list[ScoredCard], str]:
    """词法 + 向量融合排序；丢弃无任何信号的卡片后截断到 top_k。"""
    if not cards:
        return [], "lexical"

    lexical = lexical_scores(question, cards)
    max_lexical = max(lexical.values(), default=0.0)
    lexical_norm = {
        name: (value / max_lexical if max_lexical > 0 else 0.0)
        for name, value in lexical.items()
    }

    dense = None
    if embedding_weight > 0:
        dense = await dense_scores(question, cards)

    registry_order = {card.name: index for index, card in enumerate(TOOL_CARDS)}
    scored: list[ScoredCard] = []
    for card in cards:
        lexical_value = lexical_norm.get(card.name, 0.0)
        dense_value = dense.get(card.name, 0.0) if dense is not None else 0.0
        score = (
            (1.0 - embedding_weight) * lexical_value + embedding_weight * dense_value
            if dense is not None
            else lexical_value
        )
        if score <= 0:
            continue
        scored.append(
            ScoredCard(
                card=card,
                lexical=round(lexical_value, 6),
                dense=round(dense_value, 6),
                score=round(score, 6),
            )
        )

    # 并列分数按注册表顺序兜底，保证同一输入始终得到同一候选顺序。
    scored.sort(key=lambda item: (-item.score, registry_order.get(item.card.name, len(registry_order))))
    return scored[:top_k], ("hybrid" if dense is not None else "lexical")


@dataclass(frozen=True)
class RouteDecision:
    candidates: tuple[ScoredCard, ...]
    domains: tuple[str, ...]
    confidence: float
    reason: str
    layer: str
    dropped: tuple[dict[str, str], ...]
    latency_ms: float

    @property
    def cards(self) -> tuple[ToolCard, ...]:
        return tuple(scored.card for scored in self.candidates)

    @property
    def tools(self) -> list:
        return [scored.card.tool for scored in self.candidates]


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


async def route_tools(
    question: str,
    context: RoutingContext | None = None,
    *,
    top_k: int | None = None,
    embedding_weight: float | None = None,
) -> RouteDecision:
    """分层路由入口：过滤 → （逃生舱 | 粗分 → 检索）→ 候选集合。"""
    started = time.perf_counter()
    if context is None:
        context = RoutingContext(
            environment=active_environment(), confirmed=has_confirmation(question)
        )
    settings = get_settings()
    weight = settings.tool_route_embedding_weight if embedding_weight is None else embedding_weight
    k = top_k or max(1, settings.agent_max_exposed_tools)

    allowed, dropped = filter_cards(TOOL_CARDS, context)
    dropped_items = tuple(dropped)
    if not allowed:
        return RouteDecision(
            (), (), 0.0, "no_allowed_tools", "empty_after_filter", dropped_items, _elapsed_ms(started)
        )

    if any(keyword in question.lower() for keyword in ALL_TOOLS_REQUEST_KEYWORDS):
        # 显式逃生舱绕过粗分与检索，但不绕过过滤层和高风险确认门。
        candidates = tuple(ScoredCard(card, 1.0, 1.0, 1.0) for card in allowed)
        return RouteDecision(
            candidates, (), 1.0, "explicit_all_tools_request", "explicit_all", dropped_items,
            _elapsed_ms(started),
        )

    domains = classify_domains(question, allowed)
    if not domains:
        return RouteDecision(
            (), (), 0.0, "no_tool_intent", "no_intent", dropped_items, _elapsed_ms(started)
        )

    scoped = [card for card in allowed if card.category in domains]
    if not scoped:
        # 命中业务域内的工具被权限或确认门挡掉时不能扩大召回，否则直接造成越权暴露。
        return RouteDecision(
            (), domains, 0.0, "no_allowed_tools_in_domain", "empty_after_filter", dropped_items,
            _elapsed_ms(started),
        )

    ranked, layer = await hybrid_retrieve(question, scoped, k, weight)
    reason = "domain_and_retrieval"
    if not ranked:
        ranked, _ = await hybrid_retrieve(question, allowed, k, weight)
        if not ranked:
            return RouteDecision(
                (), domains, 0.0, "no_tool_intent", "no_intent", dropped_items, _elapsed_ms(started)
            )
        layer, reason = "expanded", "expanded_domain_after_empty"

    threshold = settings.tool_route_min_confidence
    if threshold > 0 and ranked[0].score < threshold:
        broadened, _ = await hybrid_retrieve(question, allowed, k, weight)
        if broadened:
            ranked, layer, reason = broadened, "expanded", "expanded_low_confidence"

    return RouteDecision(
        tuple(ranked), domains, ranked[0].score, reason, layer, dropped_items, _elapsed_ms(started)
    )


def check_tool_authorized(name: str, allowed_names: Collection[str]) -> bool:
    """执行期兜底：候选集之外的工具名一律拒绝。"""
    return name in allowed_names


def _bind_descriptions() -> None:
    """把何时用 / 何时不用追加进工具描述，供模型区分相似工具；以「不适用：」做幂等标记。"""
    for card in TOOL_CARDS:
        base = (card.tool.description or "").rstrip()
        if "不适用：" in base:
            continue
        card.tool.description = (
            f"{base}\n\n适用场景：{card.when_to_use}\n不适用：{card.when_not_to_use}"
        )


_bind_descriptions()
_build_term_idf()
