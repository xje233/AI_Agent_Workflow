import unittest

from app.evaluation.agent_tools import (
    ToolCallRecord,
    ToolEvalCase,
    score_routing,
    score_tool_traces,
)


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


class ScoreRoutingTests(unittest.TestCase):
    def test_scores_recall_rejection_and_exposure(self):
        cases = [
            ToolEvalCase("q1", "knowledge", "查制度", ("search_tool",)),
            ToolEvalCase("q2", "chat", "你好", (), ("send_email",)),
        ]

        report = score_routing(cases, {"q1": ["search_tool"], "q2": []})

        self.assertEqual(report["evaluated_samples"], 2)
        self.assertEqual(report["recall_at_k"], 1.0)
        self.assertEqual(report["exact_match_at_k"], 1.0)
        self.assertEqual(report["precision_at_k"], 1.0)
        self.assertEqual(report["no_tool_rejection_accuracy"], 1.0)
        self.assertEqual(report["unauthorized_exposure_rate"], 0.0)

    def test_forbidden_tool_exposure_is_reported(self):
        case = ToolEvalCase("q1", "unauthorized", "发邮件", (), ("send_email",))

        report = score_routing([case], {"q1": ["send_email"]})

        self.assertEqual(report["unauthorized_exposure_rate"], 1.0)
        self.assertEqual(report["no_tool_rejection_accuracy"], 0.0)
        self.assertEqual(report["failures"][0]["reason"], "forbidden_tool_exposed")

    def test_partial_recall_reduces_recall_and_precision(self):
        case = ToolEvalCase("q1", "multi_intent", "两件事", ("search_tool", "run_python"))

        report = score_routing([case], {"q1": ["search_tool", "query_db"]})

        self.assertEqual(report["recall_at_k"], 0.0)
        self.assertEqual(report["exact_match_at_k"], 0.0)
        self.assertEqual(report["precision_at_k"], 0.5)
        self.assertEqual(report["failures"][0]["reason"], "expected_tool_not_recalled")

    def test_missing_routes_are_reported_without_distorting_rates(self):
        cases = [
            ToolEvalCase("q1", "knowledge", "查制度", ("search_tool",)),
            ToolEvalCase("q2", "data", "查数据", ("query_db",)),
        ]

        report = score_routing(cases, {"q1": ["search_tool"]})

        self.assertEqual(report["evaluated_samples"], 1)
        self.assertEqual(report["missing_routes"], ["q2"])
        self.assertEqual(report["recall_at_k"], 1.0)

    def test_side_effect_interception_rate_tracks_confirmation_tools(self):
        case = ToolEvalCase("q1", "unauthorized", "发邮件", (), ("send_email",))

        intercepted = score_routing([case], {"q1": []}, confirmation_tools=("send_email",))
        leaked = score_routing([case], {"q1": ["send_email"]}, confirmation_tools=("send_email",))

        self.assertEqual(intercepted["side_effect_interception_rate"], 1.0)
        self.assertEqual(leaked["side_effect_interception_rate"], 0.0)
        self.assertIsNone(score_routing([case], {"q1": []})["side_effect_interception_rate"])

    def test_diagnostics_expose_layer_distribution_and_latency(self):
        case = ToolEvalCase("q1", "knowledge", "查制度", ("search_tool",))

        report = score_routing(
            [case],
            {"q1": ["search_tool"]},
            diagnostics={"q1": {"layer": "hybrid", "latency_ms": 12.5}},
        )

        self.assertEqual(report["layer_distribution"], {"hybrid": 1})
        self.assertEqual(report["route_latency_ms"]["samples"], 1)
        self.assertEqual(report["route_latency_ms"]["p50"], 12.5)


if __name__ == "__main__":
    unittest.main()
