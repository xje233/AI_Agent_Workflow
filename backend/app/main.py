from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api import chat, knowledge, conversation, workflow


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


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
