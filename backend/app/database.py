import socket
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings, BASE_DIR

settings = get_settings()

_engine = None
_sessionmaker = None


class Base(DeclarativeBase):
    pass


def _pg_is_available() -> bool:
    """用 socket 检测 PostgreSQL 是否可达（无需 asyncio）"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 5432))
        sock.close()
        return result == 0
    except Exception:
        return False


def get_engine():
    global _engine, _sessionmaker
    if _engine is not None:
        return _engine

    if _pg_is_available():
        _engine = create_async_engine(settings.database_url, echo=settings.debug)
        print("[DB] PostgreSQL connected")
    else:
        import os
        sqlite_path = BASE_DIR / "data" / "agent.db"
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite+aiosqlite:///{sqlite_path}"
        _engine = create_async_engine(db_url, echo=settings.debug)
        print(f"[DB] PostgreSQL unavailable, fallback to SQLite: {sqlite_path}")

    _sessionmaker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine


def get_sessionmaker():
    return _sessionmaker or async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    sm = get_sessionmaker()
    async with sm() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
