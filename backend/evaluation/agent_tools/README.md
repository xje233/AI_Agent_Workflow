# Agent tool-call evaluation

This dataset evaluates whether the Agent uses the right tools and whether the
execution is efficient and reliable. It is separate from the RAG answer/retrieval
evaluation.

The checked-in set contains 24 tasks across knowledge search, document analysis,
database, Python, notification, chat, multi-intent, and boundary cases.

## Validate the dataset

From `backend`:

```bash
python scripts/evaluate_agent_tools.py --validate-only
```

## Evaluate runtime traces

The chat service emits a safe `tool_call_trace` field in its `chat_timing` JSON
log. Each call contains:

- `name`: tool name;
- `status`: `success`, `parameter_error`, `error`, or `timeout`;
- `duration_ms`: execution duration;
- `args_fingerprint`: hash of arguments, never the raw arguments.

Save one JSONL row per task using this shape:

```json
{"id":"knowledge-001","tool_calls":[{"name":"search_tool","status":"success","duration_ms":83.2,"args_fingerprint":"..."}]}
```

Then run:

```bash
python scripts/evaluate_agent_tools.py \
  --traces evaluation/agent_tools/traces.jsonl
```

The report contains:

- `selection_accuracy`: exact match between actual and expected tool sets;
- `parameter_error_rate`: parameter errors divided by all tool calls;
- `duplicate_call_rate`: repeated tool plus argument-fingerprint calls divided by all calls;
- `tool_error_rate`: parameter and execution errors divided by all calls;
- `execution_error_rate`: execution errors and timeouts divided by all calls;
- `latency_ms`: sample count, average, P50, P95, and maximum call duration;
- category breakdown and selection failure cases.

A missing trace is reported separately and does not silently count as a passing
or failing tool selection sample.
