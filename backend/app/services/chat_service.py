import json
import asyncio
from typing import AsyncGenerator
from sqlalchemy import select
from app.database import get_sessionmaker
from app.models.conversation import Conversation
from app.models.message import Message
from app.agent.base import create_agent
from app.agent.memory import RedisConversationMemory
from app.agent.guard import guard


class ChatService:
    def __init__(self):
        self.active_agents: dict[str, object] = {}

    async def get_or_create_conversation(self, conversation_id: str | None, title: str = "New Chat") -> str:
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

    async def save_message(self, conversation_id: str, role: str, content: str):
        async with get_sessionmaker()() as db:
            msg = Message(conversation_id=conversation_id, role=role, content=content)
            db.add(msg)
            await db.commit()

    async def _run_agent_with_retry(self, agent, question: str, max_retries: int = 2) -> str:
        """执行 Agent 并支持重试"""
        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                full_response = ""
                async for event in agent.astream_events(
                    {"input": question}, version="v2"
                ):
                    if event.get("event") == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            full_response += chunk.content

                # 护栏校验
                result = guard.validate(full_response)
                if not result["used_fallback"]:
                    return result["text"]

                # 兜底输出但看起来有效也接受
                if len(result["text"].strip()) > 10:
                    return result["text"]

                # 需要重试
                last_error = "output_validation_failed"
                if attempt < max_retries:
                    continue

            except Exception as e:
                last_error = str(e)[:200]
                if attempt < max_retries:
                    continue

        # 所有重试耗尽
        return guard.fallback("empty_output" if not last_error else "unknown")

    async def chat_stream(self, conversation_id: str, question: str) -> AsyncGenerator[str, None]:
        # 输入校验
        if not question or not question.strip():
            yield f"data: {json.dumps({'content': '请输入您的问题。', 'done': True})}\n\n"
            return
        if len(question) > 5000:
            yield f"data: {json.dumps({'content': '问题过长，请精简后重试（限5000字）。', 'done': True})}\n\n"
            return

        # 保存用户消息
        await self.save_message(conversation_id, "user", question)

        # 加载历史
        history_messages = await self.get_messages(conversation_id)
        memory = RedisConversationMemory(conversation_id=conversation_id)
        memory.load_from_db(history_messages[:-1])

        agent = create_agent(memory, verbose=False)
        self.active_agents[conversation_id] = agent

        full_response = ""
        stream_error = False

        try:
            async for event in agent.astream_events(
                {"input": question}, version="v2"
            ):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        full_response += token
                        yield f"data: {json.dumps({'content': token, 'done': False})}\n\n"
                        await asyncio.sleep(0)

                # 捕获工具调用异常
                elif kind == "on_tool_error":
                    err = event.get("data", {}).get("error", "未知工具错误")
                    error_token = f"\n> ⚠️ 工具调用异常：{str(err)[:200]}\n"
                    full_response += error_token
                    yield f"data: {json.dumps({'content': error_token, 'done': False})}\n\n"

        except asyncio.TimeoutError:
            full_response = guard.fallback("empty_output")
            stream_error = True
        except Exception as e:
            full_response = guard.fallback("unknown")
            stream_error = True
        finally:
            self.active_agents.pop(conversation_id, None)

        # 输出后护栏校验（仅对正常流式输出校验，不对 fallback 内容二次校验）
        if full_response and not stream_error:
            result = guard.validate(full_response)
            if result["used_fallback"] and result["text"] != full_response:
                # 兜底替换了整个输出，需要告知前端
                yield f"data: {json.dumps({'content': '\n\n' + result['text'], 'done': False})}\n\n"

        # 保存最终内容
        if stream_error:
            # 异常场景：full_response 已是 fallback 字符串，直接保存
            final_content = full_response
        elif full_response:
            # 正常场景：使用 validate 结果中的文本
            final_content = guard.validate(full_response)["text"]
        else:
            final_content = guard.fallback("empty_output")
        await self.save_message(conversation_id, "assistant", final_content)

        # 完成信号
        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
