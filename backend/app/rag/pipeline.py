"""RAG 四层策略：路由、检索评估、查询改写和回答校验。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from langchain.schema import Document

from app.agent.guard import OutputGuard
from app.config import get_settings
from app.rag.retriever import similarity_search, similarity_search_with_scores


@dataclass(frozen=True)
class QueryRoute:
    should_retrieve: bool
    reason: str
    k: int


@dataclass(frozen=True)
class RetrievalResult:
    route: QueryRoute
    query: str
    documents: list[Document]
    scores: list[float]


_KNOWLEDGE_TERMS = ("知识库", "文档", "资料", "制度", "流程", "规范", "政策", "手册", "根据")
_CHAT_TERMS = ("你好", "您好", "嗨", "谢谢", "再见", "你是谁")
_REFUSAL_MARKERS = ("未找到", "没有相关", "无相关", "无法确认", "无法回答")


def route_query(query: str, default_k: int | None = None) -> QueryRoute:
    """判断是否需要知识库，避免问候语和纯闲聊无意义地触发检索。"""
    text = query.strip().lower()
    k = default_k or get_settings().rag_default_k
    if not text:
        return QueryRoute(False, "empty_query", k)
    if any(term in text for term in _CHAT_TERMS) and len(text) <= 20:
        return QueryRoute(False, "casual_chat", k)
    if any(term in text for term in _KNOWLEDGE_TERMS):
        return QueryRoute(True, "knowledge_intent", k)
    # 企业助手的非闲聊问题默认检索，宁可交给相关性评估层拒绝弱命中。
    return QueryRoute(True, "default_knowledge_search", k)


def rewrite_query(query: str, history: Iterable[str] | None = None) -> str:
    """做低成本、可解释的查询规范化；不改变用户的业务实体和数字。"""
    text = re.sub(r"\s+", " ", query.strip())
    text = re.sub(r"^(请问|请帮我|麻烦告诉我|能否告诉我)[，,:： ]*", "", text)
    if history and re.search(r"(它|这个|那个|上述|该规定|该流程)", text):
        previous = next((item.strip() for item in reversed(list(history)) if item.strip()), "")
        if previous:
            text = f"{previous} {text}"
    return text[:2000]


def evaluate_retrieval(
    hits: Iterable[tuple[Document, float]], threshold: float | None = None, k: int = 4
) -> tuple[list[Document], list[float]]:
    """按相关性阈值过滤并按来源/内容去重，返回最终证据集。"""
    min_score = get_settings().rag_relevance_threshold if threshold is None else threshold
    documents: list[Document] = []
    scores: list[float] = []
    seen: set[tuple[str, str]] = set()
    for document, score in hits:
        source = str(document.metadata.get("source", ""))
        key = (source, document.page_content.strip())
        if score < min_score or key in seen:
            continue
        seen.add(key)
        documents.append(document)
        scores.append(round(float(score), 4))
        if len(documents) >= k:
            break
    return documents, scores


async def retrieve(
    query: str, k: int | None = None, collection_name: str = "knowledge_base"
) -> RetrievalResult:
    """执行完整的路由、改写、检索和相关性评估流程。"""
    route = route_query(query, default_k=k)
    if not route.should_retrieve:
        return RetrievalResult(route, query.strip(), [], [])

    rewritten = rewrite_query(query)
    try:
        hits = await similarity_search_with_scores(rewritten, route.k, collection_name)
        documents, scores = evaluate_retrieval(hits, k=route.k)
    except AttributeError:
        # 兼容不支持 relevance scores 的向量库实现，至少保留原有检索能力。
        documents = await similarity_search(rewritten, route.k, collection_name)
        scores = []
    return RetrievalResult(route, rewritten, documents, scores)


def validate_answer(answer: str, evidence: list[Document], routed_to_retrieval: bool) -> dict:
    """先执行通用输出护栏，再拦截无证据却给出确定答案的情况。"""
    result = OutputGuard.validate(answer)
    if routed_to_retrieval and not evidence and not any(marker in answer for marker in _REFUSAL_MARKERS):
        reason = "no_evidence"
        return {
            "text": "根据现有知识库资料，未找到足以支持该问题的相关文档，无法确认答案。",
            "has_issue": True,
            "issues": [reason],
            "used_fallback": True,
        }
    return result
