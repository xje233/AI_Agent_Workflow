"""共享 LLM HTTP 客户端：在应用生命周期内复用连接池。"""
import httpx


_client: httpx.AsyncClient | None = None


def create_client() -> httpx.AsyncClient:
    # 模型请求复用 keep-alive 连接，并限制连接数避免高并发时无限扩张。
    return httpx.AsyncClient(
        limits=httpx.Limits(
            max_keepalive_connections=10,
            max_connections=50,
            keepalive_expiry=30,
        ),
        timeout=httpx.Timeout(120.0, connect=5.0),
    )


def get_client() -> httpx.AsyncClient | None:
    return _client


async def startup() -> None:
    global _client
    if _client is None:
        # 应用启动阶段创建一次；业务请求仅获取现成客户端。
        _client = create_client()


async def shutdown() -> None:
    global _client
    if _client is not None:
        # 显式关闭连接池，避免热重载或进程退出时遗留 socket。
        await _client.aclose()
        _client = None
