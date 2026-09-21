"""应用配置：从环境变量加载模型、数据库和基础设施连接参数。"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # LLM
    openai_api_key: str = "sk-xxx"
    openai_base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o-mini"
    simple_chat_enabled: bool = True
    agent_max_exposed_tools: int = 3

    # Embedding（可独立配置，支持硅基流动等不同服务商）
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_model: str = "BAAI/bge-m3"

    # Database
    database_url: str = "postgresql+asyncpg://agent:agent123@localhost:5432/agent_workflow"
    database_url_sync: str = "postgresql://agent:agent123@localhost:5432/agent_workflow"
    database_query_timeout_seconds: float = 5.0

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Chroma
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_persist_dir: str = "./chroma_db"
    rag_relevance_threshold: float = 0.35
    rag_default_k: int = 4

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
