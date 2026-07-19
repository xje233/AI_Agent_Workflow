# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目状态

这是一个企业级 AI Agent 工作流平台，目前处于 Phase 1。已实现的主要链路是：Vue 3 前端通过 REST 和 Server-Sent Events（SSE）与 FastAPI 后端通信。后端同时包含 LangChain 对话 Agent 链路，以及正在完善中的 LangGraph 工作流链路。

`PRE.md` 描述完整目标架构和后续阶段；`README.md` 是当前已实现 Phase 1 行为的主要参考文档。

## 开发命令

请在对应目录执行命令。

### 基础设施

在仓库根目录启动 PostgreSQL、Redis、Chroma，以及可选的容器化后端：

```bash
docker-compose up -d
```

Compose 中的后端和本地 Uvicorn 后端都会占用 `8000` 端口，不要同时启动。停止服务：

```bash
docker-compose down
```

### 后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文档地址是 `http://localhost:8000/docs`，健康检查接口是 `GET /api/health`。

后端从 `backend/.env` 读取配置。首次使用时，将 `backend/.env.example` 复制为 `backend/.env`，然后配置 OpenAI 兼容的 LLM 接口和 Embedding 接口，才能使用 Agent 和 RAG 功能。不要替换或提交真实凭据。

当 PostgreSQL 不可用时，`backend/app/database.py` 会自动回退到 SQLite，并使用 `backend/data/agent.db`，因此本地 API 开发仍可启动。会话记忆和向量检索功能仍分别需要 Redis 和 Chroma。

当前仓库没有配置后端测试套件、测试命令、格式化工具或 lint 工具。不要凭空添加不存在的命令；后端改动应根据需要通过 API 或针对性的 Python 检查进行验证。

### 前端

```bash
cd frontend
npm install
npm run dev
```

Vite 开发服务器运行在 `http://localhost:3000`，并将 `/api` 请求代理到 `http://localhost:8000`。

构建并进行前端类型检查：

```bash
npm run build
```

预览生产构建：

```bash
npm run preview
```

`frontend/package.json` 当前没有配置前端测试或 lint 脚本。

## 系统架构

### 请求与服务流转

`backend/app/main.py` 创建 FastAPI 应用，在生命周期启动阶段初始化数据库元数据，配置开发环境下的 CORS，并注册 `backend/app/api/` 中的路由。

`backend/app/api/chat.py` 中的聊天接口负责获取或创建会话，并返回 SSE `StreamingResponse`。`backend/app/services/chat_service.py` 负责保存用户消息和助手消息、重建会话记忆、创建 LangChain Agent、流式处理模型和工具事件，以及通过 `backend/app/agent/guard.py` 执行输出校验和兜底处理。

会话和知识库接口使用 `backend/app/database.py` 中的异步 SQLAlchemy 会话工厂。ORM 模型位于 `backend/app/models/`。

### LangChain Agent 链路

主要聊天 Agent 在 `backend/app/agent/base.py` 中组装，使用面向 OpenAI 兼容接口的 `ChatOpenAI` 和 `create_tool_calling_agent`。系统提示词规定了中文和 Markdown 输出格式、业务边界、来源标注以及反幻觉规则。

工具定义在 `backend/app/agent/tools.py` 中，并统一收集到 `ALL_TOOLS`。RAG 搜索委托给 `backend/app/rag/retriever.py`；其他工具目前包含模拟的数据库、文档和邮件行为，以及受限的 Python 执行实现。除非明确修改并完成验证，否则应将这些非 RAG 工具视为开发阶段占位实现。

RAG 链路为：加载器 -> 文本切分器 -> Chroma 检索器：

- `backend/app/rag/loader.py` 加载 PDF、DOCX、Markdown 和文本文件。
- `backend/app/rag/splitter.py` 创建递归文本分块。
- `backend/app/rag/retriever.py` 创建 Embedding 并访问 Chroma。

`backend/app/agent/memory.py` 提供基于 Redis 的会话记忆；数据库仍然是已持久化会话消息的来源。

### LangGraph 工作流链路

`backend/app/agent/workflow.py` 定义 `WorkflowState` 和线性图：

`START -> analyze -> research -> execute -> review -> END`

节点实现位于 `backend/app/agent/workflow_nodes.py`，负责结构化规划、检索与研究、答案生成以及护栏和审核处理。工作流检查点通过 `AsyncSqliteSaver` 保存到 `backend/data/workflow_checkpoints.db`。工作流相关路由和服务位于 `backend/app/api/workflow.py` 与 `backend/app/services/workflow_service.py`。

修改功能时，应保持 LangChain 聊天链路和 LangGraph 工作流链路在概念上的分离；配置、RAG、模型和输出护栏是两条链路之间预期的共享集成点。

### 前端链路

`frontend/src/main.ts` 注册 Vue、Pinia、Element Plus 和路由。路由定义在 `frontend/src/router/index.ts`，包括聊天页（`/`）、知识库管理页（`/knowledge`）和工作流页（`/workflow`）。

`frontend/src/stores/` 中的 Pinia Store 管理聊天和知识库状态。`frontend/src/api/` 中的 API 封装使用 `/api` 作为基础路径。聊天流式响应由 `frontend/src/composables/useSSE.ts` 使用 `fetch` 和 SSE 解析实现；Markdown 渲染由 `useMarkdown.ts` 处理。页面位于 `frontend/src/views/`，通过 `frontend/src/components/` 下的组件进行组合。

## 修改约束

- 保持现有异步边界：FastAPI 路由、服务和 SQLAlchemy 数据库操作是异步的，而部分 LangChain/RAG 操作在内部仍是同步的。
- 保持 API 响应结构与 TypeScript 类型以及 `useSSE.ts` 消费的 SSE 格式一致：每个事件应为 `data: {"content": ..., "done": ...}`，并以空行结束。
- 修改配置时，如果配置项需要用户设置，应同时更新 `backend/app/config.py` 和 `backend/.env.example`。
- 新增文档格式时，需要同时修改 `backend/app/api/knowledge.py` 中的上传校验，以及 `backend/app/rag/loader.py` 中的加载器映射。
- `.codebuddy/rules/功能开发.mdc` 规定开发新功能或迭代已有功能时使用仓库配置的 superpowers 工作流；相关插件可用时应遵循该工作流。
