"""会话记忆：将最近对话写入 Redis，并在不可用时降级为空记忆。"""
import json

from langchain.memory import ConversationBufferMemory

from app.config import get_settings


settings = get_settings()
_redis_client = None
_redis_initialized = False


def _get_redis_client():
    global _redis_client, _redis_initialized
    if _redis_initialized:
        return _redis_client

    # 首次连接失败也记录结果，避免每个请求都重复进行短超时连接。
    _redis_initialized = True
    try:
        import redis

        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
        )
    except Exception:
        _redis_client = None
    return _redis_client


class RedisConversationMemory(ConversationBufferMemory):
    """Conversation memory with lazy, shared Redis access."""

    def __init__(self, conversation_id: str, ttl: int = 3600 * 24 * 7):
        super().__init__(memory_key="chat_history", return_messages=True)
        object.__setattr__(self, "conversation_id", conversation_id)
        object.__setattr__(self, "ttl", ttl)
        object.__setattr__(self, "redis_client", _get_redis_client())

    def load_from_db(self, messages: list[dict]):
        # 数据库是完整历史来源；Redis 只承担跨请求的热缓存。
        for msg in messages:
            if msg["role"] == "user":
                self.chat_memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                self.chat_memory.add_ai_message(msg["content"])

    def save_context(self, inputs: dict, outputs: dict):
        super().save_context(inputs, outputs)
        if self.redis_client:
            try:
                # 序列化 LangChain 消息后按会话维度写入并设置 TTL。
                key = f"memory:{self.conversation_id}"
                data = json.dumps(
                    [msg.to_json() for msg in self.chat_memory.messages],
                    default=str,
                )
                self.redis_client.setex(key, self.ttl, data)
            except Exception:
                pass

    def load_context(self):
        if self.redis_client:
            try:
                key = f"memory:{self.conversation_id}"
                data = self.redis_client.get(key)
                if data:
                    messages = json.loads(data)
                    for msg in messages:
                        msg_type = msg.get("type", "")
                        msg_content = msg.get("content", "")
                        if msg_type == "human":
                            self.chat_memory.add_user_message(msg_content)
                        elif msg_type == "ai":
                            self.chat_memory.add_ai_message(msg_content)
            except Exception:
                pass

    def clear(self):
        super().clear()
        if self.redis_client:
            try:
                self.redis_client.delete(f"memory:{self.conversation_id}")
            except Exception:
                pass
