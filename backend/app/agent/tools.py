"""Agent 工具集（含输入校验、异常处理、输出规范化）"""
import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field

from langchain.tools import tool
from sqlalchemy import text

from app.config import get_settings
from app.database import get_sessionmaker
from app.rag.pipeline import retrieve


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolResult:
    """工具统一结果，避免把异常堆栈直接暴露给模型和用户。"""

    ok: bool
    code: str
    message: str
    data: list[dict] = field(default_factory=list)

    def render(self) -> str:
        if not self.ok:
            return f"【{self.code}】{self.message}"
        payload = json.dumps(self.data, ensure_ascii=False, default=str)
        return f"【{self.code}】{self.message}\n```json\n{payload}\n```"


def _validate_query(query: str) -> str:
    """通用输入校验"""
    if not query or not query.strip():
        raise ValueError("查询内容不能为空")
    q = query.strip()
    if len(q) > 2000:
        raise ValueError("查询内容过长（限制2000字符）")
    # 过滤潜在的危险字符
    q = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', q)
    return q


@tool
async def search_tool(query: str) -> str:
    """
    在企业知识库中搜索相关文档内容。
    适用场景：知识性问题、文档内容查找、方案参考。
    注意：只能搜索已上传到知识库的文档。
    """
    try:
        query = _validate_query(query)
        # 统一执行查询路由、改写和相关性评估，避免把最近邻弱命中交给模型。
        retrieval = await retrieve(query, k=4)
        docs = retrieval.documents

        if not docs:
            return (
                "【检索结果】未在知识库中找到相关文档。\n"
                "建议：1) 确认文档已上传 2) 尝试不同的关键词 3) 检查知识库索引状态"
            )

        results = [f"【检索查询】{retrieval.query}（路由：{retrieval.route.reason}）"]
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', '未知来源')
            content = doc.page_content[:800]  # 截断过长内容
            results.append(f"**【文档 {i}】** 来源: `{source}`\n{content}")

        return "\n\n---\n\n".join(results)

    except ValueError as e:
        return f"【参数错误】{e}"
    except Exception as e:
        return f"【检索失败】知识库服务暂时不可用，请稍后重试。错误信息：{str(e)[:200]}"


_QUERY_COLUMNS = {
    "conversations": {"id", "title", "created_at"},
    "messages": {"id", "conversation_id", "role", "content", "created_at"},
    "documents": {"id", "filename", "file_type", "vector_status", "created_at"},
}
_QUERY_KEYWORDS = {
    "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "NULL", "IS", "LIKE",
    "ORDER", "BY", "GROUP", "ASC", "DESC", "LIMIT", "OFFSET", "AS", "COUNT",
    "DISTINCT", "TRUE", "FALSE",
}
_BLOCKED_SQL_TERMS = (
    "JOIN", "UNION", "WITH", "INTO", "PRAGMA", "ATTACH", "DETACH", "COPY",
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "GRANT",
    "REVOKE", "EXEC", "EXECUTE", "CALL",
)


