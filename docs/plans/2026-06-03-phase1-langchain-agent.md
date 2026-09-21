# Phase 1: LangChain Agent 基础版 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建 LangChain Agent 基础版，实现智能对话、RAG 知识库、工具调用、会话记忆、流式输出。

**Architecture:** FastAPI 后端 + LangChain ReAct Agent + Vue3 前端。后端通过 SSE 推送流式响应，Chroma 做向量存储，PostgreSQL 存业务数据，Redis 做会话缓存。

**Tech Stack:** Python 3.14, FastAPI, LangChain, Chroma, PostgreSQL, Redis, Vue3, Vite, Pinia, Element Plus, TypeScript

---

## 项目目录结构

```
ai-agent-workflow/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   └── document.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py
│   │   │   ├── knowledge.py
│   │   │   └── conversation.py
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── tools.py
│   │   │   └── memory.py
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── loader.py
│   │   │   ├── splitter.py
│   │   │   └── retriever.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── chat_service.py
│   ├── requirements.txt
│   ├── .env.example
│   └── uploads/
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── style.css
│       ├── router/index.ts
│       ├── stores/chat.ts
│       ├── stores/knowledge.ts
│       ├── api/request.ts
│       ├── api/chat.ts
│       ├── api/knowledge.ts
│       ├── composables/useSSE.ts
│       ├── composables/useMarkdown.ts
│       ├── types/chat.ts
│       ├── types/knowledge.ts
│       ├── views/HomeView.vue
│       ├── views/KnowledgeView.vue
│       └── components/
│           ├── chat/ChatWindow.vue
│           ├── chat/MessageBubble.vue
│           ├── chat/ChatInput.vue
│           ├── chat/HistorySidebar.vue
│           ├── knowledge/FileUploader.vue
│           ├── knowledge/DocList.vue
│           └── common/NavBar.vue
└── docker-compose.yml
```

---

### Task 1: 项目初始化与依赖配置

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `frontend/package.json`
- Create: `docker-compose.yml`

**Step 1: 创建后端 requirements.txt**

```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
langchain==0.3.14
langchain-openai==0.2.11
langchain-community==0.3.14
chromadb==0.5.23
sqlalchemy==2.0.36
asyncpg==0.30.0
psycopg2-binary==2.9.10
redis==5.2.1
python-multipart==0.0.19
python-dotenv==1.0.1
pydantic==2.10.4
pydantic-settings==2.7.1
sse-starlette==2.2.1
unstructured==0.16.16
pypdf==5.1.0
python-docx==1.1.2
markdown==3.7
tiktoken==0.8.0
beautifulsoup4==4.12.3
```

**Step 2: 创建前端 package.json**

```json
{
  "name": "ai-agent-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.13",
    "vue-router": "^4.5.0",
    "pinia": "^2.3.0",
    "element-plus": "^2.9.1",
    "@element-plus/icons-vue": "^2.3.1",
    "axios": "^1.7.9",
    "marked": "^15.0.4",
    "highlight.js": "^11.11.1",
    "@vueuse/core": "^12.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.1",
    "typescript": "^5.7.3",
    "vite": "^6.0.7",
    "vue-tsc": "^2.2.0",
    "tailwindcss": "^3.4.17",
    "postcss": "^8.4.49",
    "autoprefixer": "^10.4.20"
  }
}
```

**Step 3: 创建 docker-compose.yml**

```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: agent123
      POSTGRES_DB: agent_workflow
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

volumes:
  postgres_data:
  chroma_data:
```

**Step 4: 创建 .env.example**

```env
# LLM
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# Database
DATABASE_URL=postgresql+asyncpg://agent:agent123@localhost:5432/agent_workflow
DATABASE_URL_SYNC=postgresql://agent:agent123@localhost:5432/agent_workflow

# Redis
REDIS_URL=redis://localhost:6379/0

# Chroma
CHROMA_HOST=localhost
CHROMA_PORT=8001

# App
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true
```

---

### Task 2: 后端核心配置与数据库连接

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

**Step 1: 创建 config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    openai_api_key: str = "sk-xxx"
    openai_base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # Database
    database_url: str = "postgresql+asyncpg://agent:agent123@localhost:5432/agent_workflow"
    database_url_sync: str = "postgresql://agent:agent123@localhost:5432/agent_workflow"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Chroma
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_persist_dir: str = "./chroma_db"

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
```

**Step 2: 创建 database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

---

### Task 3: 数据库模型定义

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/models/message.py`
- Create: `backend/app/models/document.py`

**Step 1: 创建 user.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
```

**Step 2: 创建 conversation.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="新会话")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
```

