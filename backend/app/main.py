"""FastAPI 应用入口：初始化基础设施并注册各业务路由。"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.database import init_db
from app.api import chat, knowledge, conversation, workflow
from app.agent.llm_client import shutdown as shutdown_llm_client
from app.agent.llm_client import startup as startup_llm_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在接收请求前完成持久化层和共享 HTTP 客户端的初始化。
    await init_db()
    await startup_llm_client()
    try:
        yield
    finally:
        # 服务关闭时释放连接池，避免重载后遗留连接。
        await shutdown_llm_client()


app = FastAPI(
    title="AI Agent Workflow Platform",
    description="企业级 AI Agent 工作流平台 - LangChain + LangGraph 双引擎",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(conversation.router)
app.include_router(knowledge.router)
app.include_router(workflow.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ── 生产模式：前端静态文件服务 ──────────────────────────────
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    import logging
    logger = logging.getLogger("uvicorn")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """为 SPA 提供静态文件服务，API 路由优先于本回退规则。"""
        file_path = _frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_dist / "index.html"))

    logger.info("前端静态文件服务已启用: %s", _frontend_dist)
else:
    import logging
    logger = logging.getLogger("uvicorn")
    logger.info("未发现前端构建产物 %s，仅提供 API 服务", _frontend_dist)
