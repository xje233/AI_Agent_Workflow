# Phase 2: LangGraph Workflow 升级 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现有 LangChain Agent 基础上新增 LangGraph 工作流引擎，实现多步骤任务编排（Analyze → Research → Execute → Review），支持 Checkpoint 状态持久化和 SSE 流式节点进度推送。

**Architecture:** 新增独立端点 `POST /api/workflow/start`，通过 LangGraph StateGraph 编排 4 个节点。原 `POST /api/chat/send`（LangChain Agent）保持不变。Checkpointer 使用 SQLite（SqliteSaver），前端通过 SSE 实时展示节点执行状态。

**Tech Stack:** LangGraph, StateGraph, SqliteSaver, FastAPI SSE, Vue3 + Element Plus

**Design Decisions:**
- LangGraph 独立端点，与 LangChain Agent 并存
- 4 节点：Analyze → Research → Execute → Review
- SQLite Checkpointer（后续可升级 PG）
- SSE 流式推送节点状态
- 暂不做 Human-in-the-Loop / 用户认证

---

## 项目目录变更

```
backend/app/
├── agent/
│   ├── workflow.py          ← NEW: LangGraph StateGraph 定义
│   └── workflow_nodes.py    ← NEW: 4 个节点函数
├── services/
│   └── workflow_service.py  ← NEW: 工作流服务层 (SSE流式)
├── api/
│   └── workflow.py          ← NEW: /api/workflow 路由
├── main.py                  ← MODIFY: 注册 workflow router
frontend/src/
├── router/index.ts          ← MODIFY: 添加 /workflow 路由
├── types/
│   └── workflow.ts          ← NEW: 工作流类型定义
├── stores/
│   └── workflow.ts          ← NEW: 工作流 Pinia Store
├── api/
│   └── workflow.ts          ← NEW: 工作流 API 封装
├── composables/
│   └── useWorkflowSSE.ts    ← NEW: 工作流 SSE 处理
├── views/
│   └── WorkflowView.vue     ← NEW: 工作流执行页面
├── components/
│   └── workflow/
│       ├── WorkflowPanel.vue   ← NEW: 工作流可视化面板
│       └── NodeStatusCard.vue  ← NEW: 节点状态卡片
backend/requirements.txt     ← MODIFY: 添加 langgraph
```

---

### Task 1: 添加 LangGraph 依赖

**Files:**
- Modify: `backend/requirements.txt` — 添加 langgraph 包

**Step 1: 修改 requirements.txt**

在 `langchain-core` 之后添加：
```txt
langgraph>=0.2.0,<0.4.0
langgraph-checkpoint-sqlite>=2.0.0
```

**Step 2: 安装依赖**

```bash
cd backend && ..\.venv\Scripts\pip.exe install langgraph langgraph-checkpoint-sqlite
```

**验证：**
```bash
..\.venv\Scripts\python.exe -c "from langgraph.graph import StateGraph; print('OK')"
```

---

### Task 2: 创建工作流节点

**Files:**
- Create: `backend/app/agent/workflow_nodes.py`
- Create: `backend/app/agent/__init__.py` — 追加导出（如已存在则不变）

**Step 1: 创建 workflow_nodes.py**