**Step 3: 创建 message.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")
```

**Step 4: 创建 document.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    vector_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending|indexing|completed|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

---

### Task 4: RAG 知识库模块

**Files:**
- Create: `backend/app/rag/__init__.py`
- Create: `backend/app/rag/loader.py`
- Create: `backend/app/rag/splitter.py`
- Create: `backend/app/rag/retriever.py`

**Step 1: 创建 loader.py**

```python
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)
from langchain.schema import Document
from pathlib import Path


def load_document(file_path: str) -> list[Document]:
    """根据文件类型加载文档"""
    suffix = Path(file_path).suffix.lower()

    loader_map = {
        ".pdf": PyPDFLoader,
        ".docx": Docx2txtLoader,
        ".txt": TextLoader,
        ".md": UnstructuredMarkdownLoader,
    }

    loader_cls = loader_map.get(suffix)
    if not loader_cls:
        raise ValueError(f"不支持的文件类型: {suffix}")

    loader = loader_cls(file_path)
    return loader.load()
```

**Step 2: 创建 splitter.py**

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document


def split_documents(documents: list[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )
    return splitter.split_documents(documents)
```

**Step 3: 创建 retriever.py**

```python
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from app.config import get_settings

settings = get_settings()


def get_embeddings():
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
        openai_api_base=settings.openai_base_url,
    )


def get_vector_store(collection_name: str = "knowledge_base") -> Chroma:
    http_client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    embeddings = get_embeddings()
    return Chroma(
        client=http_client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )


def add_documents(documents: list[Document], collection_name: str = "knowledge_base"):
    vector_store = get_vector_store(collection_name)
    vector_store.add_documents(documents)


def similarity_search(query: str, k: int = 4) -> list[Document]:
    vector_store = get_vector_store()
    return vector_store.similarity_search(query, k=k)


def delete_documents(doc_ids: list[str]):
    vector_store = get_vector_store()
    vector_store.delete(ids=doc_ids)
```

---

### Task 5: Agent 工具定义

**Files:**
- Create: `backend/app/agent/__init__.py`
- Create: `backend/app/agent/tools.py`

**Step 1: 创建 tools.py**

```python
from langchain.tools import tool
from app.rag.retriever import similarity_search


@tool
def search_tool(query: str) -> str:
    """在企业知识库中搜索相关文档内容。当用户询问知识性问题时使用此工具。"""
    docs = similarity_search(query, k=4)
    if not docs:
        return "未找到相关文档。"
    results = []
    for i, doc in enumerate(docs, 1):
        results.append(f"[文档{i}] (来源: {doc.metadata.get('source', '未知')})\n{doc.page_content}")
    return "\n\n".join(results)


@tool
def query_db(sql: str) -> str:
    """执行SQL查询来获取结构化数据。用于查询数据库中的记录、统计信息等。"""
    # 模拟数据库查询
    return f"[SQL模拟] 查询: {sql}\n返回: 查询结果将在此展示（需连接真实数据库）"


@tool
def analyze_doc(file_name: str) -> str:
    """分析指定文档的内容，返回摘要和关键信息。"""
    return f"[文档分析] 文件: {file_name}\n内容摘要: 文档分析结果将在此展示"


@tool
def run_python(code: str) -> str:
    """安全执行Python代码并返回结果。用于数据处理和计算。"""
    # 注意: 生产环境需使用沙箱隔离
    import io
    import sys

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(code, {"__builtins__": {}})
        result = sys.stdout.getvalue()
    except Exception as e:
        result = f"执行错误: {str(e)}"
    finally:
        sys.stdout = old_stdout
    return result or "代码执行完成，无输出"


@tool
def send_email(content: str) -> str:
    """发送邮件通知。用于审批通知、结果分发等场景。"""
    return f"[邮件发送] 内容: {content[:100]}...\n邮件已发送（模拟）"


# 工具列表
ALL_TOOLS = [search_tool, query_db, analyze_doc, run_python, send_email]
```

---

### Task 6: 会话记忆管理

**Files:**
- Create: `backend/app/agent/memory.py`

**Step 1: 创建 memory.py**

