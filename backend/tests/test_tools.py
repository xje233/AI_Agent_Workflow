import asyncio
import unittest
from dataclasses import replace
from unittest.mock import patch

from app.agent.tool_router import (
    TOOL_CARDS,
    RoutingContext,
    check_tool_authorized,
    classify_domains,
    filter_cards,
    lexical_scores,
    route_tools,
)
from app.agent.tools import ALL_TOOLS


def route(question, **kwargs):
    """离线路由：embedding_weight=0.0 保证测试不触发任何 Embedding 调用。"""
    kwargs.setdefault("embedding_weight", 0.0)
    return asyncio.run(route_tools(question, **kwargs))


DEV_CONTEXT = RoutingContext(environment="dev", confirmed=True)


class RouteToolsTests(unittest.TestCase):
    def test_exposes_all_matching_domains_without_confirmation(self):
        decision = route("检索知识库并用 Python 计算结果，再发送邮件通知")

        self.assertEqual([card.name for card in decision.cards], ["search_tool", "run_python"])
        self.assertEqual(decision.domains, ("compute", "knowledge"))
        self.assertEqual(decision.reason, "domain_and_retrieval")
        self.assertEqual(decision.layer, "lexical")

    def test_exposes_high_risk_tool_only_after_confirmation(self):
        names = [
            card.name
            for card in route(
                "检索知识库并用 Python 计算结果，再发送邮件通知，确认发送",
                context=DEV_CONTEXT,
            ).cards
        ]

        self.assertIn("send_email", names)
        self.assertEqual(names[0], "send_email")

    def test_records_dropped_reason_for_gated_tool(self):
        decision = route("发送邮件通知项目负责人", context=RoutingContext(environment="dev"))

        self.assertEqual(decision.cards, ())
        self.assertIn({"name": "send_email", "reason": "requires_confirmation"}, decision.dropped)

    def test_returns_no_candidates_without_tool_intent(self):
        decision = route("概括一下当前项目")

        self.assertEqual(decision.cards, ())
        self.assertEqual(decision.layer, "no_intent")
        self.assertEqual(decision.reason, "no_tool_intent")

    def test_explicit_all_request_still_respects_confirmation_gate(self):
        decision = route("请调用所有工具完成这个任务", context=RoutingContext(environment="dev"))

        self.assertEqual(decision.layer, "explicit_all")
        self.assertEqual(
            {card.name for card in decision.cards},
            {"search_tool", "query_db", "analyze_doc", "run_python"},
        )

    def test_exposes_at_most_top_k(self):
        decision = route(
            "检索知识库，分析文档，再用 Python 计算并发送邮件",
            context=DEV_CONTEXT,
            top_k=2,
        )

        self.assertLessEqual(len(decision.cards), 2)

    def test_production_environment_drops_cards_restricted_to_dev(self):
        dev_only = replace(TOOL_CARDS[0], environments=("dev",))

        allowed, dropped = filter_cards([dev_only], RoutingContext(environment="prod"))

        self.assertEqual(allowed, [])
        self.assertEqual(dropped, [{"name": dev_only.name, "reason": "environment_mismatch"}])

    def test_scope_restriction_limits_candidates(self):
        decision = route(
            "检索知识库并发送邮件确认发送",
            context=RoutingContext(scopes=frozenset({"knowledge:read"}), environment="dev", confirmed=True),
        )

        self.assertEqual([card.name for card in decision.cards], ["search_tool"])
        self.assertIn({"name": "send_email", "reason": "missing_scope"}, decision.dropped)


class ToolRegistryTests(unittest.TestCase):
    def test_registry_declares_routing_metadata(self):
        self.assertEqual({card.name for card in TOOL_CARDS}, {tool.name for tool in ALL_TOOLS})
        for card in TOOL_CARDS:
            self.assertTrue(card.namespace and card.category and card.risk)
            self.assertTrue(card.required_scope and card.when_to_use and card.when_not_to_use)
            self.assertTrue(card.environments)

        cards = {card.name: card for card in TOOL_CARDS}
        self.assertTrue(cards["send_email"].requires_confirmation)
        self.assertFalse(cards["send_email"].read_only)
        self.assertTrue(cards["query_db"].read_only)
        self.assertTrue(all("dev" in card.environments for card in TOOL_CARDS))

    def test_descriptions_carry_negative_boundary(self):
        for card in TOOL_CARDS:
            self.assertIn("不适用：", card.tool.description)


class HybridRetrievalTests(unittest.TestCase):
    def test_embedding_weight_reorders_candidates_and_marks_layer_hybrid(self):
        class _FakeEmbeddings:
            """knowledge.search 映射到第一维，其余卡片映射到第二维。"""

            def embed_documents(self, texts):
                return [
                    [1.0, 0.0] if "knowledge.search" in text else [0.0, 1.0] for text in texts
                ]

            def embed_query(self, text):
                return [0.0, 1.0]

        with patch("app.agent.tool_router.get_embeddings", return_value=_FakeEmbeddings()), patch(
            "app.agent.tool_router._DENSE_DISABLED", False
        ), patch("app.agent.tool_router._CARD_VECTORS", None):
            decision = asyncio.run(
                route_tools("分析文档并检索知识库", embedding_weight=1.0)
            )

        self.assertEqual(decision.layer, "hybrid")
        self.assertEqual([card.name for card in decision.cards], ["analyze_doc"])


class ClassifyAndScoreTests(unittest.TestCase):
    def test_classify_domains_is_multi_label_and_silent_on_chat(self):
        self.assertEqual(
            classify_domains("检索知识库并用 Python 计算", TOOL_CARDS), ("compute", "knowledge")
        )
        self.assertEqual(classify_domains("你好，请介绍一下你自己", TOOL_CARDS), ())

    def test_lexical_scores_reward_rare_terms(self):
        self.assertGreater(lexical_scores("用 sql 统计记录", TOOL_CARDS)["query_db"], 0.0)
        self.assertEqual(set(lexical_scores("你好", TOOL_CARDS).values()), {0.0})

    def test_check_tool_authorized(self):
        self.assertTrue(check_tool_authorized("search_tool", {"search_tool"}))
        self.assertFalse(check_tool_authorized("send_email", {"search_tool"}))


if __name__ == "__main__":
    unittest.main()
