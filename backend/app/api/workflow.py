"""工作流 API：启动 LangGraph 任务并提供状态查询接口。"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.workflow_service import run_workflow_stream
import uuid

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


class WorkflowRequest(BaseModel):
    question: str
    conversation_id: str | None = None


@router.post("/start")
async def start_workflow(req: WorkflowRequest) -> StreamingResponse:
    """启动 LangGraph 工作流，SSE 流式返回节点执行状态"""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    thread_id = str(uuid.uuid4())

    # thread_id 同时作为 LangGraph checkpoint 的隔离键，避免并发任务串状态。
    return StreamingResponse(
        run_workflow_stream(
            question=req.question,
            chat_history=[],
            thread_id=thread_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Workflow-Thread-Id": thread_id,
        },
    )


@router.get("/status/{thread_id}")
async def get_workflow_status(thread_id: str):
    """查询工作流当前状态（用于轮询恢复场景）"""
    from app.agent.workflow import get_workflow

    workflow = await get_workflow()
    config = {"configurable": {"thread_id": thread_id}}
    state = await workflow.aget_state(config)

    if not state:
        return {"thread_id": thread_id, "status": "not_found"}

    values = state.values or {}
    return {
        "thread_id": thread_id,
        "current_node": values.get("current_node", ""),
        "node_status": values.get("node_status", ""),
        "final_answer": values.get("final_answer"),
    }


@router.get("/history")
async def list_workflows():
    """列出历史工作流执行记录"""
    return {"workflows": [], "message": "历史记录功能将在后续版本实现"}
