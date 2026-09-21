"""运行 Agent 工具评测任务集，采集真实 tool_call_trace，生成 traces.jsonl。

用法（在 backend 目录）：
    python scripts/collect_agent_tool_traces.py [--output evaluation/agent_tools/traces.jsonl] [--ids knowledge-001,chat-001]

每个任务使用独立会话运行 ChatService.chat_stream，避免历史上下文干扰；
从 metrics["tool_call_trace"] 提取安全化的工具调用记录后写入 JSONL。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings  # noqa: E402
from app.evaluation.agent_tools import load_cases  # noqa: E402
from app.services.chat_service import ChatService  # noqa: E402

DATA_DIR = BACKEND_DIR / "evaluation" / "agent_tools"
FINAL_STATUSES = {"success", "parameter_error", "error", "timeout"}


async def run_case(service: ChatService, case) -> tuple[str, list[dict], str]:
    """运行单个任务并返回 (case_id, tool_calls, 摘要文本)。"""
    conversation_id = str(uuid.uuid4())
    metrics = {
        "request_id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "model": get_settings().model_name,
        "request_received": time.perf_counter(),
    }
    chunks = []
    async for chunk in service.chat_stream(conversation_id, case.question, metrics):
        chunks.append(chunk)

    trace = metrics.get("tool_call_trace", [])
    final_calls = [
        {
            "name": call["name"],
            "status": call["status"],
            "duration_ms": round(call["duration_ms"], 2)
            if isinstance(call.get("duration_ms"), (int, float))
            else None,
            "args_fingerprint": call.get("args_fingerprint", ""),
        }
        for call in trace
        if call.get("status") in FINAL_STATUSES
    ]
    return case.id, final_calls, "".join(chunks)[-300:]


async def collect(
    cases,
    output: Path,
    ids: list[str] | None,
) -> int:
    service = ChatService()
    selected = [c for c in cases if not ids or c.id in ids]
    rows = []
    errors = []

    for index, case in enumerate(selected, 1):
        started = time.perf_counter()
        try:
            case_id, calls, summary = await run_case(service, case)
            rows.append({"id": case_id, "tool_calls": calls})
            print(
                f"[{index}/{len(selected)}] {case_id} "
                f"tools={sorted({c['name'] for c in calls})} "
                f"calls={len(calls)} elapsed={round(time.perf_counter() - started, 1)}s"
            )
        except Exception as exc:
            errors.append({"id": case.id, "error": str(exc)[:200]})
            print(f"[{index}/{len(selected)}] {case.id} ERROR: {str(exc)[:200]}", file=sys.stderr)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps(
        {
            "status": "ok" if not errors else "partial",
            "ran": len(rows),
            "selected": len(selected),
            "output": str(output),
            "errors": errors,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect real Agent tool-call traces")
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_DIR / "traces.jsonl",
        help="Output JSONL path (default: evaluation/agent_tools/traces.jsonl)",
    )
    parser.add_argument(
        "--ids",
        help="Comma-separated case ids to run (default: all cases)",
    )
    args = parser.parse_args()

    cases = load_cases(DATA_DIR / "cases.jsonl")
    ids = [item.strip() for item in args.ids.split(",")] if args.ids else None
    return asyncio.run(collect(cases, args.output, ids))


if __name__ == "__main__":
    raise SystemExit(main())
