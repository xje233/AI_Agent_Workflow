"""RAG 向量检索模块 — 异步接口 + 客户端缓存 + 参数修正"""
import asyncio
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from app.config import get_settings

settings = get_settings()

# ── 客户端缓存（避免每次操作都重建连接和 embedding_function）──
_chroma_client = None
_embeddings = None
_vector_store_cache: dict[str, Chroma] = {}


def _get_chroma_client() -> chromadb.ClientAPI:
    """获取 ChromaDB 客户端（优先 HTTP → 回退本地持久化），全局缓存"""
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    try:
        client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        client.heartbeat()
        _chroma_client = client
        print("[Chroma] HTTP client connected")
    except Exception:
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        print("[Chroma] HTTP unavailable, fallback to PersistentClient")

    return _chroma_client


def get_embeddings() -> OpenAIEmbeddings:
    """获取 Embedding 实例（全局缓存）"""
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    api_key = settings.embedding_api_key or settings.openai_api_key
    base_url = settings.embedding_base_url or settings.openai_base_url

    _embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=api_key,
        base_url=base_url,  # 修正：openai_api_base 已废弃，使用 base_url
    )
    return _embeddings


def get_vector_store(collection_name: str = "knowledge_base") -> Chroma:
    """获取 Chroma 向量库实例（按 collection 缓存）"""
    if collection_name in _vector_store_cache:
        return _vector_store_cache[collection_name]

    client = _get_chroma_client()
    embeddings = get_embeddings()
    vs = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )
    _vector_store_cache[collection_name] = vs
    return vs


async def add_documents(documents: list[Document], collection_name: str = "knowledge_base"):
    """异步添加文档到向量库（在 event loop 中运行同步 Chroma 操作）"""
    vector_store = get_vector_store(collection_name)
    # Chroma.add_documents 是同步的，通过 run_in_executor 避免阻塞 event loop
    await asyncio.to_thread(vector_store.add_documents, documents)


async def similarity_search(query: str, k: int = 4, collection_name: str = "knowledge_base") -> list[Document]:
    """异步相似度检索"""
    vector_store = get_vector_store(collection_name)
    # Chroma SDK 为同步接口，移入线程后避免阻塞 FastAPI 事件循环。
    return await asyncio.to_thread(vector_store.similarity_search, query, k=k)


async def delete_documents(doc_ids: list[str], collection_name: str = "knowledge_base"):
    """异步删除向量库中的文档"""
    vector_store = get_vector_store(collection_name)
    await asyncio.to_thread(vector_store.delete, ids=doc_ids)
