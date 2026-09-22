"""Agent 工具调用评测：选择、参数、重复调用、错误和耗时。"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_STATUSES = {"success", "parameter_error", "error", "timeout", "unauthorized"}


@dataclass(frozen=True)
class ToolEvalCase:
    id: str
    category: str
    question: str
    expected_tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolCallRecord:
    name: str
    status: str
    duration_ms: float
    args_fingerprint: str = ""


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
    return rows


def load_cases(path: Path) -> list[ToolEvalCase]:
    return [
        ToolEvalCase(
            id=row["id"],
            category=row["category"],
            question=row["question"],
            expected_tools=tuple(row.get("expected_tools", [])),
            forbidden_tools=tuple(row.get("forbidden_tools", [])),
        )
        for row in load_jsonl(path)
    ]


def _fingerprint_args(args: object) -> str:
    payload = json.dumps(args or {}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_traces(path: Path) -> dict[str, list[ToolCallRecord]]:
    traces: dict[str, list[ToolCallRecord]] = {}
    for row in load_jsonl(path):
        calls = []
        for call in row.get("tool_calls", []):
            duration = call.get("duration_ms")
            if not isinstance(duration, (int, float)):
                raise ValueError(f"{path}: {row.get('id')}: duration_ms must be numeric")
            args_fingerprint = call.get("args_fingerprint") or _fingerprint_args(call.get("args"))
            calls.append(
                ToolCallRecord(
                    name=call["name"],
                    status=call.get("status", "success"),
                    duration_ms=float(duration),
                    args_fingerprint=args_fingerprint,
                )
            )
        traces[row["id"]] = calls
    return traces


def validate_dataset(cases: list[ToolEvalCase], supported_tools: set[str]) -> None:
    errors = []
    if len(cases) < 20:
        errors.append(f"expected at least 20 cases, got {len(cases)}")
    duplicate_ids = [
        case_id
        for case_id in {case.id for case in cases}
        if sum(case.id == case_id for case in cases) > 1
    ]
    if duplicate_ids:
        errors.append(f"duplicate case ids: {', '.join(sorted(duplicate_ids))}")
    for case in cases:
        expected = set(case.expected_tools)
        forbidden = set(case.forbidden_tools)
        unknown = (expected | forbidden) - supported_tools
        if unknown:
            errors.append(f"{case.id}: unknown tools: {', '.join(sorted(unknown))}")
        overlap = expected & forbidden
        if overlap:
            errors.append(
                f"{case.id}: tools cannot be both expected and forbidden: {', '.join(sorted(overlap))}"
            )
        if not case.question.strip():
            errors.append(f"{case.id}: question cannot be empty")
    if errors:
        raise ValueError("agent tool dataset validation failed:\n- " + "\n- ".join(errors))


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(ordered[lower], 2)
    weight = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * weight, 2)


def _summarize_latency(values: list[float]) -> dict:
    return {
        "samples": len(values),
        "avg": round(sum(values) / len(values), 2) if values else None,
        "p50": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
        "max": round(max(values), 2) if values else None,
    }


def score_tool_traces(
    cases: list[ToolEvalCase], traces: dict[str, list[ToolCallRecord]]
) -> dict:
    """计算工具选择和调用质量指标。

    selection_accuracy 要求实际工具集合与 expected_tools 完全一致。
    duplicate_call_rate 按同一案例中相同工具+参数指纹的重复调用数计算。
    tool_error_rate 包含参数错误和执行错误；execution_error_rate 不含参数错误。
    """
    selection_samples = []
    failures = []
    by_category: dict[str, list[dict]] = defaultdict(list)
    all_durations: list[float] = []
    total_calls = parameter_errors = execution_errors = duplicate_calls = 0
    duplicate_cases = 0
    missing_traces = []

    for case in cases:
        if case.id not in traces:
            missing_traces.append(case.id)
            continue
        calls = traces[case.id]
        actual_tools = {call.name for call in calls}
        expected_tools = set(case.expected_tools)
        forbidden_tools = set(case.forbidden_tools)
        selection_correct = actual_tools == expected_tools and not actual_tools & forbidden_tools
        selection_samples.append(selection_correct)

        seen_calls: set[tuple[str, str]] = set()
        case_duplicates = 0
        case_parameter_errors = 0
        case_execution_errors = 0
        for call in calls:
            total_calls += 1
            if call.status not in SUPPORTED_STATUSES:
                raise ValueError(f"{case.id}: unsupported tool call status {call.status}")
            if call.duration_ms < 0:
                raise ValueError(f"{case.id}: duration_ms cannot be negative")
            all_durations.append(call.duration_ms)
            call_key = (call.name, call.args_fingerprint)
            if call_key in seen_calls:
                duplicate_calls += 1
                case_duplicates += 1
            seen_calls.add(call_key)
            if call.status == "parameter_error":
                parameter_errors += 1
                case_parameter_errors += 1
            elif call.status in {"error", "timeout", "unauthorized"}:
                execution_errors += 1
                case_execution_errors += 1

        if case_duplicates:
            duplicate_cases += 1
        by_category[case.category].append(
            {
                "selection_correct": selection_correct,
                "tool_calls": len(calls),
                "parameter_errors": case_parameter_errors,
                "execution_errors": case_execution_errors,
                "duplicate_calls": case_duplicates,
            }
        )
        if not selection_correct:
            failures.append(
                {
                    "id": case.id,
                    "category": case.category,
                    "reason": "tool_selection_mismatch",
                    "expected": sorted(expected_tools),
                    "actual": sorted(actual_tools),
                }
            )

    evaluated = len(selection_samples)
    tool_error_count = parameter_errors + execution_errors
    return {
        "evaluated_samples": evaluated,
        "missing_traces": missing_traces,
        "selection_accuracy": round(sum(selection_samples) / evaluated, 4) if evaluated else None,
        "tool_calls": total_calls,
        "parameter_error_rate": round(parameter_errors / total_calls, 4) if total_calls else None,
        "duplicate_call_rate": round(duplicate_calls / total_calls, 4) if total_calls else None,
        "duplicate_case_rate": round(duplicate_cases / evaluated, 4) if evaluated else None,
        "tool_error_rate": round(tool_error_count / total_calls, 4) if total_calls else None,
        "execution_error_rate": round(execution_errors / total_calls, 4) if total_calls else None,
        "latency_ms": _summarize_latency(all_durations),
        "by_category": {category: samples for category, samples in sorted(by_category.items())},
        "failures": failures,
    }


def _rate(samples: list[bool]) -> float | None:
    return round(sum(samples) / len(samples), 4) if samples else None


def score_routing(
    cases: list[ToolEvalCase],
    routes: dict[str, list[str]],
    k: int = 3,
    diagnostics: dict[str, dict] | None = None,
    confirmation_tools: Collection[str] = (),
) -> dict:
    """计算候选召回、越权暴露与无工具拒选等路由层指标。

    `routes[case_id]` 是路由器按分数降序给出的候选工具名；期望工具必须全部落在
    Top-K 才算召回。越权暴露按全部样本统计，无工具拒选只统计 `expected_tools` 为空的样本。
    """
    diagnostics = diagnostics or {}
    confirmation = set(confirmation_tools)
    recall_samples: list[bool] = []
    exact_samples: list[bool] = []
    precision_samples: list[float] = []
    rejection_samples: list[bool] = []
    side_effect_samples: list[bool] = []
    candidate_counts: list[int] = []
    layer_counts: Counter = Counter()
    latencies: list[float] = []
    missing_routes: list[str] = []
    exposures = 0
    failures: list[dict] = []
    by_category: dict[str, list[dict]] = defaultdict(list)

    for case in cases:
        if case.id not in routes:
            missing_routes.append(case.id)
            continue
        candidates = list(routes[case.id])[:k]
        expected = set(case.expected_tools)
        forbidden = set(case.forbidden_tools)
        candidate_set = set(candidates)
        candidate_counts.append(len(candidates))

        exposed = sorted(forbidden & candidate_set)
        if exposed:
            exposures += 1
            failures.append(
                {
                    "id": case.id,
                    "category": case.category,
                    "reason": "forbidden_tool_exposed",
                    "candidates": candidates,
                    "expected": sorted(forbidden),
                }
            )

        recalled = expected <= candidate_set
        if expected:
            recall_samples.append(recalled)
            exact_samples.append(candidate_set == expected)
            precision_samples.append(
                len(expected & candidate_set) / len(candidates) if candidates else 0.0
            )
            if not recalled:
                failures.append(
                    {
                        "id": case.id,
                        "category": case.category,
                        "reason": "expected_tool_not_recalled",
                        "candidates": candidates,
                        "expected": sorted(expected),
                    }
                )
        else:
            rejection_samples.append(not candidates)
            if candidates:
                failures.append(
                    {
                        "id": case.id,
                        "category": case.category,
                        "reason": "unexpected_candidates",
                        "candidates": candidates,
                        "expected": [],
                    }
                )

        gated = forbidden & confirmation
        if gated:
            side_effect_samples.append(not (gated & candidate_set))

        info = diagnostics.get(case.id) or {}
        if info.get("layer"):
            layer_counts[str(info["layer"])] += 1
        latency = info.get("latency_ms")
        if isinstance(latency, (int, float)) and not isinstance(latency, bool):
            latencies.append(float(latency))

        by_category[case.category].append(
            {"recall": recalled, "unauthorized_exposure": bool(exposed)}
        )

    evaluated = len(candidate_counts)
    return {
        "evaluated_samples": evaluated,
        "top_k": k,
        "missing_routes": missing_routes,
        "recall_at_k": _rate(recall_samples),
        "exact_match_at_k": _rate(exact_samples),
        "precision_at_k": round(sum(precision_samples) / len(precision_samples), 4)
        if precision_samples
        else None,
        "no_tool_rejection_accuracy": _rate(rejection_samples),
        "unauthorized_exposure_rate": round(exposures / evaluated, 4) if evaluated else None,
        "side_effect_interception_rate": _rate(side_effect_samples),
        "avg_candidate_count": round(sum(candidate_counts) / evaluated, 4) if evaluated else None,
        "layer_distribution": dict(sorted(layer_counts.items())),
        "route_latency_ms": _summarize_latency(latencies),
        "by_category": {
            category: {
                "samples": len(samples),
                "recall": round(sum(sample["recall"] for sample in samples) / len(samples), 4),
                "unauthorized_exposure": round(
                    sum(sample["unauthorized_exposure"] for sample in samples) / len(samples), 4
                ),
            }
            for category, samples in sorted(by_category.items())
        },
        "failures": failures,
    }
