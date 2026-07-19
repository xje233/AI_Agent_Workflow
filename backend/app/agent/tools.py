"""Agent 工具集（含输入校验、异常处理、输出规范化）"""
import re
from langchain.tools import tool
from app.rag.retriever import similarity_search


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
        docs = await similarity_search(query, k=4)

        if not docs:
            return (
                "【检索结果】未在知识库中找到相关文档。\n"
                "建议：1) 确认文档已上传 2) 尝试不同的关键词 3) 检查知识库索引状态"
            )

        results = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', '未知来源')
            content = doc.page_content[:800]  # 截断过长内容
            results.append(f"**【文档 {i}】** 来源: `{source}`\n{content}")

        return "\n\n---\n\n".join(results)

    except ValueError as e:
        return f"【参数错误】{e}"
    except Exception as e:
        return f"【检索失败】知识库服务暂时不可用，请稍后重试。错误信息：{str(e)[:200]}"


@tool
def query_db(sql: str) -> str:
    """
    执行 SQL 查询获取结构化数据。
    适用场景：数据统计、记录查询、业务数据提取。
    仅支持 SELECT 查询，不支持修改操作。
    """
    # 安全检查：仅允许 SELECT
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return "【执行拒绝】仅允许 SELECT 查询操作。"
    if any(kw in sql_upper for kw in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]):
        return "【执行拒绝】不允许修改数据库结构的操作。"

    return (
        "【SQL 模拟结果】\n"
        f"```sql\n{sql.strip()[:500]}\n```\n"
        "> 提示：SQL 查询当前为模拟模式。生产环境需配置数据库连接后启用真实查询。"
    )


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

    # 安全检查
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


def select_tools(question: str):
    text = question.lower()
    if any(word in text for word in ("知识库", "文档", "资料", "搜索", "检索", "文件")):
        return KNOWLEDGE_TOOLS
    if any(word in text for word in ("sql", "数据库", "统计", "查询数据")):
        return DATA_TOOLS
    if any(word in text for word in ("python", "计算", "脚本", "运行代码")):
        return CODE_TOOLS
    if any(word in text for word in ("邮件", "通知", "发送")):
        return NOTIFICATION_TOOLS
    return ALL_TOOLS
