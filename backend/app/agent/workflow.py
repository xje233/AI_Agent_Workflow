"""
LangGraph StateGraph 定义
4 节点链: analyze → research → execute → review
"""
from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.config import get_settings, BASE_DIR
from app.agent.workflow_nodes import (
    analyze_node,
    research_node,
    execute_node,
    review_node,
)

settings = get_settings()


class WorkflowState(TypedDict):
    """工作流状态定义"""
    question: str
    chat_history: Annotated[list, add]

    # 各节点输出（注意：字段名不能与节点名重复）
    plan: str
    parsed_plan: dict
    research_data: dict
    draft_answer: str
    final_answer: str

    # 审核
    review_note: str
    guard_result: dict

    # 进度跟踪
    current_node: str
    node_status: str


def build_workflow() -> StateGraph:
    """构建 LangGraph 工作流"""
    builder = StateGraph(WorkflowState)

    builder.add_node("analyze", analyze_node)
    builder.add_node("research", research_node)
    builder.add_node("execute", execute_node)
    builder.add_node("review", review_node)

    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "research")
    builder.add_edge("research", "execute")
    builder.add_edge("execute", "review")
    builder.add_edge("review", END)

    return builder


_workflow = None
_checkpointer_ctx = None


async def get_workflow():
    global _workflow, _checkpointer_ctx
    if _workflow is None:
        # 仅在首个工作流请求时创建图和检查点连接，后续请求复用同一实例。
        builder = build_workflow()
        db_path = BASE_DIR / "data" / "workflow_checkpoints.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # 上下文管理器需要长期持有，以保持检查点 SQLite 连接在应用生命周期内可用。
        _checkpointer_ctx = AsyncSqliteSaver.from_conn_string(str(db_path))
        checkpointer = await _checkpointer_ctx.__aenter__()
        _workflow = builder.compile(checkpointer=checkpointer)
    return _workflow