```python
import json
import redis
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage
from app.config import get_settings

settings = get_settings()


class RedisConversationMemory(ConversationBufferMemory):
    """基于 Redis 的会话记忆，支持持久化和过期"""

    def __init__(self, conversation_id: str, ttl: int = 3600 * 24 * 7):
        super().__init__(memory_key="chat_history", return_messages=True)
        self.conversation_id = conversation_id
        self.ttl = ttl
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)

    def load_from_db(self, messages: list[dict]):
        """从数据库加载历史消息"""
        for msg in messages:
            if msg["role"] == "user":
                self.chat_memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                self.chat_memory.add_ai_message(msg["content"])

    def save_context(self, inputs: dict, outputs: dict):
        super().save_context(inputs, outputs)
        key = f"memory:{self.conversation_id}"
        data = json.dumps([msg.dict() for msg in self.chat_memory.messages], default=str)
        self.redis_client.setex(key, self.ttl, data)

    def load_context(self):
        key = f"memory:{self.conversation_id}"
        data = self.redis_client.get(key)
        if data:
            messages = json.loads(data)
            for msg in messages:
                if msg["type"] == "human":
                    self.chat_memory.add_user_message(msg["content"])
                elif msg["type"] == "ai":
                    self.chat_memory.add_ai_message(msg["content"])

    def clear(self):
        super().clear()
        key = f"memory:{self.conversation_id}"
        self.redis_client.delete(key)
```

---

### Task 7: LangChain Agent 核心

**Files:**
- Create: `backend/app/agent/base.py`

**Step 1: 创建 base.py**

```python
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.config import get_settings
from app.agent.tools import ALL_TOOLS
from app.agent.memory import RedisConversationMemory

settings = get_settings()


# ReAct Prompt 模板
REACT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一个企业级 AI Agent 工作流助手。你可以使用以下工具来帮助用户完成任务：

{tools}

请严格遵循以下格式回答问题：
Thought: 分析用户问题，思考需要做什么
Action: 要使用的工具名称，必须是 [{tool_names}] 之一
Action Input: 工具需要的输入参数
Observation: 工具返回的结果
... (这个 Thought/Action/Action Input/Observation 可以重复多次)
Thought: 我现在知道最终答案了
Final Answer: 给用户的最终回复

重要规则：
1. 始终使用中文回复
2. 先思考再行动
3. 使用工具时严格按照格式
4. 最终答案要清晰、结构化
5. 如果没有合适工具，直接回复 Final Answer
"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])


def get_llm(temperature: float = 0.7):
    return ChatOpenAI(
        model=settings.model_name,
        temperature=temperature,
        openai_api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


def create_agent(memory: RedisConversationMemory, temperature: float = 0.7):
    llm = get_llm(temperature)
    agent = create_react_agent(llm=llm, tools=ALL_TOOLS, prompt=REACT_PROMPT)
    return AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        memory=memory,
        verbose=settings.debug,
        handle_parsing_errors=True,
        max_iterations=10,
        max_execution_time=120,
    )
```

---

### Task 8: 聊天服务层

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/chat_service.py`

**Step 1: 创建 chat_service.py**

```python
import json
import asyncio
from typing import AsyncGenerator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain.callbacks import AsyncIteratorCallbackHandler
from app.database import async_session
from app.models.conversation import Conversation
from app.models.message import Message
from app.agent.base import create_agent
from app.agent.memory import RedisConversationMemory


class ChatService:
    def __init__(self):
        self.active_agents: dict[str, object] = {}

    async def get_or_create_conversation(self, conversation_id: str | None, title: str = "新会话") -> str:
        async with async_session() as db:
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
        async with async_session() as db:
            result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            messages = result.scalars().all()
            return [{"role": m.role, "content": m.content} for m in messages]

    async def save_message(self, conversation_id: str, role: str, content: str):
        async with async_session() as db:
            msg = Message(conversation_id=conversation_id, role=role, content=content)
            db.add(msg)
            await db.commit()

    async def chat_stream(self, conversation_id: str, question: str) -> AsyncGenerator[str, None]:
        # 保存用户消息
        await self.save_message(conversation_id, "user", question)

        # 加载历史消息
        history_messages = await self.get_messages(conversation_id)

        # 创建带记忆的 Agent
        memory = RedisConversationMemory(conversation_id=conversation_id)
        memory.load_from_db(history_messages[:-1])  # 不包含刚保存的用户消息

        agent = create_agent(memory)

        self.active_agents[conversation_id] = agent

        # 使用回调收集完整响应
        full_response = ""

        # 异步执行 Agent
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None, lambda: agent.invoke({"input": question})
            )
            full_response = result.get("output", "")
        except Exception as e:
            full_response = f"抱歉，处理您的请求时出现了错误：{str(e)}"
        finally:
            self.active_agents.pop(conversation_id, None)

        # 模拟流式输出（逐字符发送）
        for i in range(0, len(full_response), 5):
            chunk = full_response[i:i + 5]
            yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
            await asyncio.sleep(0.02)

        # 保存助手消息
        await self.save_message(conversation_id, "assistant", full_response)

        # 发送完成信号
        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
```

---

### Task 9: FastAPI API 路由

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/chat.py`
- Create: `backend/app/api/knowledge.py`
- Create: `backend/app/api/conversation.py`

