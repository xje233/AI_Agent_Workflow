import unittest
from pathlib import Path


CHAT_SERVICE = Path(__file__).parents[1] / "app" / "services" / "chat_service.py"


class TTFTMetricSourceTest(unittest.TestCase):
    def test_sse_enqueue_metrics_use_model_boundary_and_expose_segments(self):
        source = CHAT_SERVICE.read_text(encoding="utf-8")

        self.assertIn("backend_model_to_sse_ms", source)
        self.assertIn("backend_request_to_sse_ms", source)
        self.assertIn(
            'metrics["first_sse_enqueued"] - metrics["model_request_started"]',
            source,
        )

    def test_chat_service_has_direct_simple_chat_path(self):
        source = (CHAT_SERVICE.parent / "chat_service.py").read_text(encoding="utf-8")

        self.assertIn("simple_chat", source)
        self.assertIn("get_llm", source)
        self.assertIn("tools = []", source)
        self.assertIn("simple_chat_enabled", source)


if __name__ == "__main__":
    unittest.main()