```python
"""
LangGraph 工作流节点定义
4 节点链: analyze → research → execute → review
"""
import json
from typing import Any
from langchain_core.messages import HumanMessage, AIMessage
from app.config import get_settings
from app.agent.base import get_llm
from app.agent.tools import ALL_TOOLS
from app.rag.retriever import similarity_search
from app.agent.guard import OutputGuard

settings = get_settings()
_guard = OutputGuard()

# ─── 节点共享的 LLM 实例（temperature 0.3 降低幻觉）───
_llm = get_llm(temperature=0.3)


def analyze_node(state: dict) -> dict:
    """分析用户意图，拆解子任务，输出结构化计划"""
    question = state.get("question", "")
    history = state.get("chat_history", [])

    prompt = f"""你是一个工作流规划器。分析用户问题并输出结构化执行计划。

用户问题: {question}

请输出 JSON 格式的执行计划，包含:
1. intent: 用户意图分类 (query|analysis|generation|troubleshooting)
2. subtasks: 子任务列表，每个含 {{
    "step": 序号,
    "action": 描述,
    "tool": 需要的工具名称或"none"
}}
3. expected_output: 预期产出描述

只输出 JSON，不要其他内容。"""

    messages = history + [HumanMessage(content=prompt)]
    result = _llm.invoke(messages)
    content = result.content

    # 尝试解析 JSON，失败则用原始文本
    try:
        plan = json.loads(content)
    except json.JSONDecodeError:
        plan = {"intent": "general", "subtasks": [], "expected_output": content}

    return {
        **state,
        "plan": content,
        "parsed_plan": plan,
        "current_node": "analyze",
        "node_status": "completed",
    }


def research_node(state: dict) -> dict:
    """RAG 检索 + 工具调用，收集信息"""
    question = state.get("question", "")
    plan_data = state.get("plan", "")

    # 1. 知识库检索
    try:
        docs = similarity_search(question, k=4)
        knowledge_context = "\n\n".join(
            f"[文档{i+1}] {doc.page_content[:500]}" for i, doc in enumerate(docs)
        ) if docs else "知识库中未找到相关文档。"
    except Exception as e:
        knowledge_context = f"知识库检索失败: {e}"

    # 2. 汇总研究结果
    prompt = f"""你是一个信息收集研究员。根据以下信息回答用户问题。

用户问题: {question}
执行计划: {plan_data}
知识库检索结果:
{knowledge_context}

请输出:
1. 收集到的关键信息（分点列出）
2. 信息缺口（如有哪些问题尚待明确）
3. 建议的下一步行动

使用 Markdown 格式回复。"""

    messages = state.get("chat_history", []) + [HumanMessage(content=prompt)]
    result = _llm.invoke(messages)

    return {
        **state,
        "research": {
            "knowledge": knowledge_context,
            "analysis": result.content,
        },
        "current_node": "research",
        "node_status": "completed",
    }


def execute_node(state: dict) -> dict:
    """汇总信息，生成最终方案/答案"""
    question = state.get("question", "")
    research = state.get("research", {})

    prompt = f"""你是一个方案生成专家。基于研究结果，为用户问题生成完整回复。

用户问题: {question}

研究结果:
{research.get('analysis', '无研究结果')}

知识库原文:
{research.get('knowledge', '无知识库内容')}

请按照以下模板输出:

【结论】一句话总结核心答案

【分析】详细分析过程，引用研究中的关键发现

【建议】具体可执行的建议或方案（如适用）

【参考】引用的知识来源（如有）

使用 Markdown 格式，确保内容专业、准确、可执行。
遵守反幻觉规则：不编造任何数据、日期、数字。"""

    messages = state.get("chat_history", []) + [HumanMessage(content=prompt)]
    result = _llm.invoke(messages)

    return {
        **state,
        "draft_answer": result.content,
        "current_node": "execute",
        "node_status": "completed",
    }


def review_node(state: dict) -> dict:
    """LLM 自检：幻觉检测、完整性校验、格式审查"""
    draft = state.get("draft_answer", "")
    question = state.get("question", "")
    research = state.get("research", {})

    # 使用 guard 模块做基础检测
    guard_result = _guard.validate(draft)

    if guard_result.get("has_issue"):
        # 有问题 → 在回复末尾追加警告
        issue_tags = guard_result.get("issues", [])
        tags_text = "\n".join(f"- {t}" for t in issue_tags)
        final_answer = f"""{draft}

---
⚠️ **质量审查标注**（以下问题可能需要人工确认）：
{tags_text}
"""
    else:
        final_answer = draft

    # 完整性审查
    review_prompt = f"""你是一个质量审核员。请审查以下回复是否完整回答了用户问题。

用户问题: {question}
生成的回复:
{draft[:2000]}

请简要输出审查意见（1-2句话），如果回复完整则输出"PASS"。"""

    review_result = _llm.invoke([HumanMessage(content=review_prompt)])
    review_note = review_result.content.strip()

    return {
        **state,
        "final_answer": final_answer,
        "review_note": review_note,
        "guard_result": guard_result,
        "current_node": "review",
        "node_status": "completed",
    }


def decide_next(state: dict) -> str:
    """条件路由：根据意图决定是否跳过 research"""
    plan = state.get("parsed_plan", {})
    intent = plan.get("intent", "general") if isinstance(plan, dict) else "general"

    # 闲聊类直接跳 execute
    if intent in ("chat", "greeting"):
        return "execute"
    return "research"
```

---

### Task 3: 定义 LangGraph StateGraph