**Step 1: 创建 chat.py**

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])

chat_service = ChatService()


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    conversation_id: str
    message: str


@router.post("/send")
async def send_message(req: ChatRequest) -> StreamingResponse:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    conversation_id = await chat_service.get_or_create_conversation(req.conversation_id)

    return StreamingResponse(
        chat_service.chat_stream(conversation_id, req.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-Id": conversation_id,
        },
    )


@router.post("/new")
async def new_conversation():
    conv_id = await chat_service.get_or_create_conversation(None, "新会话")
    return {"conversation_id": conv_id}
```

**Step 2: 创建 conversation.py**

```python
from fastapi import APIRouter
from sqlalchemy import select
from app.database import async_session
from app.models.conversation import Conversation

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations():
    async with async_session() as db:
        result = await db.execute(
            select(Conversation).order_by(Conversation.created_at.desc()).limit(50)
        )
        conversations = result.scalars().all()
        return [
            {"id": str(c.id), "title": c.title, "created_at": str(c.created_at)}
            for c in conversations
        ]


@router.get("/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    from app.services.chat_service import ChatService
    svc = ChatService()
    messages = await svc.get_messages(conversation_id)
    return {"messages": messages}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    async with async_session() as db:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            await db.delete(conv)
            await db.commit()
    return {"status": "ok"}
```

**Step 3: 创建 knowledge.py**

```python
import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy import select
from app.database import async_session
from app.models.document import Document as DocumentModel
from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.rag.retriever import add_documents

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    allowed_types = {".pdf", ".docx", ".txt", ".md"}
    suffix = os.path.splitext(file.filename)[1].lower()

    if suffix not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {suffix}")

    file_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    async with async_session() as db:
        doc = DocumentModel(
            filename=file.filename,
            file_path=save_path,
            file_type=suffix.lstrip("."),
            vector_status="pending",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        try:
            doc.vector_status = "indexing"
            await db.commit()

            documents = load_document(save_path)
            chunks = split_documents(documents)
            add_documents(chunks)

            doc.vector_status = "completed"
        except Exception as e:
            doc.vector_status = "failed"
            raise HTTPException(status_code=500, detail=f"索引失败: {str(e)}")
        finally:
            await db.commit()

    return {
        "id": str(doc.id),
        "filename": file.filename,
        "status": doc.vector_status,
    }


@router.get("/documents")
async def list_documents():
    async with async_session() as db:
        result = await db.execute(select(DocumentModel).order_by(DocumentModel.created_at.desc()))
        docs = result.scalars().all()
        return [
            {
                "id": str(d.id),
                "filename": d.filename,
                "file_type": d.file_type,
                "vector_status": d.vector_status,
                "created_at": str(d.created_at),
            }
            for d in docs
        ]


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    async with async_session() as db:
        result = await db.execute(select(DocumentModel).where(DocumentModel.id == doc_id))
        doc = result.scalar_one_or_none()
        if doc:
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
            await db.delete(doc)
            await db.commit()
    return {"status": "ok"}
```

---

### Task 10: FastAPI 主入口

**Files:**
- Create: `backend/app/main.py`

**Step 1: 创建 main.py**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api import chat, knowledge, conversation


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await init_db()
    yield


app = FastAPI(
    title="AI Agent Workflow Platform",
    description="企业级 AI Agent 工作流平台 - LangChain 版本",
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


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
```

---

### Task 11: 前端 Vite + Vue3 项目搭建

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/style.css`
- Create: `frontend/src/env.d.ts`

**Step 1: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Agent 工作流平台</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

**Step 2: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

**Step 3: 创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "paths": {
      "@/*": ["./src/*"]
    },
    "types": ["element-plus/global"]
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue", "src/env.d.ts"]
}
```

**Step 4: 创建 src/main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
```

**Step 5: 创建 src/App.vue**

```vue
<script setup lang="ts">
</script>

<template>
  <router-view />
</template>
```

---

### Task 12: 前端路由与类型定义

**Files:**
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/types/chat.ts`
- Create: `frontend/src/types/knowledge.ts`
- Create: `frontend/src/env.d.ts`

**Step 1: 创建 src/router/index.ts**

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { title: 'AI Agent 聊天' },
    },
    {
      path: '/knowledge',
      name: 'knowledge',
      component: () => import('@/views/KnowledgeView.vue'),
      meta: { title: '知识库管理' },
    },
  ],
})

export default router
```

**Step 2: 创建 src/types/chat.ts**

```typescript
export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export interface Conversation {
  id: string
  title: string
  created_at: string
}

