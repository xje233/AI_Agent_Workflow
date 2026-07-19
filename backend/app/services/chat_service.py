import asyncio
import json
import time
import uuid
from typing import AsyncGenerator

from sqlalchemy import select
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.base import SYSTEM_PROMPT, create_agent, get_llm
from app.agent.guard import guard
from app.agent.memory import RedisConversationMemory
from app.agent.tools import ALL_TOOLS, select_tools
from app.config import get_settings
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
    def count_tokens(value: str) -> int:
        try:
            import tiktoken

            encoding = tiktoken.encoding_for_model(get_settings().model_name)
        except Exception:
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
            except Exception:
                return 0
        return len(encoding.encode(value))

    @classmethod
    def tool_token_count(cls, tools: list) -> int:
        schemas = []
        for tool in tools:
            schema = getattr(tool, "args_schema", None)
            if schema is not None:
                try:
                    schema = schema.model_json_schema()
                except AttributeError:
                    schema = schema.schema()
            schemas.append({"name": tool.name, "description": tool.description, "schema": schema})
        return cls.count_tokens(json.dumps(schemas, ensure_ascii=False, default=str))

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
            "history_token_count": metrics.get("history_token_count", 0),
            "system_prompt_token_count": metrics.get("system_prompt_token_count", 0),
            "tool_count": metrics.get("tool_count", 0),
            "tool_definition_token_count": metrics.get("tool_definition_token_count", 0),
            "model_call_count": metrics.get("model_call_count", 0),
            "tool_call_count": metrics.get("tool_call_count", 0),
            "first_tool_call_at_ms": metrics.get("first_tool_call_at_ms"),
            "durations_ms": durations,
            "backend_model_ttft_ms": round(
                (metrics["first_model_token"] - metrics["model_request_started"])
                * 1000,
                2,
            )
            if "first_model_token" in metrics
            else None,
            "backend_sse_enqueue_ttft_ms": round(
                (metrics["first_sse_enqueued"] - metrics["model_request_started"])
                * 1000,
                2,
            )
            if "first_sse_enqueued" in metrics and "model_request_started" in metrics
            else None,
            "backend_sse_ttft_ms": round(
                (metrics["first_sse_enqueued"] - metrics["model_request_started"])
                * 1000,
                2,
            )
            if "first_sse_enqueued" in metrics and "model_request_started" in metrics
            else None,
            "backend_model_to_sse_ms": round(
                (metrics["first_sse_enqueued"] - metrics["first_model_token"])
                * 1000,
                2,
            )
            if "first_sse_enqueued" in metrics and "first_model_token" in metrics
            else None,
            "backend_request_to_sse_ms": round(
                (metrics["first_sse_enqueued"] - start) * 1000, 2
            )
            if "first_sse_enqueued" in metrics
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

        tools = select_tools(question)
        simple_chat = get_settings().simple_chat_enabled and tools is ALL_TOOLS
        if simple_chat:
            tools = []
        metrics["tool_count"] = len(tools)
        metrics["tool_definition_token_count"] = self.tool_token_count(tools)
        metrics["system_prompt_token_count"] = self.count_tokens(SYSTEM_PROMPT)
        metrics["history_token_count"] = self.count_tokens(
            "\n".join(message["content"] for message in history_messages)
        )

        memory = RedisConversationMemory(conversation_id=conversation_id)
        memory.load_from_db(history_messages)
        self.mark(metrics, "redis_ready")
        self.mark(metrics, "memory_loaded")

        agent = None
        if not simple_chat:
            agent = create_agent(memory, verbose=False, tools=tools)
            self.mark(metrics, "agent_created")
            self.active_agents[conversation_id] = agent

        full_response = ""
        stream_error = False

        try:
            self.mark(metrics, "model_request_started")
            if simple_chat:
                metrics["model_call_count"] = 1
                messages = [SystemMessage(content=SYSTEM_PROMPT)]
                for message in history_messages:
                    messages.append(
                        HumanMessage(content=message["content"])
                        if message["role"] == "user"
                        else AIMessage(content=message["content"])
                    )
                messages.append(HumanMessage(content=question))
                async for chunk in get_llm().astream(messages):
                    token = chunk.content if hasattr(chunk, "content") else ""
                    if token:
                        full_response += token
                        if "first_model_token" not in metrics:
                            self.mark(metrics, "first_model_token")
                        if "first_sse_enqueued" not in metrics:
                            self.mark(metrics, "first_sse_enqueued")
                        yield f"data: {json.dumps({'content': token, 'done': False})}\n\n"
                        await asyncio.sleep(0)
            else:
                async for event in agent.astream_events(
                    {"input": question}, version="v2"
                ):
                    kind = event.get("event", "")
                    if kind == "on_chat_model_start":
                        metrics["model_call_count"] = metrics.get("model_call_count", 0) + 1
                    elif kind == "on_tool_start":
                        metrics["tool_call_count"] = metrics.get("tool_call_count", 0) + 1
                        if "first_tool_call_at_ms" not in metrics:
                            metrics["first_tool_call_at_ms"] = round(
                                (time.perf_counter() - metrics["request_received"]) * 1000,
                                2,
                            )
                    if kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            token = chunk.content
                            full_response += token
                            if "first_model_token" not in metrics:
                                self.mark(metrics, "first_model_token")
                            if "first_sse_enqueued" not in metrics:
                                self.mark(metrics, "first_sse_enqueued")
                            yield f"data: {json.dumps({'content': token, 'done': False})}\n\n"
                            await asyncio.sleep(0)
                    elif kind == "on_tool_error":
                        err = event.get("data", {}).get("error", "tool error")
                        error_token = f"\n> Tool error: {str(err)[:200]}\n"
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
