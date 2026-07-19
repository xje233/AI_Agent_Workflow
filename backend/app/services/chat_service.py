import asyncio
import json
import time
import uuid
from typing import AsyncGenerator

from sqlalchemy import select

from app.agent.base import create_agent
from app.agent.guard import guard
from app.agent.memory import RedisConversationMemory
from app.database import get_sessionmaker
from app.models.conversation import Conversation
from app.models.message import Message


class ChatService:
    def __init__(self):
        self.active_agents: dict[str, object] = {}

    async def get_or_create_conversation(
        self, conversation_id: str | None, title: str = "New Chat"
    ) -> str:
        async with get_sessionmaker()() as db:
            if conversation_id:
                result = await db.execute(
                    select(Conversation).where(Conversation.id == conversation_id)
                )
                conv = result.scalar_one_or_none()
                if conv:
                    return str(conv.id)

            conv = Conversation(title=title)
            db.add(conv)
            await db.commit()
            await db.refresh(conv)
            return str(conv.id)

    async def get_messages(self, conversation_id: str) -> list[dict]:
        async with get_sessionmaker()() as db:
            result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            messages = result.scalars().all()
            return [{"role": m.role, "content": m.content} for m in messages]

    async def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        message_id: str | None = None,
    ):
        async with get_sessionmaker()() as db:
            db.add(
                Message(
                    id=message_id or str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    role=role,
                    content=content,
                )
            )
            await db.commit()

    async def get_previous_messages(
        self, conversation_id: str, exclude_id: str
    ) -> list[dict]:
        async with get_sessionmaker()() as db:
            result = await db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.id != exclude_id,
                )
                .order_by(Message.created_at)
            )
            messages = result.scalars().all()
            return [{"role": m.role, "content": m.content} for m in messages]

    @staticmethod
    def trim_history(
        messages: list[dict], max_messages: int = 20, max_chars: int = 12000
    ) -> list[dict]:
        selected: list[dict] = []
        chars = 0
        for message in reversed(messages):
            content = message["content"]
            if selected and (
                len(selected) >= max_messages or chars + len(content) > max_chars
            ):
                break
            selected.append(message)
            chars += len(content)
        return list(reversed(selected))

    @staticmethod
    def mark(metrics: dict, name: str) -> None:
        metrics[name] = time.perf_counter()

    @staticmethod
    def metric_payload(metrics: dict) -> dict:
        start = metrics["request_received"]
        durations = {
            name: round((value - start) * 1000, 2)
            for name, value in metrics.items()
            if name != "request_received" and isinstance(value, float)
        }
        return {
            "request_id": metrics["request_id"],
            "conversation_id": metrics["conversation_id"],
            "model": metrics["model"],
            "history_message_count": metrics.get("history_message_count", 0),
            "history_character_count": metrics.get("history_character_count", 0),
            "durations_ms": durations,
            "backend_model_ttft_ms": round(
                (metrics["first_model_token"] - metrics["model_request_started"])
                * 1000,
                2,
            )
            if "first_model_token" in metrics
            else None,
            "backend_sse_ttft_ms": round(
                (metrics["first_sse_yielded"] - start) * 1000, 2
            )
            if "first_sse_yielded" in metrics
            else None,
        }

    @classmethod
    def log_metrics(cls, metrics: dict) -> None:
        print(json.dumps({"event": "chat_timing", **cls.metric_payload(metrics)}, ensure_ascii=False))

    async def chat_stream(
        self, conversation_id: str, question: str, metrics: dict
    ) -> AsyncGenerator[str, None]:
        if not question or not question.strip():
            yield f"data: {json.dumps({'content': '请输入您的问题。', 'done': True})}\n\n"
            return
        if len(question) > 5000:
            yield f"data: {json.dumps({'content': '问题过长，请精简后重试（限5000字）。', 'done': True})}\n\n"
            return

        user_message_id = str(uuid.uuid4())
        history_task = self.get_previous_messages(conversation_id, user_message_id)
        save_task = self.save_message(
            conversation_id, "user", question, user_message_id
        )
        history_messages, _ = await asyncio.gather(history_task, save_task)
        self.mark(metrics, "user_message_saved")
        self.mark(metrics, "history_loaded")

        history_messages = self.trim_history(history_messages)
        metrics["history_message_count"] = len(history_messages)
        metrics["history_character_count"] = sum(
            len(message["content"]) for message in history_messages
        )

        memory = RedisConversationMemory(conversation_id=conversation_id)
        memory.load_from_db(history_messages)
        self.mark(metrics, "redis_ready")
        self.mark(metrics, "memory_loaded")

        agent = create_agent(memory, verbose=False)
        self.mark(metrics, "agent_created")
        self.active_agents[conversation_id] = agent

        full_response = ""
        stream_error = False

        try:
            self.mark(metrics, "model_request_started")
            async for event in agent.astream_events(
                {"input": question}, version="v2"
            ):
                kind = event.get("event", "")
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        full_response += token
                        if "first_model_token" not in metrics:
                            self.mark(metrics, "first_model_token")
                        yield f"data: {json.dumps({'content': token, 'done': False})}\n\n"
                        if "first_sse_yielded" not in metrics:
                            self.mark(metrics, "first_sse_yielded")
                        await asyncio.sleep(0)
                elif kind == "on_tool_error":
                    err = event.get("data", {}).get("error", "未知工具错误")
                    error_token = f"\n> ⚠️ 工具调用异常：{str(err)[:200]}\n"
                    full_response += error_token
                    yield f"data: {json.dumps({'content': error_token, 'done': False})}\n\n"
        except asyncio.TimeoutError:
            full_response = guard.fallback("empty_output")
            stream_error = True
        except Exception:
            full_response = guard.fallback("unknown")
            stream_error = True
        finally:
            self.active_agents.pop(conversation_id, None)

        if full_response and not stream_error:
            result = guard.validate(full_response)
            if result["used_fallback"] and result["text"] != full_response:
                yield f"data: {json.dumps({'content': chr(10) * 2 + result['text'], 'done': False})}\n\n"

        if stream_error:
            final_content = full_response
        elif full_response:
            final_content = guard.validate(full_response)["text"]
        else:
            final_content = guard.fallback("empty_output")
        await self.save_message(conversation_id, "assistant", final_content)

        timing = self.metric_payload(metrics)
        yield f"data: {json.dumps({'content': '', 'done': True, **timing})}\n\n"
        self.log_metrics(metrics)