export interface ChatRequest {
  conversation_id?: string
  message: string
}
```

**Step 3: 创建 src/types/knowledge.ts**

```typescript
export interface KnowledgeDocument {
  id: string
  filename: string
  file_type: string
  vector_status: 'pending' | 'indexing' | 'completed' | 'failed'
  created_at: string
}
```

---

### Task 13: API 封装层

**Files:**
- Create: `frontend/src/api/request.ts`
- Create: `frontend/src/api/chat.ts`
- Create: `frontend/src/api/knowledge.ts`

**Step 1: 创建 src/api/request.ts**

```typescript
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg = error.response?.data?.detail || '网络错误'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default request
```

**Step 2: 创建 src/api/chat.ts**

```typescript
import request from './request'
import type { Conversation, Message } from '@/types/chat'

export const chatApi = {
  getConversations(): Promise<Conversation[]> {
    return request.get('/conversations') as any
  },

  getMessages(conversationId: string): Promise<{ messages: Message[] }> {
    return request.get(`/conversations/${conversationId}/messages`) as any
  },

  deleteConversation(conversationId: string): Promise<any> {
    return request.delete(`/conversations/${conversationId}`)
  },

  newConversation(): Promise<{ conversation_id: string }> {
    return request.post('/chat/new')
  },
}
```

**Step 3: 创建 src/api/knowledge.ts**

```typescript
import request from './request'
import type { KnowledgeDocument } from '@/types/knowledge'

export const knowledgeApi = {
  upload(file: File): Promise<KnowledgeDocument> {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }) as any
  },

  getDocuments(): Promise<KnowledgeDocument[]> {
    return request.get('/knowledge/documents') as any
  },

  deleteDocument(docId: string): Promise<any> {
    return request.delete(`/knowledge/documents/${docId}`)
  },
}
```

---

### Task 14: Pinia 状态管理

**Files:**
- Create: `frontend/src/stores/chat.ts`
- Create: `frontend/src/stores/knowledge.ts`

**Step 1: 创建 src/stores/chat.ts**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatApi } from '@/api/chat'
import type { Message, Conversation } from '@/types/chat'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const currentId = ref<string | null>(null)
  const messages = ref<Message[]>([])
  const streaming = ref(false)
  const tokenCount = ref(0)

  async function loadConversations() {
    conversations.value = await chatApi.getConversations()
  }

  async function loadMessages(convId: string) {
    currentId.value = convId
    const res = await chatApi.getMessages(convId)
    messages.value = res.messages
  }

  async function newConversation() {
    const res = await chatApi.newConversation()
    currentId.value = res.conversation_id
    messages.value = []
    await loadConversations()
  }

  async function deleteConversation(convId: string) {
    await chatApi.deleteConversation(convId)
    if (currentId.value === convId) {
      currentId.value = null
      messages.value = []
    }
    await loadConversations()
  }

  function addMessage(msg: Message) {
    messages.value.push(msg)
  }

  function updateLastMessage(content: string) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content += content
    }
  }

  return {
    conversations, currentId, messages, streaming, tokenCount,
    loadConversations, loadMessages, newConversation, deleteConversation,
    addMessage, updateLastMessage,
  }
})
```

**Step 2: 创建 src/stores/knowledge.ts**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { knowledgeApi } from '@/api/knowledge'
import type { KnowledgeDocument } from '@/types/knowledge'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const documents = ref<KnowledgeDocument[]>([])
  const uploading = ref(false)

  async function loadDocuments() {
    documents.value = await knowledgeApi.getDocuments()
  }

  async function uploadDocument(file: File) {
    uploading.value = true
    try {
      await knowledgeApi.upload(file)
      await loadDocuments()
    } finally {
      uploading.value = false
    }
  }

  async function deleteDocument(docId: string) {
    await knowledgeApi.deleteDocument(docId)
    await loadDocuments()
  }

  return { documents, uploading, loadDocuments, uploadDocument, deleteDocument }
})
```

---

### Task 15: Composables

**Files:**
- Create: `frontend/src/composables/useSSE.ts`
- Create: `frontend/src/composables/useMarkdown.ts`

**Step 1: 创建 src/composables/useSSE.ts**

```typescript
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { Message } from '@/types/chat'

