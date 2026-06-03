# 企业级 AI Agent 工作流平台 — 项目需求与工程文档 (PRE)

---

## 一、项目背景

随着大模型（LLM）快速发展，企业越来越希望利用 AI 提升知识管理、文档处理、业务自动化等工作效率。传统聊天机器人仅能完成简单问答，而企业场景往往需要：

- 知识库检索
- 多步骤任务规划
- 外部工具调用
- 人工审批
- 长期记忆管理
- 流程追踪与审计

因此，本项目设计并实现一个基于 **LangChain** 与 **LangGraph** 的企业级 AI Agent 工作流平台。

### 项目分两个阶段

| 阶段 | 方案 | 核心能力 |
|------|------|----------|
| **第一阶段** | LangChain 版本 | 多轮对话、工具调用、RAG知识库、会话记忆、流式输出 |
| **第二阶段** | LangGraph 版本 | 状态管理、工作流编排、Checkpoint恢复、Human-in-the-Loop、多Agent协作、长期记忆管理 |

通过两个版本的实现，展示从 **Agent Prototype → Production Agent** 的完整演进过程。

---

## 二、项目目标

构建一个企业知识工作流助手，帮助用户完成：

- 企业知识查询
- 文档分析
- 方案生成
- 数据查询
- 工单处理
- 流程审批

### 核心工作链路

```
用户需求 → 任务规划 → 知识检索 → 工具调用 → 结果生成 → 人工审批 → 结果归档
```

---

## 三、系统架构

### 整体架构图

```
┌──────────────────────────────────────┐
│              前端系统                  │
│     Vue3 + Vite + TypeScript +       │
│     Pinia + Vue Router + Element Plus │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│         FastAPI Gateway              │
│     (RESTful + WebSocket/SSE)        │
└────────────────┬─────────────────────┘
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
┌─────────────┐     ┌──────────────┐
│ LangChain版  │     │ LangGraph版   │
│ Agent       │     │ Workflow     │
│             │     │ Agent        │
└──────┬──────┘     └──────┬───────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌──────────────┐
│  Tool Layer │     │  Tool Layer  │
└──────┬──────┘     └──────┬───────┘
       │                   │
       └─────────┬─────────┘
                 ▼
┌──────────────────────────────────────┐
│  PostgreSQL + Redis + VectorDB       │
│  (pgvector / Chroma)                 │
└──────────────────────────────────────┘
```

### 技术栈总览

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | `Vue3 + Vite + TypeScript` | 组件化 SPA 应用 |
| **状态管理** | `Pinia` | Vue3 官方推荐 |
| **路由** | `Vue Router 4` | SPA 路由 |
| **UI 组件库** | `Element Plus` | 企业级 Vue3 组件库 |
| **样式方案** | `TailwindCSS` / `UnoCSS` | 原子化 CSS |
| **HTTP 客户端** | `Axios` / `ofetch` | API 请求 |
| **图表** | `ECharts` / `Chart.js` | 工作流监控可视化 |
| **后端** | `FastAPI` (Python) | API 网关 |
| **Agent 框架** | `LangChain` + `LangGraph` | Agent 核心 |
| **LLM** | `OpenAI / Qwen / DeepSeek` | 大模型 |
| **向量数据库** | `Chroma` (开发) / `pgvector` (生产) | 向量存储 |
| **关系数据库** | `PostgreSQL` | 业务数据 |
| **缓存** | `Redis` | 会话缓存、流式队列 |
| **部署** | `Docker Compose` | 容器化部署 |

---

## 四、核心功能设计

### 4.1 智能对话

- 多轮上下文管理
- 流式回复 (SSE/WebSocket)
- Token 统计
- 历史会话管理

**示例交互流程：**

```
用户：「帮我生成一份数据库优化方案」

Agent：
  1. 分析需求
  2. 检索知识库
  3. 查询案例
  4. 输出优化方案
```

### 4.2 RAG 知识库

| 功能 | 实现方案 |
|------|----------|
| **文档上传** | PDF、Word、Markdown、TXT |
| **文档解析** | LangChain Loader |
| **文本切分** | RecursiveCharacterTextSplitter |
| **Embedding** | OpenAI Embedding / BGE-M3 / Qwen Embedding |
| **向量存储** | Chroma (开发版) / pgvector (生产版) |

