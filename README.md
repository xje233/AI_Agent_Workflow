# 企业级 AI Agent 工作流平台

基于 **LangChain** + **FastAPI** + **React** 构建的企业级 AI Agent 工作流平台，支持多轮对话、RAG 知识库、工具调用、流式输出。

> 当前阶段：**Phase 1 — LangChain Agent 基础版** ✅

---

## 系统架构

```
┌──────────────────────────────────────┐
│       前端 (React + Vite + TS)        │
│   Zustand + Ant Design + TailwindCSS  │
└────────────────┬─────────────────────┘
                 │ SSE / REST
                 ▼
┌──────────────────────────────────────┐
│         FastAPI Gateway              │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│    LangChain Agent (ReAct 模式)       │
│  ┌──────────┬──────────┬──────────┐  │
│  │  Tools   │   RAG    │  Memory  │  │
│  │ (5个工具) │(知识检索) │(Redis)   │  │
│  └──────────┴──────────┴──────────┘  │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  PostgreSQL + Redis + Chroma         │
└──────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| **LLM** | DeepSeek / OpenAI / 任意兼容接口 |
| **Agent** | LangChain ReAct Agent + Tool Calling |
| **后端** | FastAPI + SSE 流式 + Pydantic |
| **数据库** | PostgreSQL (SQLAlchemy async) + Redis + Chroma |
| **前端** | React + Vite + Zustand + Ant Design + TypeScript |
| **RAG** | LangChain Loader → RecursiveCharacterTextSplitter → Chroma |
| **部署** | Docker Compose |

## 项目结构

```
ai-agent-workflow/
├── docker-compose.yml
├── README.md
├── PRE.md                          # 项目需求文档
├── backend/
│   ├── requirements.txt
│   ├── .env                        # 环境变量配置
│   └── app/
│       ├── main.py                 # FastAPI 入口 (lifespan + CORS)
│       ├── config.py               # Pydantic Settings 配置
│       ├── database.py             # SQLAlchemy 异步引擎
│       ├── models/                 # ORM 模型
│       │   ├── user.py
│       │   ├── conversation.py
│       │   ├── message.py
│       │   └── document.py
│       ├── rag/                    # RAG 知识库模块
│       │   ├── loader.py           # 文档加载 (PDF/Word/MD/TXT)
│       │   ├── splitter.py         # RecursiveCharacterTextSplitter
│       │   └── retriever.py        # Chroma 向量存储与检索
│       ├── agent/                  # LangChain Agent 模块
│       │   ├── base.py             # ReAct Agent 核心
│       │   ├── tools.py            # 5 个内置工具
│       │   └── memory.py           # Redis 会话记忆
│       ├── services/
│       │   └── chat_service.py     # 聊天服务 (SSE 流式响应)
│       └── api/                    # REST API 路由
│           ├── chat.py             # 对话接口
│           ├── conversation.py     # 会话管理
│           └── knowledge.py        # 知识库管理
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    └── src/
        ├── main.tsx                # React 入口
        ├── App.vue
        ├── router/index.ts         # 路由 (/, /knowledge)
        ├── stores/                 # Zustand 状态管理
        │   ├── chat.ts
        │   └── knowledge.ts
        ├── api/                    # Axios 封装
        │   ├── request.ts
        │   ├── chat.ts
        │   └── knowledge.ts
        ├── composables/            # 组合函数
        │   ├── useSSE.ts           # SSE 流式接收
        │   └── useMarkdown.ts      # Markdown 渲染
        ├── types/                  # TypeScript 类型
        │   ├── chat.ts
        │   └── knowledge.ts
        ├── views/                  # 页面
        │   ├── HomeView.vue        # AI 对话首页
        │   └── KnowledgeView.vue   # 知识库管理
        └── components/
            ├── common/NavBar.vue
            ├── chat/
            │   ├── ChatWindow.vue
            │   ├── MessageBubble.vue
            │   ├── ChatInput.vue
            │   └── HistorySidebar.vue
            └── knowledge/
                ├── FileUploader.vue
                └── DocList.vue
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- Docker Desktop

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `.env` 填入 LLM API 密钥：

```env
# 以 DeepSeek 为例（国内可用）
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat

# 也支持 OpenAI / 硅基流动 / Qwen 等任何兼容接口
# OPENAI_BASE_URL=https://api.openai.com/v1
# MODEL_NAME=gpt-4o-mini
# OPENAI_BASE_URL=https://api.siliconflow.cn/v1
# MODEL_NAME=deepseek-ai/DeepSeek-V3
```

### 3. 启动基础设施

```bash
docker-compose up -d
```

启动 PostgreSQL (`:5432`)、Redis (`:6379`)、Chroma (`:8001`)。

### 4. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:3000

## API 接口

### 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/chat/send` | 发送消息，返回 SSE 流式响应 |
| `POST` | `/api/chat/new` | 创建新会话 |

**发送消息示例：**
```json
// POST /api/chat/send
{
  "conversation_id": null,
  "message": "帮我生成一份数据库优化方案"
}

// 响应 (SSE text/event-stream):
data: {"content": "我来帮", "done": false}
data: {"content": "您分析", "done": false}
...
data: {"content": "", "done": true}
```

### 会话

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/conversations` | 获取历史会话列表 |
| `GET` | `/api/conversations/{id}/messages` | 获取会话消息记录 |
| `DELETE` | `/api/conversations/{id}` | 删除会话 |

### 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/knowledge/upload` | 上传文档 (PDF/Word/MD/TXT) |
| `GET` | `/api/knowledge/documents` | 文档列表 |
| `DELETE` | `/api/knowledge/documents/{id}` | 删除文档 |

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 服务状态 |

## 已实现功能

### Phase 1 — LangChain Agent 基础版 ✅

- [x] **多轮对话** — 上下文感知的智能问答
- [x] **流式输出** — 基于 SSE 的实时推送
- [x] **RAG 知识库** — 文档上传、自动切片、向量化、语义检索
- [x] **5 个内置工具** — 知识搜索、SQL 查询、文档分析、Python 执行、邮件发送
- [x] **会话记忆** — Redis 持久化的 ConversationBufferMemory
- [x] **历史会话管理** — 会话列表、消息回溯、删除
- [x] **React 前端** — Ant Design 组件库、Zustand 状态管理、SSE 流式渲染
- [x] **Markdown 渲染** — 代码高亮、表格、引用等

### 后续阶段

| 阶段 | 状态 | 内容 |
|------|------|------|
| Phase 2 | 🔜 | React 前端完善（工作流监控页等） |
| Phase 3 | 🔜 | LangGraph 工作流升级（StateGraph、Checkpoint、Human-in-the-Loop） |
| Phase 4 | 🔜 | 多 Agent 协作 |
| Phase 5 | 🔜 | 生产部署（Docker 化、鉴权、日志） |

## 内置 Agent 工具

| 工具 | 功能 |
|------|------|
| `search_tool` | 在企业知识库中语义搜索 |
| `query_db` | 执行 SQL 查询 |
| `analyze_doc` | 分析指定文档内容 |
| `run_python` | 安全执行 Python 代码 |
| `send_email` | 发送邮件通知 |

---

> 详见 `PRE.md` 了解完整项目需求与技术方案。
## Frontend Stack

The frontend is implemented with React 18, TypeScript, Vite, React Router 6, Zustand, and Ant Design. It keeps the existing REST and Server-Sent Events API contracts.
