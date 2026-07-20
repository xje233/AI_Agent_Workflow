"""
LangGraph 工作流服务层
通过 SSE 流式推送每个节点的执行状态
"""
import json
import asyncio
import traceback
from typing import AsyncGenerator
from app.config import get_settings
from app.agent.workflow import get_workflow, WorkflowState

settings = get_settings()

# 节点名称与中文标签映射
NODE_LABELS = {
    "analyze": "分析意图",
    "research": "检索信息",
    "execute": "生成方案",
    "review": "质量审查",
}

# 输出节点顺序
NODE_ORDER = ["analyze", "research", "execute", "review"]


async def run_workflow_stream(
    question: str,
    chat_history: list = None,
    thread_id: str = "default",
) -> AsyncGenerator[str, None]:
    """
    执行工作流并通过 SSE 流式推送节点状态

    LangGraph astream 返回格式: {node_name: node_output_dict}
    其中 node_output_dict 是对应节点函数的返回值（只含更新字段）
    """
    # 工作流与 SQLite checkpoint saver 为进程级单例，首次调用时才初始化。
    workflow = await get_workflow()
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: WorkflowState = {
        "question": question,
        "chat_history": chat_history or [],
        "plan": "",
        "parsed_plan": {},
        "research_data": {},
        "draft_answer": "",
        "final_answer": "",
        "review_note": "",
        "guard_result": {},
        "current_node": "",
        "node_status": "pending",
    }

    try:
        completed_nodes = set()

        # astream 逐节点执行，chunk 格式: {node_name: node_output_dict}
        # LangGraph 按节点产生增量结果；这里将其转换为前端约定的 SSE 事件。
        async for chunk in workflow.astream(initial_state, config):
            # chunk 是 dict，key 是节点名，value 是节点输出 dict
            # 例: {"analyze": {"plan": "...", "parsed_plan": {...}, "current_node": "analyze", "node_status": "completed"}}
            for node_name, node_output in chunk.items():
                if node_name not in NODE_ORDER:
                    continue  # 忽略非业务节点

                current_node = node_output.get("current_node", node_name)
                node_status = node_output.get("node_status", "")

                # 检测新完成的节点
                if node_status == "completed" and node_name not in completed_nodes:
                    completed_nodes.add(node_name)

                    # 1. 先发 node_start
                    yield _sse_event("node_start", {
                        "node": node_name,
                        "label": NODE_LABELS.get(node_name, node_name),
                    })

                    # 2. 短暂延迟让前端动画可见
                    await asyncio.sleep(0.3)

                    # 3. 发 node_complete 带摘要
                    summary = _extract_node_summary(node_name, node_output)
                    yield _sse_event("node_complete", {
                        "node": node_name,
                        "label": NODE_LABELS.get(node_name, node_name),
                        "summary": summary,
                    })

                    # 4. execute 节点完成后流式推送 draft_answer
                    if node_name == "execute":
                        draft = node_output.get("draft_answer", "")
                        if draft:
                            yield _sse_event("stream_start", {"content": ""})
                            for i in range(0, len(draft), 10):
                                piece = draft[i:i + 10]
                                yield _sse_event("stream_token", {"content": piece})
                                await asyncio.sleep(0.015)

        # 获取最终状态（使用 async 版本）
        final_state = await workflow.aget_state(config)
        if final_state and final_state.values:
            vals = final_state.values
            final_answer = vals.get("final_answer", "")
            review_note = vals.get("review_note", "")
            yield _sse_event("done", {
                "final_answer": final_answer,
                "review_note": review_note,
            })
        else:
            yield _sse_event("done", {
                "final_answer": "工作流执行完成。",
                "review_note": "",
            })

    except Exception as e:
        detail = traceback.format_exc()[:500] if settings.debug else ""
        yield _sse_event("error", {
            "message": f"工作流执行失败: {str(e)}",
            "detail": detail,
        })


def _sse_event(event_type: str, data: dict) -> str:
    """构造 SSE 事件字符串"""
    payload = {"type": event_type, **data}
    # SSE 规范要求每个 data 帧以一个空行结束。
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _extract_node_summary(node_name: str, node_output: dict) -> str:
    """从节点输出中提取节点摘要"""
    if not node_output:
        return "已完成"
    if node_name == "analyze":
        plan = node_output.get("plan", "")
        return plan[:200] if plan else "已完成分析"
    elif node_name == "research":
        rd = node_output.get("research_data", {})
        if isinstance(rd, dict):
            return rd.get("analysis", "已完成检索")[:200]
        return "已完成检索"
    elif node_name == "execute":
        da = node_output.get("draft_answer", "")
        return da[:200] if da else "已完成方案生成"
    elif node_name == "review":
        rn = node_output.get("review_note", "")
        return rn[:200] if rn else "已完成审查"
    return "已完成"