**Files:**
- Create: `backend/app/agent/workflow.py`

**Step 1: 创建 workflow.py**

```python
"""
LangGraph StateGraph 定义
4 节点链: analyze → research → execute → review
"""
from typing import Annotated, TypedDict
from operator import add
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from app.config import get_settings, BASE_DIR
from app.agent.workflow_nodes import (
    analyze_node,
    research_node,
    execute_node,
    review_node,
)

settings = get_settings()


class WorkflowState(TypedDict):
    """工作流状态定义"""
    question: str
    chat_history: Annotated[list, add]

    # 各节点输出
    plan: str
    parsed_plan: dict
    research: dict
    draft_answer: str
    final_answer: str

    # 审核
    review_note: str
    guard_result: dict

    # 进度跟踪
    current_node: str
    node_status: str


def build_workflow() -> StateGraph:
    """构建 LangGraph 工作流"""
    builder = StateGraph(WorkflowState)

    # 添加节点
    builder.add_node("analyze", analyze_node)
    builder.add_node("research", research_node)
    builder.add_node("execute", execute_node)
    builder.add_node("review", review_node)

    # 定义边
    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "research")
    builder.add_edge("research", "execute")
    builder.add_edge("execute", "review")
    builder.add_edge("review", END)

    return builder


def get_checkpointer() -> SqliteSaver:
    """获取 SQLite Checkpointer（支持工作流中断恢复）"""
    db_path = BASE_DIR / "data" / "workflow_checkpoints.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver.from_conn_string(str(db_path))


def compile_workflow():
    """编译工作流（带 Checkpointer）"""
    builder = build_workflow()
    checkpointer = get_checkpointer()
    return builder.compile(checkpointer=checkpointer)


# 全局单例
_workflow = None


def get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = compile_workflow()
    return _workflow
```

---

### Task 4: 创建工作流服务层（SSE 流式）

**Files:**
- Create: `backend/app/services/workflow_service.py`

**Step 1: 创建 workflow_service.py**

```python
"""
LangGraph 工作流服务层
通过 SSE 流式推送每个节点的执行状态
"""
import json
import asyncio
import traceback
from typing import AsyncGenerator
from app.agent.workflow import get_workflow, WorkflowState


async def run_workflow_stream(
    question: str,
    chat_history: list = None,
    thread_id: str = "default",
) -> AsyncGenerator[str, None]:
    """
    执行工作流并通过 SSE 流式推送节点状态

    SSE 事件格式:
    - node_start: {"type": "node_start", "node": "analyze", "timestamp": ...}
    - node_complete: {"type": "node_complete", "node": "analyze", "output": {...}}
    - stream_token: {"type": "stream_token", "content": "..."}
    - workflow_complete: {"type": "done", "final_answer": "...", "review_note": "..."}
    - workflow_error: {"type": "error", "message": "..."}
    """
    workflow = get_workflow()
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: WorkflowState = {
        "question": question,
        "chat_history": chat_history or [],
        "plan": "",
        "parsed_plan": {},
        "research": {},
        "draft_answer": "",
        "final_answer": "",
        "review_note": "",
        "guard_result": {},
        "current_node": "",
        "node_status": "pending",
    }

    try:
        # 使用 astream_events 捕获每个节点的执行
        async for event in workflow.astream_events(initial_state, config, version="v2"):
            kind = event.get("event", "")

            if kind == "on_chain_start":
                node_name = event.get("name", "")
                if node_name in ("analyze", "research", "execute", "review"):
                    yield _sse_event("node_start", {
                        "node": node_name,
                        "status": "running",
                    })

            elif kind == "on_chain_end":
                node_name = event.get("name", "")
                output = event.get("data", {}).get("output", {})

                if node_name in ("analyze", "research", "execute", "review"):
                    # 提取该节点产出的关键文本
                    summary = _extract_node_summary(node_name, output)
                    yield _sse_event("node_complete", {
                        "node": node_name,
                        "status": "completed",
                        "summary": summary,
                    })

                    # execute 完成后就开始流式输出 draft
                    if node_name == "execute" and output.get("draft_answer"):
                        draft = output["draft_answer"]
                        for i in range(0, len(draft), 8):
                            chunk = draft[i:i + 8]
                            yield _sse_event("stream_token", {"content": chunk})
                            await asyncio.sleep(0.015)

            elif kind == "on_chat_model_stream":
                # LLM 流式输出 token（可选，展示思考过程）
                chunk = event.get("data", {}).get("chunk", {})
                if hasattr(chunk, "content") and chunk.content:
                    yield _sse_event("stream_token", {"content": chunk.content})

        # 工作流完成，获取最终结果
        final_state = workflow.get_state(config)
        if final_state and final_state.values:
            final_answer = final_state.values.get("final_answer", "")
            review_note = final_state.values.get("review_note", "")
            yield _sse_event("done", {
                "final_answer": final_answer,
                "review_note": review_note,
            })
        else:
            yield _sse_event("done", {
                "final_answer": "工作流执行完成，但未获取到最终结果。",
                "review_note": "",
            })

    except Exception as e:
        yield _sse_event("error", {
            "message": f"工作流执行失败: {str(e)}",
            "detail": traceback.format_exc()[:500] if settings.debug else "",
        })


def _sse_event(event_type: str, data: dict) -> str:
    """构造 SSE 事件字符串"""
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _extract_node_summary(node_name: str, output: dict) -> str:
    """从节点输出中提取关键摘要文本"""
    if not output:
        return ""
    if node_name == "analyze":
        return output.get("plan", "")[:300]
    elif node_name == "research":
        research = output.get("research", {})
        return research.get("analysis", "")[:300]
    elif node_name == "execute":
        return output.get("draft_answer", "")[:300]
    elif node_name == "review":
        return output.get("review_note", "")[:300]
    return ""
```

