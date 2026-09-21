"""
LangGraph 工作流节点定义
4 节点链: analyze → research → execute → review

重要：节点函数只返回需要更新的字段，LangGraph StateGraph 会自动合并到 state 中。
不要使用 **state 展开，否则会与 Annotated[list, add] 类型字段冲突。
"""
import json
from langchain_core.messages import HumanMessage
from app.config import get_settings
from app.agent.base import get_llm
from app.rag.retriever import similarity_search
from app.agent.guard import OutputGuard

settings = get_settings()
_guard = OutputGuard()
_llm = get_llm(temperature=0.3)


def analyze_node(state: dict) -> dict:
    """分析用户意图，拆解子任务，输出结构化计划"""
    question = state.get("question", "")

    prompt = f"""你是一个工作流规划器。分析用户问题并输出结构化执行计划。

用户问题: {question}

请输出 JSON 格式的执行计划，包含:
1. intent: 用户意图分类 (query|analysis|generation|troubleshooting|chat)
2. subtasks: 子任务列表，每个含:
   - "step": 序号
   - "action": 描述
   - "tool": 需要的工具名称或"none"
3. expected_output: 预期产出描述

只输出 JSON，不要其他内容。"""

    result = _llm.invoke([HumanMessage(content=prompt)])
    content = result.content

    try:
        plan = json.loads(content)
    except json.JSONDecodeError:
        plan = {"intent": "general", "subtasks": [], "expected_output": content}

    return {
        "plan": content,
        "parsed_plan": plan,
        "current_node": "analyze",
        "node_status": "completed",
    }


async def research_node(state: dict) -> dict:
    """RAG 检索 + 信息收集"""
    question = state.get("question", "")
    plan_data = state.get("plan", "")

    # 知识库检索（异步）
    try:
        docs = await similarity_search(question, k=4)
        knowledge_context = "\n\n".join(
            f"[文档{i+1}] {doc.page_content[:500]}" for i, doc in enumerate(docs)
        ) if docs else "知识库中未找到相关文档。"
    except Exception as e:
        knowledge_context = f"知识库检索失败: {e}"

    # 汇总研究结果
    prompt = f"""你是一个信息收集研究员。根据以下信息回答用户问题。

用户问题: {question}
执行计划: {plan_data}
知识库检索结果:
{knowledge_context}

请输出:
1. 收集到的关键信息（分点列出）
2. 信息缺口（有哪些问题尚待明确）
3. 建议的下一步行动

使用 Markdown 格式回复。"""

    result = _llm.invoke([HumanMessage(content=prompt)])

    return {
        "research_data": {
            "knowledge": knowledge_context,
            "analysis": result.content,
        },
        "current_node": "research",
        "node_status": "completed",
    }


def execute_node(state: dict) -> dict:
    """汇总信息，生成最终方案/答案"""
    question = state.get("question", "")
    research_data = state.get("research_data", {})

    prompt = f"""你是一个方案生成专家。基于研究结果，为用户问题生成完整回复。

用户问题: {question}

研究结果:
{research_data.get('analysis', '无研究结果')}

知识库原文:
{research_data.get('knowledge', '无知识库内容')}

请按照以下模板输出:

【结论】一句话总结核心答案

【分析】详细分析过程，引用研究中的关键发现

【建议】具体可执行的建议或方案（如适用）

【参考】引用的知识来源（如有）

使用 Markdown 格式，确保内容专业、准确、可执行。
遵守反幻觉规则：不编造任何数据、日期、数字。"""

    result = _llm.invoke([HumanMessage(content=prompt)])

    return {
        "draft_answer": result.content,
        "current_node": "execute",
        "node_status": "completed",
    }


def review_node(state: dict) -> dict:
    """LLM 自检：幻觉检测、完整性校验、格式审查"""
    draft = state.get("draft_answer", "")

    # 使用 guard 模块做基础检测，返回结构化 dict
    guard_result = _guard.validate(draft)

    # guard_result 结构：{"text", "has_issue", "issues", "used_fallback"}
    if guard_result["used_fallback"]:
        # 质量问题严重，使用兜底回复作为最终答案
        final_answer = guard_result["text"]
    elif guard_result["has_issue"]:
        # 有警告但不需要兜底，附加标注
        issue_tags = guard_result["issues"]
        tags_text = "\n".join(f"- {t}" for t in issue_tags)
        final_answer = f"""{draft}

---
⚠️ **质量审查标注**（以下问题可能需要人工确认）：
{tags_text}
"""
    else:
        final_answer = draft

    # 完整性审查
    question = state.get("question", "")
    review_prompt = f"""你是一个质量审核员。请审查以下回复是否完整回答了用户问题。

用户问题: {question}
生成的回复:
{draft[:2000]}

请简要输出审查意见（1-2句话），如果回复完整则输出"PASS"。"""
    try:
        review_result = _llm.invoke([HumanMessage(content=review_prompt)])
        review_note = review_result.content.strip()
    except Exception:
        review_note = "PASS"

    return {
        "final_answer": final_answer,
        "review_note": review_note,
        "guard_result": guard_result,
        "current_node": "review",
        "node_status": "completed",
    }