def _validate_read_query(sql: str) -> str:
    """校验并标准化只读查询，返回带最大行数限制的 SQL。"""
    if not sql or not sql.strip():
        raise ValueError("SQL 查询不能为空")
    query = sql.strip()
    if len(query) > 4000:
        raise ValueError("SQL 查询过长（限制 4000 字符）")
    if "--" in query or "/*" in query or "*/" in query:
        raise ValueError("不允许使用 SQL 注释")
    if ";" in query:
        if not query.endswith(";") or query[:-1].find(";") >= 0:
            raise ValueError("只允许执行一条 SQL 语句")
        query = query[:-1].rstrip()

    upper = query.upper()
    if not re.match(r"^SELECT\b", upper):
        raise ValueError("仅允许 SELECT 查询")
    for term in _BLOCKED_SQL_TERMS:
        if re.search(rf"\b{term}\b", upper):
            raise ValueError(f"不允许使用 {term} 操作")
    if "*" in query:
        raise ValueError("必须指定明确列名，不能使用 SELECT *")

    table_match = re.search(r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)\b", query, re.IGNORECASE)
    if not table_match:
        raise ValueError("查询必须指定允许的 FROM 表")
    table = table_match.group(1).lower()
    if table not in _QUERY_COLUMNS:
        raise ValueError(f"不允许查询的表：{table}")

    select_part = query[6 : table_match.start()].strip()
    if not select_part:
        raise ValueError("必须指定查询列")
    for expression in select_part.split(","):
        expression = expression.strip()
        column_match = re.fullmatch(
            r"(?:COUNT\s*\(\s*)?([A-Za-z_][A-Za-z0-9_]*)(?:\s*\))?(?:\s+AS\s+[A-Za-z_][A-Za-z0-9_]*)?",
            expression,
            re.IGNORECASE,
        )
        if not column_match or column_match.group(1).lower() not in _QUERY_COLUMNS[table]:
            raise ValueError(f"不允许查询的列：{expression}")

    # 移除字符串和数字后检查剩余标识符，防止 WHERE/ORDER BY 引用未授权字段。
    scrubbed = re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|\b\d+(?:\.\d+)?\b", " ", query)
    identifiers = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", scrubbed)
    allowed_identifiers = _QUERY_KEYWORDS | set(_QUERY_COLUMNS[table]) | {table}
    unknown = sorted({item.lower() for item in identifiers if item.upper() not in _QUERY_KEYWORDS and item.lower() not in allowed_identifiers})
    if unknown:
        raise ValueError(f"不允许使用的标识符：{', '.join(unknown)}")

    limit_match = re.search(r"\bLIMIT\s+(\d+)\b", query, re.IGNORECASE)
    if limit_match and int(limit_match.group(1)) > 100:
        raise ValueError("LIMIT 不能超过 100")
    if not limit_match:
        query = f"{query} LIMIT 100"
    return query


async def _execute_read_query(sql: str) -> list[dict]:
    async with get_sessionmaker()() as session:
        result = await session.execute(text(sql))
        return [dict(row._mapping) for row in result.fetchall()]


@tool
async def query_db(sql: str) -> str:
    """
    在应用数据库中执行受限的只读 SQL 查询。
    仅允许 conversations、messages、documents 三张白名单表，最多返回 100 行。
    """
    started = time.perf_counter()
    query_hash = hashlib.sha256((sql or "").encode("utf-8")).hexdigest()[:12]
    table = "unknown"
    try:
        safe_sql = _validate_read_query(sql)
        table_match = re.search(r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)\b", safe_sql, re.IGNORECASE)
        table = table_match.group(1).lower() if table_match else table
        rows = await asyncio.wait_for(
            _execute_read_query(safe_sql),
            timeout=get_settings().database_query_timeout_seconds,
        )
        result = ToolResult(True, "数据库查询成功", f"已返回 {len(rows)} 行", rows)
        logger.info(
            "query_db_audit",
            extra={"query_hash": query_hash, "table": table, "status": "success", "rows": len(rows), "duration_ms": round((time.perf_counter() - started) * 1000, 2)},
        )
        return result.render()
    except ValueError as exc:
        logger.warning("query_db_audit", extra={"query_hash": query_hash, "table": table, "status": "rejected", "reason": str(exc)})
        return ToolResult(False, "数据库查询拒绝", str(exc)).render()
    except asyncio.TimeoutError:
        logger.warning("query_db_audit", extra={"query_hash": query_hash, "table": table, "status": "timeout"})
        return ToolResult(False, "数据库查询超时", "查询超过允许的执行时间，请缩小范围后重试").render()
    except Exception:
        logger.exception("query_db_audit", extra={"query_hash": query_hash, "table": table, "status": "error"})
        return ToolResult(False, "数据库查询失败", "数据库暂时不可用，请稍后重试").render()


@tool
def analyze_doc(file_name: str) -> str:
    """
    分析指定文档内容，返回结构化摘要。
    适用场景：文档解读、关键信息提取、风险分析。
    """
    try:
        file_name = _validate_query(file_name)
    except ValueError as e:
        return f"【参数错误】{e}"

    return (
        "【文档分析】（模拟模式）\n"
        f"- 文件名称：`{file_name}`\n"
        f"- 分析状态：待接入文档解析服务\n"
        "> 提示：完整文档分析需要将文件上传至知识库后使用 search_tool 检索。"
    )