export function useSSE() {
  const store = useChatStore()
  const abortController = ref<AbortController | null>(null)

  async function sendMessage(content: string) {
    store.addMessage({ role: 'user', content })
    store.addMessage({ role: 'assistant', content: '' })
    store.streaming = true

    abortController.value = new AbortController()

    try {
      const response = await fetch('/api/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: store.currentId,
          message: content,
        }),
        signal: abortController.value.signal,
      })

      if (!response.ok) throw new Error('请求失败')

      // 获取 conversation_id
      const convId = response.headers.get('X-Conversation-Id')
      if (convId) store.currentId = convId

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n').filter((l) => l.startsWith('data: '))

        for (const line of lines) {
          const data = JSON.parse(line.slice(6))
          if (data.done) {
            store.streaming = false
          } else {
            store.updateLastMessage(data.content)
          }
        }
      }

      store.streaming = false
      await store.loadConversations()
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        store.streaming = false
        store.updateLastMessage('\n\n[请求出错，请重试]')
      }
    }
  }

  function stopStreaming() {
    abortController.value?.abort()
    store.streaming = false
  }

  return { sendMessage, stopStreaming }
}
```

**Step 2: 创建 src/composables/useMarkdown.ts**

```typescript
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

marked.setOptions({
  highlight: (code: string, lang: string) => {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true,
})

export function useMarkdown() {
  function render(markdown: string): string {
    return marked.parse(markdown) as string
  }

  return { render }
}
```

---

### Task 16: Vue3 视图页面

**Files:**
- Create: `frontend/src/views/HomeView.vue`
- Create: `frontend/src/views/KnowledgeView.vue`
- Create: `frontend/src/components/common/NavBar.vue`
- Create: `frontend/src/components/chat/ChatWindow.vue`
- Create: `frontend/src/components/chat/MessageBubble.vue`
- Create: `frontend/src/components/chat/ChatInput.vue`
- Create: `frontend/src/components/chat/HistorySidebar.vue`
- Create: `frontend/src/components/knowledge/FileUploader.vue`
- Create: `frontend/src/components/knowledge/DocList.vue`

**Step 1: 创建 NavBar.vue**

```vue
<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const navItems = [
  { path: '/', label: 'AI 对话' },
  { path: '/knowledge', label: '知识库' },
]
</script>

<template>
  <el-menu
    :default-active="route.path"
    mode="horizontal"
    :ellipsis="false"
    @select="(key: string) => router.push(key)"
  >
    <div class="nav-brand">
      <el-icon :size="24"><Cpu /></el-icon>
      <span>AI Agent 工作流平台</span>
    </div>
    <div class="flex-grow" />
    <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
      {{ item.label }}
    </el-menu-item>
  </el-menu>
</template>

<style scoped>
.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  font-size: 18px;
  font-weight: 700;
  color: #409eff;
}
.flex-grow {
  flex: 1;
}
</style>
```

**Step 2: 创建 HomeView.vue**

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import NavBar from '@/components/common/NavBar.vue'
import HistorySidebar from '@/components/chat/HistorySidebar.vue'
import ChatWindow from '@/components/chat/ChatWindow.vue'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()

onMounted(() => {
  store.loadConversations()
})
</script>

<template>
  <div class="home-container">
    <NavBar />
    <div class="home-body">
      <HistorySidebar />
      <ChatWindow />
    </div>
  </div>
</template>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.home-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}
</style>
```

**Step 3: 创建 ChatWindow.vue**

```vue
<script setup lang="ts">
import { nextTick, watch, ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSSE } from '@/composables/useSSE'
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'

const store = useChatStore()
const { sendMessage, stopStreaming } = useSSE()
const messagesContainer = ref<HTMLElement>()

watch(
  () => store.messages.length,
  async () => {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  }
)

async function handleSend(content: string) {
  if (!store.currentId) {
    await store.newConversation()
  }
  await sendMessage(content)
}
</script>

<template>
  <div class="chat-window">
    <div ref="messagesContainer" class="messages-container">
      <div v-if="!store.currentId" class="welcome-message">
        <el-icon :size="64" color="#c0c4cc"><ChatDotRound /></el-icon>
        <h2>AI Agent 工作流助手</h2>
        <p>选择一个会话或创建新会话开始对话</p>
      </div>

      <div v-else-if="store.messages.length === 0" class="welcome-message">
        <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p>开始你的第一个问题</p>
      </div>

      <MessageBubble
        v-for="(msg, i) in store.messages"
        :key="i"
        :message="msg"
        :streaming="store.streaming && i === store.messages.length - 1 && msg.role === 'assistant'"
      />
    </div>

    <ChatInput
      :disabled="!store.currentId"
      :streaming="store.streaming"
      @send="handleSend"
      @stop="stopStreaming"
    />
  </div>
</template>

<style scoped>
.chat-window {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
.welcome-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  gap: 12px;
}
.welcome-message h2 {
  margin: 0;
  color: #303133;
}
</style>
```

**Step 4: 创建 MessageBubble.vue**

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useMarkdown } from '@/composables/useMarkdown'
import type { Message } from '@/types/chat'

