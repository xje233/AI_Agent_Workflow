import json
from langchain.memory import ConversationBufferMemory
from app.config import get_settings

settings = get_settings()


class RedisConversationMemory(ConversationBufferMemory):
    """基于 Redis 的会话记忆，Redis 不可用时降级为纯内存模式"""

    def __init__(self, conversation_id: str, ttl: int = 3600 * 24 * 7):
        super().__init__(memory_key="chat_history", return_messages=True)
        object.__setattr__(self, "conversation_id", conversation_id)
        object.__setattr__(self, "ttl", ttl)

        redis_client = None
        try:
            import redis
            r = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)
            r.ping()  # 立即验证连接
            redis_client = r
        except Exception:
            print("[Memory] Redis unavailable, using in-memory mode")
        object.__setattr__(self, "redis_client", redis_client)

    def load_from_db(self, messages: list[dict]):
        for msg in messages:
            if msg["role"] == "user":
                self.chat_memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                self.chat_memory.add_ai_message(msg["content"])

    def save_context(self, inputs: dict, outputs: dict):
        super().save_context(inputs, outputs)
        if self.redis_client:
            try:
                key = f"memory:{self.conversation_id}"
                data = json.dumps(
                    [msg.to_json() for msg in self.chat_memory.messages],
                    default=str
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
                        # to_json() 输出格式: {"type": "human"/"ai", "content": "...", ...}
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
                key = f"memory:{self.conversation_id}"
                self.redis_client.delete(key)
            except Exception:
                pass