@tool
def run_python(code: str) -> str:
    """
    安全执行 Python 代码并返回结果。
    适用场景：数据处理、数值计算、格式转换。
    注意：代码执行在受限环境中，不能访问网络和文件系统。
    """
    import io
    import sys

    # 安全检查采用关键字拒绝和受限内建函数的双层限制。
    forbidden = [
        "import os", "import sys", "import subprocess", "import socket",
        "import requests", "import urllib", "__import__", "eval(", "exec(",
        "open(", "compile(", "globals()", "__builtins__",
    ]
    code_lower = code.lower()
    for kw in forbidden:
        if kw in code_lower:
            return f"【执行拒绝】代码包含不允许的操作：`{kw}`"

    if len(code) > 5000:
        return "【执行拒绝】代码过长（限制 5000 字符）"

    safe_builtins = {
        "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
        "chr": chr, "dict": dict, "divmod": divmod, "enumerate": enumerate,
        "filter": filter, "float": float, "format": format, "frozenset": frozenset,
        "hash": hash, "hex": hex, "int": int, "isinstance": isinstance,
        "issubclass": issubclass, "iter": iter, "len": len, "list": list,
        "map": map, "max": max, "min": min, "next": next, "oct": oct,
        "ord": ord, "pow": pow, "print": print, "range": range,
        "repr": repr, "reversed": reversed, "round": round, "set": set,
        "slice": slice, "sorted": sorted, "str": str, "sum": sum,
        "tuple": tuple, "type": type, "zip": zip,
    }

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(code, {"__builtins__": safe_builtins})
        result = sys.stdout.getvalue()
        if result:
            return f"【执行结果】\n```\n{result.strip()[:2000]}\n```"
        return "【执行结果】代码执行完成，无输出。"
    except Exception as e:
        return f"【执行错误】\n```\n{type(e).__name__}: {str(e)[:300]}\n```"
    finally:
        sys.stdout = old_stdout


@tool
def send_email(content: str) -> str:
    """
    发送邮件通知。
    适用场景：审批通知、结果分发、告警通知。
    """
    if not content or not content.strip():
        return "【发送失败】邮件内容不能为空。"
    if len(content) > 10000:
        return "【发送失败】邮件内容过长（限制 10000 字符）。"

    return (
        "【发送成功】（模拟模式）\n"
        f"邮件内容预览：{content.strip()[:200]}...\n"
        "> 提示：邮件功能为模拟模式，生产环境需配置 SMTP 服务。"
    )


ALL_TOOLS = [search_tool, query_db, analyze_doc, run_python, send_email]

KNOWLEDGE_TOOLS = [search_tool]
DATA_TOOLS = [query_db]
DOCUMENT_TOOLS = [analyze_doc, search_tool]
CODE_TOOLS = [run_python]
NOTIFICATION_TOOLS = [send_email]
ALL_TOOLS_REQUEST_KEYWORDS = ("所有工具", "全部工具", "所有功能", "全部功能")


@dataclass(frozen=True)
class ToolSpec:
    """工具注册信息，供路由、风险过滤和后续权限系统复用。"""

    name: str
    tool: object
    category: str
    risk: str
    read_only: bool
    requires_confirmation: bool
    keywords: tuple[str, ...]


TOOL_SPECS = (
    ToolSpec(
        "search_tool", search_tool, "knowledge", "low", True, False,
        ("知识库", "资料", "搜索", "检索"),
    ),
    ToolSpec(
        "analyze_doc", analyze_doc, "document", "low", True, False,
        ("分析文档", "文档分析", "解读文件"),
    ),
    ToolSpec(
        "query_db", query_db, "data", "medium", True, False,
        ("sql", "数据库", "统计", "查询数据"),
    ),
    ToolSpec(
        "run_python", run_python, "compute", "medium", True, False,
        ("python", "计算", "脚本", "运行代码"),
    ),
    ToolSpec(
        "send_email", send_email, "notification", "high", False, True,
        ("邮件", "通知", "发送"),
    ),
)


def select_tools(question: str):
    """按意图选择少量工具；无明确意图返回空列表，避免扩大工具暴露面。"""
    text = question.lower()
    if any(keyword in text for keyword in ALL_TOOLS_REQUEST_KEYWORDS):
        # 保留显式调试/演示入口；普通问题永远走下面的上限路由。
        return ALL_TOOLS

    max_tools = max(1, get_settings().agent_max_exposed_tools)
    selected_tools = []
    for spec in TOOL_SPECS:
        if any(keyword in text for keyword in spec.keywords):
            selected_tools.append(spec.tool)
            if len(selected_tools) >= max_tools:
                break
    return selected_tools