const props = defineProps<{
  message: Message
  streaming: boolean
}>()

const { render } = useMarkdown()

const htmlContent = computed(() => render(props.message.content))
</script>

<template>
  <div class="message-bubble" :class="message.role">
    <div class="message-avatar">
      <el-icon v-if="message.role === 'user'" :size="24"><UserFilled /></el-icon>
      <el-icon v-else :size="24"><Cpu /></el-icon>
    </div>
    <div class="message-content">
      <div class="message-role">{{ message.role === 'user' ? '你' : 'AI Agent' }}</div>
      <div class="markdown-body" v-html="htmlContent" />
      <span v-if="streaming" class="typing-cursor">|</span>
    </div>
  </div>
</template>

<style scoped>
.message-bubble {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 85%;
}
.message-bubble.user {
  margin-left: auto;
  flex-direction: row-reverse;
}
.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #409eff;
  color: white;
  flex-shrink: 0;
}
.message-bubble.user .message-avatar {
  background: #67c23a;
}
.message-role {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.message-content {
  padding: 12px 16px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.message-bubble.user .message-content {
  background: #409eff;
  color: white;
}
.typing-cursor {
  animation: blink 1s infinite;
  font-weight: bold;
}
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
```

**Step 5: 创建 ChatInput.vue**

```vue
<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  disabled: boolean
  streaming: boolean
}>()
const emit = defineEmits<{ send: [content: string]; stop: [] }>()

const input = ref('')
const textarea = ref<any>()

function handleSend() {
  const content = input.value.trim()
  if (!content || props.streaming) return
  emit('send', content)
  input.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="chat-input-bar">
    <div class="input-wrapper">
      <el-input
        ref="textarea"
        v-model="input"
        type="textarea"
        :rows="2"
        maxlength="4000"
        show-word-limit
        placeholder="输入消息，Enter 发送，Shift+Enter 换行"
        :disabled="disabled"
        @keydown="handleKeydown"
      />
      <el-button
        v-if="!streaming"
        type="primary"
        :icon="'Promotion'"
        :disabled="!input.trim() || disabled"
        @click="handleSend"
      >
        发送
      </el-button>
      <el-button v-else type="danger" @click="emit('stop')">
        停止生成
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.chat-input-bar {
  padding: 16px 24px;
  background: white;
  border-top: 1px solid #e4e7ed;
}
.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
</style>
```

**Step 6: 创建 HistorySidebar.vue**

```vue
<script setup lang="ts">
import { useChatStore } from '@/stores/chat'

const store = useChatStore()

function selectConversation(id: string) {
  store.loadMessages(id)
}
</script>

<template>
  <div class="history-sidebar">
    <div class="sidebar-header">
      <h3>历史会话</h3>
      <el-button type="primary" size="small" @click="store.newConversation()">
        <el-icon><Plus /></el-icon>
        新会话
      </el-button>
    </div>

    <div class="conversation-list">
      <div
        v-for="conv in store.conversations"
        :key="conv.id"
        class="conversation-item"
        :class="{ active: conv.id === store.currentId }"
        @click="selectConversation(conv.id)"
      >
        <el-icon><ChatLineSquare /></el-icon>
        <span class="conv-title">{{ conv.title }}</span>
        <el-button
          type="danger"
          link
          size="small"
          class="delete-btn"
          @click.stop="store.deleteConversation(conv.id)"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>

      <div v-if="store.conversations.length === 0" class="empty-hint">
        暂无会话，点击上方按钮创建
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e4e7ed;
}
.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
}
.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.conversation-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.conversation-item:hover {
  background: #f5f7fa;
}
.conversation-item.active {
  background: #ecf5ff;
  color: #409eff;
}
.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
}
.conversation-item:hover .delete-btn {
  opacity: 1;
}
.empty-hint {
  text-align: center;
  padding: 40px 16px;
  color: #c0c4cc;
  font-size: 14px;
}
</style>
```

**Step 7: 创建 KnowledgeView.vue**

```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import NavBar from '@/components/common/NavBar.vue'
import FileUploader from '@/components/knowledge/FileUploader.vue'
import DocList from '@/components/knowledge/DocList.vue'
import { useKnowledgeStore } from '@/stores/knowledge'

const store = useKnowledgeStore()

onMounted(() => {
  store.loadDocuments()
})
</script>

<template>
  <div class="knowledge-container">
    <NavBar />
    <div class="knowledge-body">
      <div class="knowledge-header">
        <h2>知识库管理</h2>
        <p>上传文档构建企业知识库，支持 PDF、Word、Markdown、TXT 格式</p>
        <FileUploader />
      </div>
      <DocList />
    </div>
  </div>
</template>

