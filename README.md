# 企业级 AI Agent 工作流平台

基于 LangChain、LangGraph、FastAPI 和 React 构建的 AI Agent 工作流平台，提供流式聊天、RAG 知识库与多步骤工作流执行能力。

## 技术栈

- 前端：React 18、Vite、TypeScript、Zustand、Ant Design、Tailwind CSS
- 后端：FastAPI、SQLAlchemy Async、SSE
- AI：LangChain、LangGraph、OpenAI 兼容 LLM / Embedding 接口
- 基础设施：PostgreSQL、Redis、Chroma

## 已实现功能

- 多轮聊天与 SSE 流式输出
- 会话创建、历史消息查询与删除
- PDF、DOCX、TXT、Markdown 文档上传、分块与向量检索
- LangGraph 工作流：分析 → 检索 → 执行 → 审查
- 工作流 SQLite checkpoint 持久化
- Markdown 渲染与代码高亮
- 内置 Agent 工具：知识检索、SQL 查询、文档分析、受限 Python 执行、邮件发送

## 项目结构

```text
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI 路由
│   │   ├── agent/        # LangChain 与 LangGraph
│   │   ├── services/     # 聊天和工作流服务
│   │   ├── rag/          # 文档加载、分块、向量检索
│   │   ├── models/       # SQLAlchemy ORM 模型
│   │   ├── config.py
│   │   └── main.py
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── hooks/
│       ├── pages/
│       └── stores/
└── docker-compose.yml
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Docker Desktop（用于 PostgreSQL、Redis、Chroma）

### 1. 配置后端环境变量

在 Windows PowerShell 中：

```powershell
Copy-Item backend/.env.example backend/.env
```

编辑 `backend/.env`，至少设置以下 LLM 配置：

```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini
```

Embedding 可单独配置；留空的 `EMBEDDING_API_KEY` 和 `EMBEDDING_BASE_URL` 会复用 LLM 配置：

```env
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
EMBEDDING_MODEL=BAAI/bge-m3
```

### 2. 启动基础设施

```powershell
docker-compose up -d postgres redis chroma
```

服务端口：

- PostgreSQL：`5432`
- Redis：`6379`
- Chroma：`8001`

### 3. 启动后端

```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 API 文档：<http://localhost:8000/docs>

> `docker-compose up -d` 会同时启动容器化后端；它与本地 Uvicorn 都使用 `8000` 端口，请二选一。

### 4. 启动前端

另开一个终端：

```powershell
cd frontend
npm install
npm run dev
```

访问应用：<http://localhost:3000>

生产构建：

```powershell
npm run build
```

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/chat/send` | 发送消息，返回 SSE 流 |
| POST | `/api/chat/new` | 创建会话 |
| GET | `/api/conversations` | 查询会话列表 |
| GET | `/api/conversations/{conversation_id}/messages` | 查询会话消息 |
| DELETE | `/api/conversations/{conversation_id}` | 删除会话 |
| POST | `/api/knowledge/upload` | 上传 PDF、DOCX、TXT 或 Markdown 文档 |
| GET | `/api/knowledge/documents` | 查询知识库文档 |
| DELETE | `/api/knowledge/documents/{doc_id}` | 删除知识库文档 |
| POST | `/api/workflow/start` | 启动工作流，返回 SSE 节点事件 |
| GET | `/api/workflow/status/{thread_id}` | 查询工作流状态 |
| GET | `/api/workflow/history` | 查询工作流历史（当前为占位接口） |
| GET | `/api/health` | 健康检查 |

## 运行说明与限制

- PostgreSQL 不可用时，后端自动回退到 `backend/data/agent.db`；Redis 会话缓存与 Chroma 向量检索仍需对应服务可用。
- 工作流 checkpoint 保存在 `backend/data/workflow_checkpoints.db`。
- `query_db` 已接入应用数据库，仅允许查询 `conversations`、`messages`、`documents` 白名单表和字段，单次最多返回 100 行并有 5 秒超时；`analyze_doc` 与 `send_email` 仍是开发阶段的模拟工具。
- `run_python` 采用受限内建函数与关键字过滤，不可访问网络和文件系统。
- 请勿提交 `backend/.env` 或真实 API 密钥。

更多技术规划见 [PRE.md](PRE.md)。