> 需要补充 `import settings`：
```python
from app.config import get_settings
settings = get_settings()
```

---

### Task 5: 创建工作流 API 路由

**Files:**
- Create: `backend/app/api/workflow.py`

**Step 1: 创建 workflow.py**

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.workflow_service import run_workflow_stream
from app.database import get_sessionmaker
from app.models.conversation import Conversation
from app.models.message import Message
from sqlalchemy import select
import uuid

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


class WorkflowRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class WorkflowStatusResponse(BaseModel):
    thread_id: str
    current_node: str
    node_status: str
    final_answer: str | None


@router.post("/start")
async def start_workflow(req: WorkflowRequest) -> StreamingResponse:
    """启动 LangGraph 工作流，SSE 流式返回节点执行状态"""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    thread_id = str(uuid.uuid4())

    return StreamingResponse(
        run_workflow_stream(
            question=req.question,
            chat_history=[],
            thread_id=thread_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Workflow-Thread-Id": thread_id,
        },
    )


@router.get("/status/{thread_id}")
async def get_workflow_status(thread_id: str):
    """查询工作流当前状态（用于轮询恢复场景）"""
    from app.agent.workflow import get_workflow

    workflow = get_workflow()
    config = {"configurable": {"thread_id": thread_id}}
    state = workflow.get_state(config)

    if not state:
        return {"thread_id": thread_id, "status": "not_found"}

    values = state.values or {}
    return {
        "thread_id": thread_id,
        "current_node": values.get("current_node", ""),
        "node_status": values.get("node_status", ""),
        "final_answer": values.get("final_answer"),
    }


@router.get("/history")
async def list_workflows():
    """列出历史工作流执行记录"""
    return {"workflows": [], "message": "历史记录功能将在后续版本实现"}
```

---

### Task 6: 注册工作流路由到 FastAPI

**Files:**
- Modify: `backend/app/main.py`

**Step 1: 在 main.py 中注册 workflow router**

在 `from app.api import chat, knowledge, conversation` 之后添加：
```python
from app.api import workflow
```

在 `app.include_router(knowledge.router)` 之后添加：
```python
app.include_router(workflow.router)
```

更新 description：
```python
description="企业级 AI Agent 工作流平台 - LangGraph 版本",
version="2.0.0",
```

---

### Task 7: 前端工作流类型定义

**Files:**
- Create: `frontend/src/types/workflow.ts`

```typescript
export type NodeName = 'analyze' | 'research' | 'execute' | 'review'

export type NodeStatus = 'pending' | 'running' | 'completed' | 'error'

export interface NodeState {
  name: NodeName
  status: NodeStatus
  summary: string
  timestamp?: string
}

export interface WorkflowEvent {
  type: 'node_start' | 'node_complete' | 'stream_token' | 'done' | 'error'
  node?: NodeName
  status?: NodeStatus
  summary?: string
  content?: string
  final_answer?: string
  review_note?: string
  message?: string
}

