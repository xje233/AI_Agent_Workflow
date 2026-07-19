"""Measure chat SSE TTFT and summarize backend timing fields.

Run from the repository root:
    python backend/scripts/measure_ttft.py --url http://localhost:8000 --runs 10
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class Measurement:
    run: int
    scenario: str
    model_ttft_ms: float
    sse_enqueue_ttft_ms: float
    model_to_sse_ms: float
    request_to_sse_ms: float
    browser_ttft_ms: float
    tool_count: int
    history_token_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure chat backend TTFT over SSE")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--runs", type=int, default=10, help="Number of requests")
    parser.add_argument("--message", default=None, help="Custom message sent in every request")
    parser.add_argument(
        "--scenario",
        choices=("simple", "knowledge", "tool", "long"),
        default="simple",
        help="Preset request scenario",
    )
    parser.add_argument("--all-scenarios", action="store_true", help="Run all preset scenarios")
    parser.add_argument("--timeout", type=float, default=120.0, help="Request timeout in seconds")
    parser.add_argument("--warmup", action="store_true", help="Run one uncounted warm-up request")
    return parser.parse_args()


def iter_sse_events(response):
    event_data: list[str] = []
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if line == "":
            if event_data:
                payload = "\n".join(event_data)
                if payload.startswith("data: "):
                    yield json.loads(payload[6:])
                event_data = []
        elif line.startswith("data: "):
            event_data.append(line)
    if event_data:
        payload = "\n".join(event_data)
        if payload.startswith("data: "):
            yield json.loads(payload[6:])


SCENARIOS = {
    "simple": "请用一句话说明你能做什么。",
    "knowledge": "请搜索知识库中的项目性能优化文档并总结关键结论。",
    "tool": "请用 Python 计算 1 到 100 的总和，并给出结果。",
    "long": "请分析当前项目的 LLM 首 token 响应时间，并给出详细优化建议。",
}


def measure_once(url: str, message: str, timeout: float, run: int, scenario: str) -> Measurement:
    request = Request(
        f"{url.rstrip('/')}/api/chat/send",
        data=json.dumps({"message": message}).encode("utf-8"),
        headers={
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        },
        method="POST",
    )
    request_started = time.perf_counter()
    first_event_at = None
    timing = None
    with urlopen(request, timeout=timeout) as response:
        for event in iter_sse_events(response):
            if first_event_at is None and event.get("content"):
                first_event_at = time.perf_counter()
            if event.get("done"):
                timing = event
                break

    if timing is None:
        raise RuntimeError("SSE stream ended without a done event")
    model_ttft = timing.get("backend_model_ttft_ms")
    sse_enqueue_ttft = timing.get("backend_sse_enqueue_ttft_ms")
    if sse_enqueue_ttft is None:
        sse_enqueue_ttft = timing.get("backend_sse_ttft_ms")
    if model_ttft is None or sse_enqueue_ttft is None:
        raise RuntimeError(f"done event has no backend timing fields: {timing}")
    model_to_sse = timing.get("backend_model_to_sse_ms")
    request_to_sse = timing.get("backend_request_to_sse_ms")
    if model_to_sse is None or request_to_sse is None:
        raise RuntimeError(f"done event has no SSE segment timing fields: {timing}")
    if first_event_at is None:
        raise RuntimeError("SSE stream contained no non-empty content event")
    return Measurement(
        run=run,
        scenario=scenario,
        model_ttft_ms=float(model_ttft),
        sse_enqueue_ttft_ms=float(sse_enqueue_ttft),
        model_to_sse_ms=float(model_to_sse),
        request_to_sse_ms=float(request_to_sse),
        browser_ttft_ms=(first_event_at - request_started) * 1000,
        tool_count=int(timing.get("tool_count", 0)),
        history_token_count=int(timing.get("history_token_count", 0)),
    )


def print_summary(measurements: list[Measurement]) -> None:
    if not measurements:
        raise RuntimeError("No successful measurements")
    model_values = [item.model_ttft_ms for item in measurements]
    sse_values = [item.sse_enqueue_ttft_ms for item in measurements]
    browser_values = [item.browser_ttft_ms for item in measurements]
    def percentile(values: list[float], percentile_value: float) -> float:
        if len(values) == 1:
            return values[0]
        return statistics.quantiles(values, n=100, method="inclusive")[int(percentile_value) - 1]

    print("\nTTFT summary")
    print(f"successful runs: {len(measurements)}")
    print(f"average backend_model_ttft_ms: {statistics.fmean(model_values):.2f} ms")
    print(f"average backend_sse_enqueue_ttft_ms: {statistics.fmean(sse_values):.2f} ms")
    print(f"average backend_model_to_sse_ms:       {statistics.fmean([item.model_to_sse_ms for item in measurements]):.2f} ms")
    print(f"average browser TTFT:                {statistics.fmean(browser_values):.2f} ms")
    print(f"p95 backend_model_ttft_ms:      {percentile(model_values, 95):.2f} ms")
    print(f"p95 backend_sse_enqueue_ttft_ms:   {percentile(sse_values, 95):.2f} ms")
    print(f"min/max backend_model_ttft_ms:  {min(model_values):.2f} / {max(model_values):.2f} ms")
    print(f"min/max backend_sse_enqueue_ttft_ms: {min(sse_values):.2f} / {max(sse_values):.2f} ms")
    if len(measurements) > 1:
        print(f"median backend_model_ttft_ms:  {statistics.median(model_values):.2f} ms")
        print(f"median backend_sse_enqueue_ttft_ms: {statistics.median(sse_values):.2f} ms")
        print(f"stdev backend_model_ttft_ms:   {statistics.stdev(model_values):.2f} ms")
        print(f"stdev backend_sse_enqueue_ttft_ms: {statistics.stdev(sse_values):.2f} ms")
    print("\nper run")
    for item in measurements:
        print(
            f"#{item.run}: model={item.model_ttft_ms:.2f} ms, "
            f"scenario={item.scenario}, sse={item.sse_enqueue_ttft_ms:.2f} ms, "
            f"model_to_sse={item.model_to_sse_ms:.2f} ms, "
            f"browser={item.browser_ttft_ms:.2f} ms, tools={item.tool_count}, "
            f"history_tokens={item.history_token_count}"
        )


def main() -> int:
    args = parse_args()
    if args.runs < 1:
        print("--runs must be at least 1", file=sys.stderr)
        return 2
    scenarios = list(SCENARIOS) if args.all_scenarios else [args.scenario]
    all_measurements: list[Measurement] = []
    for scenario in scenarios:
        measurements: list[Measurement] = []
        message = args.message or SCENARIOS[scenario]
        total_runs = args.runs + int(args.warmup)
        for index in range(total_runs):
            run_label = "warmup" if args.warmup and index == 0 else str(index + 1 - int(args.warmup))
            try:
                measurement = measure_once(args.url, message, args.timeout, index + 1, scenario)
                if args.warmup and index == 0:
                    print(f"{scenario} warm-up: completed")
                    continue
                measurements.append(measurement)
                print(
                    f"{scenario} run {run_label}: model={measurement.model_ttft_ms:.2f} ms, "
                    f"sse_enqueue={measurement.sse_enqueue_ttft_ms:.2f} ms"
                )
            except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as error:
                print(f"{scenario} run {run_label}: FAILED: {error}", file=sys.stderr)
        try:
            print(f"\n=== scenario: {scenario} ===")
            print_summary(measurements)
            all_measurements.extend(measurements)
        except RuntimeError as error:
            print(f"{scenario}: {error}", file=sys.stderr)
    if not all_measurements:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
