"""Validate the Agent tool eval set and score recorded tool-call traces."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.agent.tools import TOOL_SPECS
from app.evaluation.agent_tools import (
    load_cases,
    load_traces,
    score_tool_traces,
    validate_dataset,
)

DATA_DIR = BACKEND_DIR / "evaluation" / "agent_tools"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Agent tool-call traces")
    parser.add_argument(
        "--traces",
        type=Path,
        help="JSONL trace file produced by the Agent runtime",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_DIR / "latest-report.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    cases = load_cases(DATA_DIR / "cases.jsonl")
    validate_dataset(cases, {spec.name for spec in TOOL_SPECS})
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

    if not args.traces:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "cases": len(cases),
                    "note": "Pass --traces to calculate Agent tool-call metrics.",
                },
                ensure_ascii=False,
            )
        )
        return 0

    traces = load_traces(args.traces)
    report = score_tool_traces(cases, traces)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