export interface WorkflowRequest {
  question: string
  conversation_id?: string
}
```

---

### Task 8: 前端工作流 API 封装

**Files:**
- Create: `frontend/src/api/workflow.ts`

```typescript
import request from './request'

export const workflowApi = {
  async startWorkflow(data: { question: string; conversation_id?: string }): Promise<Response> {
    return fetch('/api/workflow/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  },

  getStatus(threadId: string): Promise<any> {
    return request.get(`/workflow/status/${threadId}`) as any
  },
}
```

---

### Task 9: 前端工作流 Pinia Store

**Files:**
- Create: `frontend/src/stores/workflow.ts`

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { NodeState, NodeName } from '@/types/workflow'
import { workflowApi } from '@/api/workflow'

interface WorkflowLog {
  node: NodeName
  status: string
  summary: string
}

export const useWorkflowStore = defineStore('workflow', () => {
  const nodes = ref<NodeState[]>([
    { name: 'analyze', status: 'pending', summary: '' },
    { name: 'research', status: 'pending', summary: '' },
    { name: 'execute', status: 'pending', summary: '' },
    { name: 'review', status: 'pending', summary: '' },
  ])

  const status = ref<'idle' | 'running' | 'completed' | 'error'>('idle')
  const logs = ref<WorkflowLog[]>([])
  const finalAnswer = ref('')
  const reviewNote = ref('')
  const streamContent = ref('')
  const errorMessage = ref('')

  function reset() {
    nodes.value.forEach((n) => {
      n.status = 'pending'
      n.summary = ''
    })
    status.value = 'idle'
    logs.value = []
    finalAnswer.value = ''
    reviewNote.value = ''
    streamContent.value = ''
    errorMessage.value = ''
  }

  function updateNode(nodeName: NodeName, nodeStatus: string, summary?: string) {
    const node = nodes.value.find((n) => n.name === nodeName)
    if (node) {
      node.status = nodeStatus as any
      if (summary) node.summary = summary
      node.timestamp = new Date().toISOString()
    }
  }

  function addLog(log: WorkflowLog) {
    logs.value.push(log)
  }

  return {
    nodes, status, logs, finalAnswer, reviewNote, streamContent, errorMessage,
    reset, updateNode, addLog,
  }
})
```

---

### Task 10: 前端工作流 SSE Composable

**Files:**
- Create: `frontend/src/composables/useWorkflowSSE.ts`

```typescript
import { ref } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import type { WorkflowEvent } from '@/types/workflow'
import { ElMessage } from 'element-plus'

export function useWorkflowSSE() {
  const store = useWorkflowStore()
  const abortController = ref<AbortController | null>(null)

  async function startWorkflow(question: string) {
    store.reset()
    store.status = 'running'

    abortController.value = new AbortController()

    try {
      const response = await fetch('/api/workflow/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
        signal: abortController.value.signal,
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || '工作流启动失败')
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event: WorkflowEvent = JSON.parse(line.slice(6))
            handleEvent(event)
          } catch {
            // skip malformed JSON
          }
        }
      }

      if (store.status === 'running') {
        store.status = 'completed'
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        store.status = 'error'
        store.errorMessage = e.message || '工作流执行失败'
        ElMessage.error(store.errorMessage)
      }
    }
  }

  function handleEvent(event: WorkflowEvent) {
    switch (event.type) {
      case 'node_start':
        if (event.node) {
          store.updateNode(event.node, 'running')
          store.addLog({ node: event.node, status: 'running', summary: '' })
        }
        break

      case 'node_complete':
        if (event.node) {
          store.updateNode(event.node, 'completed', event.summary)
          store.addLog({
            node: event.node,
            status: 'completed',
            summary: event.summary || '',
          })
        }
        break

      case 'stream_token':
        if (event.content) {
          store.streamContent += event.content
        }
        break

      case 'done':
        store.finalAnswer = event.final_answer || ''
        store.reviewNote = event.review_note || ''
        store.status = 'completed'
        break

      case 'error':
        store.status = 'error'
        store.errorMessage = event.message || '未知错误'
        ElMessage.error(store.errorMessage)
        break
    }
  }

  function stopWorkflow() {
    abortController.value?.abort()
    store.status = 'idle'
  }

  return { startWorkflow, stopWorkflow }
}
```

---

### Task 11: 前端工作流视图与组件

**Files:**
- Create: `frontend/src/views/WorkflowView.vue`
- Create: `frontend/src/components/workflow/WorkflowPanel.vue`
- Create: `frontend/src/components/workflow/NodeStatusCard.vue`

**Step 1: 创建 WorkflowView.vue**

```vue
<script setup lang="ts">
import NavBar from '@/components/common/NavBar.vue'
import WorkflowPanel from '@/components/workflow/WorkflowPanel.vue'
</script>

<template>
  <div class="workflow-container">
    <NavBar />
    <div class="workflow-body">
      <div class="workflow-header">
        <h2>LangGraph 工作流</h2>
        <p>多步骤任务编排：分析 → 检索 → 执行 → 审查</p>
      </div>
      <WorkflowPanel />
    </div>
  </div>
</template>

<style scoped>
.workflow-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.workflow-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 40px;
  background: #f5f7fa;
}
.workflow-header {
  margin-bottom: 24px;
}
.workflow-header h2 {
  margin: 0 0 8px;
}
.workflow-header p {
  color: #909399;
  margin: 0;
}
</style>
```

**Step 2: 创建 WorkflowPanel.vue**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import { useWorkflowSSE } from '@/composables/useWorkflowSSE'
import NodeStatusCard from './NodeStatusCard.vue'

const store = useWorkflowStore()
const { startWorkflow, stopWorkflow } = useWorkflowSSE()

const question = ref('')
const running = ref(false)

async function handleStart() {
  const q = question.value.trim()
  if (!q) return
  running.value = true
  await startWorkflow(q)
  running.value = false
}

function handleStop() {
  stopWorkflow()
  running.value = false
}
</script>

<template>
  <div class="workflow-panel">
    <!-- 输入区 -->
    <el-card class="input-card">
      <template #header>
        <span>输入任务描述</span>
      </template>
      <el-input
        v-model="question"
        type="textarea"
        :rows="3"
        maxlength="2000"
        show-word-limit
        placeholder="描述你的复杂任务，例如：分析数据库性能瓶颈并给出优化方案"
        :disabled="running"
        @keydown.enter.ctrl="handleStart"
      />
      <div class="input-actions">
        <el-button
          v-if="!running"
          type="primary"
          :disabled="!question.trim()"
          @click="handleStart"
        >
          <el-icon><VideoPlay /></el-icon>
          启动工作流
        </el-button>
        <el-button v-else type="danger" @click="handleStop">
          <el-icon><Close /></el-icon>
          停止
        </el-button>
        <span class="hint">Ctrl+Enter 快速启动</span>
      </div>
    </el-card>

    <!-- 节点状态 -->
    <el-card class="nodes-card" v-if="store.status !== 'idle'">
      <template #header>
        <div class="nodes-header">
          <span>执行进度</span>
          <el-tag :type="store.status === 'completed' ? 'success' : store.status === 'error' ? 'danger' : 'warning'">
            {{ store.status === 'running' ? '运行中' : store.status === 'completed' ? '已完成' : '出错' }}
          </el-tag>
        </div>
      </template>
      <div class="nodes-chain">
        <NodeStatusCard
          v-for="(node, index) in store.nodes"
          :key="node.name"
          :node="node"
          :is-last="index === store.nodes.length - 1"
        />
      </div>
    </el-card>

    <!-- 实时输出 -->
    <el-card class="output-card" v-if="store.streamContent">
      <template #header>
        <span>实时输出</span>
      </template>
      <div class="stream-output markdown-body" v-text="store.streamContent" />
    </el-card>

    <!-- 最终结果 -->
    <el-card class="result-card" v-if="store.finalAnswer">
      <template #header>
        <span>最终结果</span>
      </template>
      <div class="final-answer markdown-body" v-text="store.finalAnswer" />

      <el-alert
        v-if="store.reviewNote && store.reviewNote !== 'PASS'"
        type="warning"
        :closable="false"
        show-icon
      >
        <template #title>{{ store.reviewNote }}</template>
      </el-alert>
    </el-card>
  </div>
</template>

<style scoped>
.workflow-panel {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.input-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}
.input-actions .hint {
  color: #c0c4cc;
  font-size: 12px;
}
.nodes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.nodes-chain {
  display: flex;
  align-items: center;
  gap: 0;
  overflow-x: auto;
  padding: 8px 0;
}
</style>
```

**Step 3: 创建 NodeStatusCard.vue**

```vue
<script setup lang="ts">
import type { NodeState } from '@/types/workflow'
import { computed } from 'vue'

const props = defineProps<{
  node: NodeState
  isLast: boolean
}>()

const labelMap: Record<string, string> = {
  analyze: '分析意图',
  research: '检索信息',
  execute: '生成方案',
  review: '质量审查',
}

const iconMap: Record<string, string> = {
  analyze: 'Search',
  research: 'Collection',
  execute: 'SetUp',
  review: 'Finished',
}

const statusColor = computed(() => {
  if (props.node.status === 'completed') return '#67c23a'
  if (props.node.status === 'running') return '#409eff'
  if (props.node.status === 'error') return '#f56c6c'
  return '#c0c4cc'
})
</script>

<template>
  <div class="node-chain-wrapper">
    <div class="node-card" :class="node.status">
      <div class="node-icon" :style="{ background: statusColor }">
        <el-icon :size="20"><component :is="iconMap[node.name]" /></el-icon>
      </div>
      <div class="node-info">
        <div class="node-name">{{ labelMap[node.name] }}</div>
        <div class="node-status">
          <el-tag
            size="small"
            :type="
              node.status === 'completed' ? 'success' :
              node.status === 'running' ? '' :
              node.status === 'error' ? 'danger' : 'info'
            "
            :effect="node.status === 'running' ? 'dark' : 'plain'"
          >
            {{ node.status === 'completed' ? '完成' : node.status === 'running' ? '执行中' : node.status === 'error' ? '失败' : '等待' }}
          </el-tag>
        </div>
      </div>
      <div v-if="node.status === 'running'" class="node-spinner">
        <el-icon class="is-loading"><Loading /></el-icon>
      </div>
    </div>
    <div v-if="!isLast" class="node-arrow" :style="{ color: statusColor }">
      <el-icon><ArrowRight /></el-icon>
    </div>
  </div>
</template>

<style scoped>
.node-chain-wrapper {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.node-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: 10px;
  background: white;
  border: 2px solid #e4e7ed;
  min-width: 160px;
  transition: all 0.3s;
}
.node-card.completed {
  border-color: #67c23a;
}
.node-card.running {
  border-color: #409eff;
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.3);
}
.node-card.error {
  border-color: #f56c6c;
}
.node-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  transition: background 0.3s;
}
.node-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.node-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.node-status {
  font-size: 12px;
}
.node-spinner {
  color: #409eff;
}
.node-arrow {
  font-size: 20px;
  margin: 0 4px;
  display: flex;
  align-items: center;
  transition: color 0.3s;
}
</style>
```

---

### Task 12: 前端路由注册

**Files:**
- Modify: `frontend/src/router/index.ts` — 添加 /workflow 路由
- Modify: `frontend/src/components/common/NavBar.vue` — 添加工作流导航项

**Step 1: 修改 router/index.ts**

在 routes 数组中添加：
```typescript
{
  path: '/workflow',
  name: 'workflow',
  component: () => import('@/views/WorkflowView.vue'),
  meta: { title: '工作流' },
},
```

**Step 2: 修改 NavBar.vue**

在 `navItems` 中添加：
```typescript
{ path: '/workflow', label: '工作流' },
```

---

### Task 13: 验证与测试

**Step 1: 启动后端，测试导入**

```bash
cd backend && ..\.venv\Scripts\python.exe -c "
from app.agent.workflow_nodes import analyze_node, research_node, execute_node, review_node
from app.agent.workflow import get_workflow
print('All imports OK')
print('Workflow compiled:', get_workflow())
"
```

**Step 2: 测试工作流 API**

```bash
cd backend && ..\.venv\Scripts\python.exe -c "
import httpx, asyncio
async def test():
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post('http://localhost:8000/api/workflow/start', json={'question': '请简单介绍一下自己'})
        print(f'Status: {r.status_code}')
        print(f'Response: {r.text[:500]}')
asyncio.run(test())
"
```

**Step 3: 访问 http://localhost:3000/workflow 测试前端页面**

---

## 启动检查清单

1. 安装 langgraph 依赖：
```bash
cd backend && ..\.venv\Scripts\pip.exe install langgraph langgraph-checkpoint-sqlite
```

2. 重启后端（uvicorn --reload 已自动重载）

3. 前端 Vite HMR 已自动更新路由

4. 访问 http://localhost:3000/workflow 测试工作流
