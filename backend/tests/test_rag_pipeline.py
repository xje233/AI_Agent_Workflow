import unittest
from unittest.mock import patch

from langchain.schema import Document

from app.rag.pipeline import evaluate_retrieval, route_query, rewrite_query, validate_answer


class RagPipelineTests(unittest.TestCase):
    def test_casual_chat_skips_retrieval(self):
        route = route_query("你好")
        self.assertFalse(route.should_retrieve)
        self.assertEqual(route.reason, "casual_chat")

    def test_knowledge_question_uses_retrieval(self):
        route = route_query("请问员工报销流程是什么？")
        self.assertTrue(route.should_retrieve)
        self.assertEqual(route.reason, "knowledge_intent")

    def test_rewrite_removes_polite_prefix_and_keeps_entities(self):
        self.assertEqual(rewrite_query("请问 2025 年报销上限是多少？"), "2025 年报销上限是多少？")

    def test_evaluation_filters_weak_hits_and_duplicates(self):
        first = Document(page_content="报销上限为一万元", metadata={"source": "policy.md"})
        duplicate = Document(page_content="报销上限为一万元", metadata={"source": "policy.md"})
        weak = Document(page_content="无关内容", metadata={"source": "other.md"})
        documents, scores = evaluate_retrieval(
            [(first, 0.9), (duplicate, 0.8), (weak, 0.2)], threshold=0.35
        )
        self.assertEqual(documents, [first])
        self.assertEqual(scores, [0.9])

    @patch("app.rag.pipeline.OutputGuard.validate")
    def test_answer_without_evidence_is_rejected(self, validate):
        validate.return_value = {
            "text": "可能是五万元。",
            "has_issue": False,
            "issues": [],
            "used_fallback": False,
        }
        result = validate_answer("可能是五万元。", [], routed_to_retrieval=True)
        self.assertTrue(result["used_fallback"])
        self.assertIn("未找到", result["text"])

    def test_refusal_without_evidence_is_allowed(self):
        result = validate_answer("未找到相关文档，无法确认。", [], routed_to_retrieval=True)
        self.assertFalse(result["used_fallback"])


if __name__ == "__main__":
    unittest.main()