<style scoped>
.knowledge-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.knowledge-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 40px;
  background: #f5f7fa;
}
.knowledge-header {
  margin-bottom: 24px;
}
.knowledge-header h2 {
  margin: 0 0 8px;
}
.knowledge-header p {
  color: #909399;
  margin: 0 0 16px;
}
</style>
```

**Step 8: 创建 FileUploader.vue**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useKnowledgeStore } from '@/stores/knowledge'
import { ElMessage } from 'element-plus'

const store = useKnowledgeStore()
const uploadRef = ref<any>()

const allowedTypes = ['.pdf', '.docx', '.txt', '.md']

async function handleUpload(options: any) {
  await store.uploadDocument(options.file)
}
</script>

<template>
  <el-upload
    ref="uploadRef"
    drag
    :auto-upload="false"
    :accept="allowedTypes.join(',')"
    :http-request="handleUpload"
    :show-file-list="false"
    :disabled="store.uploading"
  >
    <el-icon :size="48" color="#c0c4cc"><UploadFilled /></el-icon>
    <div class="upload-text">
      <p>拖拽文件到此处或 <em>点击上传</em></p>
      <p class="hint">支持 PDF、Word、Markdown、TXT</p>
    </div>
  </el-upload>
</template>

<style scoped>
.upload-text p {
  margin: 4px 0;
  color: #606266;
}
.upload-text .hint {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
```

**Step 9: 创建 DocList.vue**

```vue
<script setup lang="ts">
import { useKnowledgeStore } from '@/stores/knowledge'

const store = useKnowledgeStore()

const statusMap: Record<string, { label: string; type: string }> = {
  pending: { label: '待索引', type: 'info' },
  indexing: { label: '索引中', type: 'warning' },
  completed: { label: '已索引', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

const fileIcons: Record<string, string> = {
  pdf: 'Document',
  docx: 'Document',
  doc: 'Document',
  txt: 'Tickets',
  md: 'Notebook',
}
</script>

<template>
  <el-table :data="store.documents" style="width: 100%" v-loading="store.uploading">
    <el-table-column label="文件名" min-width="300">
      <template #default="{ row }">
        <div class="file-cell">
          <el-icon :size="20"><component :is="fileIcons[row.file_type] || 'Document'" /></el-icon>
          <span>{{ row.filename }}</span>
        </div>
      </template>
    </el-table-column>
    <el-table-column label="类型" width="100">
      <template #default="{ row }">
        <el-tag size="small">{{ row.file_type.toUpperCase() }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="120">
      <template #default="{ row }">
        <el-tag :type="statusMap[row.vector_status]?.type || 'info'">
          {{ statusMap[row.vector_status]?.label || row.vector_status }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="上传时间" width="180">
      <template #default="{ row }">
        {{ new Date(row.created_at).toLocaleString('zh-CN') }}
      </template>
    </el-table-column>
    <el-table-column label="操作" width="100">
      <template #default="{ row }">
        <el-button type="danger" link size="small" @click="store.deleteDocument(row.id)">
          删除
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<style scoped>
.file-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
```

---

### Task 17: 前端启动配置与样式

**Files:**
- Create: `frontend/src/style.css`

**Step 1: 创建 src/style.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* Markdown 渲染样式 */
.markdown-body h1, .markdown-body h2, .markdown-body h3 {
  margin: 16px 0 8px;
  font-weight: 600;
}
.markdown-body h1 { font-size: 1.5em; }
.markdown-body h2 { font-size: 1.3em; }
.markdown-body h3 { font-size: 1.1em; }
.markdown-body p { margin: 8px 0; line-height: 1.7; }
.markdown-body ul, .markdown-body ol { padding-left: 20px; margin: 8px 0; }
.markdown-body li { margin: 4px 0; }
.markdown-body code {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}
.markdown-body pre {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}
.markdown-body pre code {
  background: transparent;
  padding: 0;
  color: inherit;
}
.markdown-body blockquote {
  border-left: 4px solid #409eff;
  padding-left: 16px;
  color: #606266;
  margin: 12px 0;
}
.markdown-body table {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
}
.markdown-body th, .markdown-body td {
  border: 1px solid #e4e7ed;
  padding: 8px 12px;
  text-align: left;
}
.markdown-body th {
  background: #f5f7fa;
  font-weight: 600;
}

/* 滚动条 */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #c0c4cc; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #909399; }
```

---

## 启动检查清单

1. 启动 Docker 服务:
```bash
docker-compose up -d
```

2. 安装后端依赖并启动:
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 填写 API Key
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. 安装前端依赖并启动:
```bash
cd frontend
npm install
npm run dev
```

4. 访问 http://localhost:3000
