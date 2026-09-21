import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.agent.tools import _validate_read_query, query_db


class QueryDbValidationTests(unittest.TestCase):
    def test_accepts_explicit_columns_from_allowed_table(self):
        query = _validate_read_query(
            "SELECT id, title FROM conversations ORDER BY created_at DESC"
        )
        self.assertIn("LIMIT 100", query.upper())

    def test_rejects_wildcard_to_prevent_unapproved_columns(self):
        with self.assertRaisesRegex(ValueError, "明确列名"):
            _validate_read_query("SELECT * FROM documents")

    def test_rejects_non_allowlisted_table(self):
        with self.assertRaisesRegex(ValueError, "不允许查询的表"):
            _validate_read_query("SELECT username FROM users")

    def test_rejects_multiple_statements_and_comments(self):
        for query in (
            "SELECT id FROM conversations; DELETE FROM messages",
            "SELECT id FROM conversations -- expose more data",
        ):
            with self.assertRaises(ValueError):
                _validate_read_query(query)

    def test_rejects_join_and_caps_requested_limit(self):
        with self.assertRaisesRegex(ValueError, "JOIN"):
            _validate_read_query(
                "SELECT conversations.id FROM conversations JOIN messages ON messages.conversation_id = conversations.id"
            )
        with self.assertRaisesRegex(ValueError, "100"):
            _validate_read_query("SELECT id FROM conversations LIMIT 101")

    def test_query_db_executes_real_rows_and_returns_structured_output(self):
        async def run():
            with patch(
                "app.agent.tools._execute_read_query",
                new=AsyncMock(return_value=[{"id": "c1", "title": "测试会话"}]),
            ):
                result = await query_db.ainvoke({"sql": "SELECT id, title FROM conversations"})
            self.assertIn("数据库查询成功", result)
            self.assertIn("测试会话", result)

        asyncio.run(run())

    def test_query_db_does_not_expose_database_exception(self):
        async def run():
            with patch(
                "app.agent.tools._execute_read_query",
                new=AsyncMock(side_effect=RuntimeError("secret connection details")),
            ):
                result = await query_db.ainvoke({"sql": "SELECT id FROM conversations"})
            self.assertIn("数据库查询失败", result)
            self.assertNotIn("secret connection details", result)

        asyncio.run(run())

    def test_query_db_handles_timeout(self):
        async def run():
            async def slow_query(_sql):
                await asyncio.sleep(0.05)

            with patch("app.agent.tools._execute_read_query", new=slow_query), patch(
                "app.agent.tools.get_settings"
            ) as settings:
                settings.return_value.database_query_timeout_seconds = 0.001
                result = await query_db.ainvoke({"sql": "SELECT id FROM conversations"})
            self.assertIn("数据库查询超时", result)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
