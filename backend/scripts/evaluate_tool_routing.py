"""离线评测分层 Tool Routing：候选召回、越权暴露、无工具拒选与副作用拦截。

用法（在 backend 目录）：
    python scripts/evaluate_tool_routing.py [--k 3] [--lexical-only] [--validate-only]

`--lexical-only` 使路由完全不调用 Embedding，评测确定性、无网络依赖。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.agent.tool_router import TOOL_CARDS, route_tools  # noqa: E402
from app.evaluation.agent_tools import (  # noqa: E402
    load_cases,
    score_routing,
    validate_dataset,
)

DATA_DIR = BACKEND_DIR / "evaluation" / "agent_tools"
CONFIRMATION_TOOLS = {card.name for card in TOOL_CARDS if card.requires_confirmation}


async def route_cases(
    cases, k: int, lexical_only: bool
) -> tuple[dict[str, list[str]], dict[str, dict]]:
    """对每条任务跑真实路由，收集候选顺序与分层诊断信息。"""
    routes: dict[str, list[str]] = {}
    diagnostics: dict[str, dict] = {}
    for case in cases:
        decision = await route_tools(
            case.question, embedding_weight=0.0 if lexical_only else None
        )
        routes[case.id] = [scored.card.name for scored in decision.candidates]
        diagnostics[case.id] = {
            "layer": decision.layer,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "latency_ms": decision.latency_ms,
            "dropped": [[item["name"], item["reason"]] for item in decision.dropped],
        }
    return routes, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate layered tool routing candidates")
    parser.add_argument("--k", type=int, default=3, help="Top-K candidate window (default: 3)")
    parser.add_argument(
        "--lexical-only",
        action="store_true",
        help="Skip the embedding layer (deterministic and offline)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_DIR / "latest-routing-report.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    cases = load_cases(DATA_DIR / "cases.jsonl")
    validate_dataset(cases, {card.name for card in TOOL_CARDS})
    if args.validate_only:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "cases": len(cases),
                    "categories": sorted({case.category for case in cases}),
                },
                ensure_ascii=False,
            )
        )
        return 0

    routes, diagnostics = asyncio.run(route_cases(cases, args.k, args.lexical_only))
    report = score_routing(
        cases,
        routes,
        k=args.k,
        diagnostics=diagnostics,
        confirmation_tools=CONFIRMATION_TOOLS,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