### 4.3 Agent 工具调用

| 工具 | 说明 |
|------|------|
| `search_tool` | 搜索工具 |
| `query_db` | SQL 查询工具 |
| `analyze_doc` | 文档分析工具 |
| `run_python` | Python 执行工具 |
| `send_email` | 邮件发送工具 |

### 4.4 会话记忆

| 版本 | 实现 | 能力 |
|------|------|------|
| **LangChain 版** | `ConversationBufferMemory` | 最近对话、用户偏好 |
| **LangGraph 版** | `Memory Store` | 短期记忆、长期记忆、用户画像 |

### 4.5 文件分析

用户上传 PDF / Word / Excel，Agent 自动完成：

- 内容提取
- 摘要生成
- 风险分析
- 报告生成

### 4.6 工作流执行（LangGraph 版本新增）

```
开始 → 需求分析 → 任务规划 → 知识检索 → 工具调用 → 结果校验 → 人工审批 → 输出结果 → 结束
```

---

## 五、LangChain 实现方案

### Agent 架构（ReAct 模式）

```
用户输入 → Prompt → LLM → Tool Calling → Observation → Final Answer
```

### 技术特点

- 开发快，上手简单
- 适合 PoC 验证（原型验证）

### 局限

- 状态管理较弱
- 流程复杂度有限

---

## 六、LangGraph 实现方案

### Graph 结构

```
START → Planner Node → Retriever Node → Executor Node → Validator Node → Human Review Node → END
```

### State 定义

```python
class AgentState(TypedDict):
    question: str
    plan: str
    documents: list
    tool_results: list
    final_answer: str
```

### Checkpoint 机制

保存节点状态：

- 当前节点
- 当前状态
- 历史执行记录

支持：

- 中断恢复
- 失败重试
- 流程回放

### Human-in-the-Loop

在关键节点引入人工审批：

```
审批通过 → 继续执行
审批拒绝 → 重新规划
```

**应用场景：** 合同审核、方案审批、财务流程

---

## 七、前端设计（Vue3 技术栈）

### 7.1 技术选型

| 类别 | 技术 | 原方案 | 说明 |
|------|------|--------|------|
| **框架** | `Vue 3.4+` | 原 Next.js/React | Composition API + `<script setup>` |
| **构建工具** | `Vite 5` | 原 Next.js | 极速 HMR 开发体验 |
| **语言** | `TypeScript` | 同 | 类型安全 |
| **状态管理** | `Pinia` | - | Vue3 官方状态管理 |
| **路由** | `Vue Router 4` | - | SPA 路由 |
| **UI 组件库** | `Element Plus` | 原 Shadcn UI | 企业级 Vue3 组件库 |
| **样式** | `TailwindCSS` | 同 | 原子化 CSS |
| **图表** | `ECharts 5` | - | 工作流可视化 |
| **HTTP** | `Axios` | - | API 请求 |
| **Markdown** | `marked + highlight.js` | - | 流式 Markdown 渲染 |

