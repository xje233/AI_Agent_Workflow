import httpx


_client: httpx.AsyncClient | None = None


def create_client() -> httpx.AsyncClient:
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
        _client = create_client()


async def shutdown() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
