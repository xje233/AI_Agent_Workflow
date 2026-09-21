# Agent 工具调用评测 — 第一版基线报告

> **采集日期**: 2026-07-31
> **模型**: deepseek-v4-flash（`backend/.env` 配置的 OpenAI 兼容接口）
> **任务集**: 24 条（knowledge ×4、document ×3、data ×4、compute ×3、notification ×2、chat ×3、multi_intent ×4、boundary ×1）
> **轨迹文件**: `traces.jsonl`（每条任务独立会话，真实 Agent 运行）
> **机器可读报告**: `latest-report.json`

---

## 总体指标

| 指标 | 值 | 说明 |
| --- | ---: | --- |
| 评估样本数 | 24 | 24/24 均有轨迹，无缺失 |
| **工具选择准确率** | **0.625** | 15/24 任务实际调用集合与预期完全一致 |
| 工具调用总数 | 83 | |
| 参数错误率 | 0.0 | |
| 重复调用率 | 0.0361 | 3/83 次相同工具+参数重复调用 |
| 重复调用案例率 | 0.125 | 3/24 个案例存在重复调用 |
| 工具错误率 | 0.0 | |
| 执行错误率 | 0.0 | 无参数错误、执行错误或超时 |

### 工具调用耗时（单次工具执行，ms）

| 统计 | 值 |
| --- | ---: |
| 样本数 | 83 |
| 平均 | 138.72 |
| P50 | 1.78 |
| P95 | 215.05 |
| 最大 | 9231.41 |

> P50 极低是因为 query_db/send_email 等本地工具在毫秒级完成；P95 与 max 由 search_tool 的向量检索耗时贡献（首次冷启动连接可达 9.2s）。

---

## 分类正确率

| 分类 | 正确/总数 | 正确率 | 备注 |
| --- | ---: | ---: | --- |
| knowledge | 4/4 | 1.00 | search_tool 全部命中 |
| data | 4/4 | 1.00 | query_db 全部命中 |
| chat | 3/3 | 1.00 | 无工具意图，未调用工具 |
| boundary | 1/1 | 1.00 | 边界问题未误调工具 |
| notification | 1/2 | 0.50 | notification-001 未调用 send_email |
| multi_intent | 2/4 | 0.50 | multi-001/003 少调或未调工具 |
| document | 0/3 | 0.00 | analyze_doc 均未调用 |
| compute | 0/3 | 0.00 | run_python 均未调用 |

---

## 失败案例分析（9 条）

| 任务 | 预期工具 | 实际工具 | 类别 |
| --- | --- | --- | --- |
| document-001/002/003 | analyze_doc | 无 | 模型未调用 analyze_doc |
| compute-001/002/003 | run_python | 无 | 模型未调用 run_python |
| notification-001 | send_email | 无 | 模型未调用 send_email |
| multi-001 | search_tool, run_python | search_tool | 只检索，未执行计算 |
| multi-003 | analyze_doc, send_email | 无 | 未调用任何工具 |

### 归因

路由层（`select_tools`）已通过验证：上述失败任务的工具暴露均为预期集合
（document → analyze_doc，compute → run_python，notification → send_email，
multi-001 → search_tool+run_python，multi-003 → analyze_doc+send_email）。

因此失败全部发生在**模型工具调用决策层**：模型收到可用工具后选择直接文本回答，
未发起工具调用。可能与以下因素相关：

- 题目未提供具体文件名/收件人等信息，模型倾向先回答或反问；
- `analyze_doc`/`send_email` 为模拟实现，工具描述对模型吸引力不足；
- 多意图题目中模型只执行了部分意图。

---

## 复现命令

```bash
cd backend

# 1. 校验数据集
../.venv/Scripts/python.exe scripts/evaluate_agent_tools.py --validate-only

# 2. 用 24 条任务集运行 Agent，采集真实轨迹（需基础设施与 LLM 配置就绪）
../.venv/Scripts/python.exe scripts/collect_agent_tool_traces.py

# 3. 基于轨迹计算指标并输出 latest-report.json
../.venv/Scripts/python.exe scripts/evaluate_agent_tools.py --traces evaluation/agent_tools/traces.jsonl
```

> 采集脚本为 `scripts/collect_agent_tool_traces.py`，支持 `--ids` 子集运行与 `--output` 指定输出路径。