### 7.2 项目结构

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── package.json
├── src/
│   ├── main.ts                  # 入口文件
│   ├── App.vue                  # 根组件
│   ├── router/
│   │   └── index.ts             # Vue Router 配置
│   ├── stores/
│   │   ├── chat.ts              # 对话状态 (Pinia)
│   │   ├── knowledge.ts         # 知识库状态
│   │   ├── workflow.ts          # 工作流状态
│   │   └── user.ts              # 用户状态
│   ├── api/
│   │   ├── chat.ts              # 对话 API
│   │   ├── knowledge.ts         # 知识库 API
│   │   ├── workflow.ts          # 工作流 API
│   │   └── request.ts           # Axios 封装
│   ├── composables/
│   │   ├── useSSE.ts            # SSE 流式接收
│   │   ├── useMarkdown.ts       # Markdown 渲染
│   │   └── useFileUpload.ts     # 文件上传
│   ├── views/
│   │   ├── HomeView.vue         # 首页 (聊天)
│   │   ├── WorkflowView.vue     # 工作流监控
│   │   ├── KnowledgeView.vue    # 知识库管理
│   │   └── LoginView.vue        # 登录页
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatWindow.vue   # 聊天窗口
│   │   │   ├── MessageBubble.vue# 消息气泡
│   │   │   ├── ChatInput.vue    # 输入框
│   │   │   └── HistorySidebar.vue# 历史会话
│   │   ├── workflow/
│   │   │   ├── WorkflowGraph.vue# 工作流图
│   │   │   ├── NodeCard.vue     # 节点卡片
│   │   │   └── ApprovalDialog.vue# 审批弹窗
│   │   ├── knowledge/
│   │   │   ├── FileUploader.vue # 文件上传
│   │   │   ├── DocList.vue      # 文档列表
│   │   │   └── IndexStatus.vue  # 索引状态
│   │   └── common/
│   │       ├── NavBar.vue       # 导航栏
│   │       ├── TokenStats.vue   # Token 统计
│   │       └── LoadingOverlay.vue# 加载层
│   └── types/
│       ├── chat.ts              # 对话类型
│       ├── workflow.ts          # 工作流类型
│       └── knowledge.ts         # 知识库类型
```

### 7.3 路由设计

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | `HomeView` | Agent 聊天窗口 + 文件上传 + 历史会话 |
| `/workflow` | `WorkflowView` | 工作流监控：节点状态、Tool 调用、Token 消耗 |
| `/knowledge` | `KnowledgeView` | 知识库管理：上传/删除文档、重建索引 |
| `/login` | `LoginView` | 用户登录 |

### 7.4 页面设计

#### 首页 — Agent 聊天

```
┌──────────────┬──────────────────────────────┐
│  历史会话列表  │     Agent 聊天窗口             │
│              │                              │
│  ○ 会话A     │  用户: 帮我生成数据库优化方案    │
│  ○ 会话B     │                              │
│  ○ 会话C     │  Agent: 【分析需求】→【检索】    │
│              │         →【查询案例】→【输出】   │
│  + 新会话    │                              │
│              │  ┌──────────────────────┐    │
│              │  │ 📎 上传文件  输入消息  ➤│    │
│              │  └──────────────────────┘    │
└──────────────┴──────────────────────────────┘
```

#### 工作流监控页

```
┌──────────────────────────────────────────────┐
│  工作流执行状态                                │
│                                              │
│  Planner ✅  →  Retriever ✅  →  Executor 🔄  │
│                                  (运行中)     │
│  →  Validator ⏳  →  Human Review ⏳          │
│         (等待)            (等待)              │
│                                              │
│  ┌─────────────────────────────┐             │
│  │ 实时信息                     │             │
│  │ • 当前节点: Executor        │             │
│  │ • Tool调用: query_db        │             │
│  │ • Token消耗: 1,234 tokens   │             │
│  │ • 执行耗时: 2.3s            │             │
│  └─────────────────────────────┘             │
└──────────────────────────────────────────────┘
```

#### 知识库管理页

```
┌──────────────────────────────────────────────┐
│  知识库管理                                    │
│                                              │
│  [ 上传文档 ]  [ 批量删除 ]  [ 重建索引 ]       │
│                                              │
│  ┌─────────────────────────────────────┐     │
│  │ 📄 数据库优化指南.pdf    ✅ 已索引   │     │
│  │ 📄 API接口文档.doc       ✅ 已索引   │     │
│  │ 📄 架构设计.md           🔄 索引中   │     │
│  │ 📄 测试报告.txt          ❌ 未索引   │     │
│  └─────────────────────────────────────┘     │
│                                              │
│  Embedding 状态: 256/260 chunks              │
└──────────────────────────────────────────────┘
```

### 7.5 Pinia Store 设计

```typescript
// stores/chat.ts
interface ChatState {
  conversations: Conversation[]
  currentId: string | null
  messages: Message[]
  streaming: boolean
  tokenCount: number
}

// stores/workflow.ts
interface WorkflowState {
  nodes: WorkflowNode[]
  currentStep: string
  status: 'idle' | 'running' | 'paused' | 'completed'
  logs: WorkflowLog[]
}

// stores/knowledge.ts
interface KnowledgeState {
  documents: Document[]
  indexStatus: IndexInfo
  uploading: boolean
}
```

### 7.6 API 通信设计

```typescript
// api/chat.ts
export const chatApi = {
  // 发送消息 (支持 SSE 流式)
  sendMessage(data: SendMessageReq): Promise<ReadableStream>
  // 获取历史会话
  getConversations(): Promise<Conversation[]>
  // 获取会话消息
  getMessages(convId: string): Promise<Message[]>
}

