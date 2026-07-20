"""聊天 API：创建会话并以 SSE 持续返回 Agent 输出。"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import time
import uuid

from app.config import get_settings
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])

chat_service = ChatService()


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    conversation_id: str
    message: str


@router.post("/send")
async def send_message(req: ChatRequest) -> StreamingResponse:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 请求指标贯穿服务层，用于分析模型首 token 和 SSE 输出时延。
    metrics = {
        "request_id": str(uuid.uuid4()),
        "conversation_id": req.conversation_id or "",
        "model": get_settings().model_name,
        "request_received": time.perf_counter(),
    }
    conversation_id = await chat_service.get_or_create_conversation(req.conversation_id)
    metrics["conversation_id"] = conversation_id
    metrics["conversation_ready"] = time.perf_counter()

    return StreamingResponse(
        chat_service.chat_stream(conversation_id, req.message, metrics),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # 禁止反向代理缓冲，否则前端无法实时收到 token。
            "X-Accel-Buffering": "no",
            "X-Conversation-Id": conversation_id,
        },
    )


@router.post("/new")
async def new_conversation():
    conv_id = await chat_service.get_or_create_conversation(None, "新会话")
    return {"conversation_id": conv_id}
