import unittest

from app.evaluation.agent_tools import ToolCallRecord, ToolEvalCase, score_tool_traces


class AgentToolEvaluationTests(unittest.TestCase):
    def test_scores_selection_errors_parameter_errors_duplicates_errors_and_latency(self):
        cases = [
            ToolEvalCase("q1", "knowledge", "查制度", ("search_tool",)),
            ToolEvalCase("q2", "data", "查数据", ("query_db",)),
        ]
        traces = {
            "q1": [
                ToolCallRecord("search_tool", "success", 100.0, "same"),
                ToolCallRecord("search_tool", "success", 120.0, "same"),
            ],
            "q2": [
                ToolCallRecord("query_db", "parameter_error", 50.0, "bad"),
                ToolCallRecord("run_python", "error", 80.0, "wrong"),
            ],
        }

        report = score_tool_traces(cases, traces)

        self.assertEqual(report["evaluated_samples"], 2)
        self.assertEqual(report["selection_accuracy"], 0.5)
        self.assertEqual(report["tool_calls"], 4)
        self.assertEqual(report["parameter_error_rate"], 0.25)
        self.assertEqual(report["duplicate_call_rate"], 0.25)
        self.assertEqual(report["tool_error_rate"], 0.5)
        self.assertEqual(report["latency_ms"]["samples"], 4)
        self.assertEqual(report["latency_ms"]["p50"], 90.0)
        self.assertEqual(report["latency_ms"]["p95"], 117.0)

    def test_empty_expected_tools_requires_no_calls(self):
        case = ToolEvalCase("q1", "chat", "你好", ())

        no_call_report = score_tool_traces([case], {"q1": []})
        call_report = score_tool_traces(
            [case], {"q1": [ToolCallRecord("search_tool", "success", 10.0)]}
        )

        self.assertEqual(no_call_report["selection_accuracy"], 1.0)
        self.assertEqual(call_report["selection_accuracy"], 0.0)

    def test_missing_traces_are_reported_without_distorting_rates(self):
        cases = [
            ToolEvalCase("q1", "knowledge", "查制度", ("search_tool",)),
            ToolEvalCase("q2", "data", "查数据", ("query_db",)),
        ]

        report = score_tool_traces(cases, {"q1": []})

        self.assertEqual(report["evaluated_samples"], 1)
        self.assertEqual(report["missing_traces"], ["q2"])
        self.assertEqual(report["selection_accuracy"], 0.0)


if __name__ == "__main__":
    unittest.main()