// api/workflow.ts
export const workflowApi = {
  // 启动工作流
  startWorkflow(question: string): Promise<string>
  // 获取状态
  getStatus(workflowId: string): Promise<WorkflowStatus>
  // 人工审批
  approve(workflowId: string, decision: boolean): Promise<void>
}

// api/knowledge.ts
export const knowledgeApi = {
  // 上传文档
  upload(file: File): Promise<Document>
  // 删除文档
  delete(docId: string): Promise<void>
  // 重建索引
  rebuildIndex(): Promise<void>
}
```

---

## 八、数据库设计

### ER 图概要

| 表 | 主要字段 | 说明 |
|----|----------|------|
| `users` | id, username, email, created_at | 用户表 |
| `conversations` | id, user_id, title, created_at | 会话表 |
| `messages` | id, conversation_id, role, content, created_at | 消息表 |
| `documents` | id, filename, vector_status, created_at | 文档表 |
| `workflow_logs` | id, workflow_id, node_name, status, execution_time | 工作流日志表 |

### DDL 概要

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    role VARCHAR(20) NOT NULL,  -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(500) NOT NULL,
    vector_status VARCHAR(50) DEFAULT 'pending',  -- 'pending'|'indexing'|'completed'|'failed'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE workflow_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL,
    node_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'pending'|'running'|'completed'|'failed'
    execution_time INTERVAL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 九、项目亮点

### 技术亮点

| 领域 | 展示内容 |
|------|----------|
| **Vue3 工程化** | Composition API、Pinia 状态管理、Vite 构建、TypeScript |
| **LangChain Agent** | Tool Calling、RAG、Memory |
| **LangGraph Workflow** | State Management、Workflow、Checkpoint、Human-in-the-Loop |
| **LangSmith** | Tracing、Evaluation、Debugging |
| **RAG 系统** | Embedding、Retrieval、Rerank |
| **工程化能力** | Docker 部署、Redis 缓存、PostgreSQL、API 设计、权限管理 |

---

## 十、LangChain vs LangGraph 对比

| 能力 | LangChain | LangGraph |
|------|-----------|-----------|
| Tool Calling | ✅ | ✅ |
| RAG | ✅ | ✅ |
| 多步骤流程 | 一般 | **强** |
| 状态管理 | 弱 | **强** |
| Checkpoint | ❌ | ✅ |
| 人工审批 | ❌ | ✅ |
| 多 Agent 协作 | 一般 | **强** |

### 面试讲解要点

- **为什么先做 LangChain？** — 快速验证 Agent 能力，适合 MVP / 原型验证
- **为什么升级到 LangGraph？** — 解决多步骤任务、状态管理、流程恢复、人工介入等问题

---

## 十一、未来优化方向

1. **Multi-Agent 系统** — Planner Agent、Research Agent、Coding Agent、Review Agent 协同工作
2. **MCP 支持** — 接入数据库 MCP、GitHub MCP、企业系统 MCP，实现标准化工具生态
3. **长期记忆系统** — 用户画像、偏好学习、个性化推荐
4. **SaaS 化部署** — 多租户、企业知识库、权限管理、Agent 市场

---

## 十二、预期收获

通过本项目可以向面试官展示：

1. LLM 应用开发能力
2. LangChain 开发能力
3. LangGraph 开发能力
4. RAG 系统设计能力
5. Agent 工作流设计能力
6. Python 后端开发能力
7. Vue3 前端开发能力（替代原 React）
8. AI 系统工程化能力

**对标岗位：** Agent 开发工程师 / AI 应用开发工程师 / LLM 工程师 / AI 平台工程师

---

## 十三、开发计划

| 阶段 | 任务 | 说明 |
|------|------|------|
| **Phase 1** | LangChain Agent 基础版 | 对话、RAG、Tool Calling、Memory |
| **Phase 2** | Vue3 前端搭建 | Vite + Pinia + Element Plus 完整前端 |
| **Phase 3** | LangGraph 工作流升级 | StateGraph、Checkpoint、Human-in-the-Loop |
| **Phase 4** | 工作流监控 + 知识库管理 | 可视化监控面板、文档管理 |
| **Phase 5** | 生产部署 | Docker 化、API 鉴权、日志监控 |
