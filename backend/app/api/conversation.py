from fastapi import APIRouter
from sqlalchemy import select
from app.database import get_sessionmaker
from app.models.conversation import Conversation
from app.models.message import Message

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations():
    async with get_sessionmaker()() as db:
        result = await db.execute(
            select(Conversation).order_by(Conversation.created_at.desc()).limit(50)
        )
        conversations = result.scalars().all()
        return [
            {"id": str(c.id), "title": c.title, "created_at": str(c.created_at)}
            for c in conversations
        ]


@router.get("/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    from app.services.chat_service import ChatService
    svc = ChatService()
    messages = await svc.get_messages(conversation_id)
    return {"messages": messages}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    async with get_sessionmaker()() as db:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            await db.delete(conv)
            await db.commit()
    return {"status": "ok"}
