from app.agent.tools import ALL_TOOLS, TOOL_SPECS, select_tools


def test_select_tools_combines_all_matching_categories():
    tools = select_tools("检索知识库并用 Python 计算结果，再发送邮件通知")

    assert [tool.name for tool in tools] == [
        "search_tool",
        "run_python",
        "send_email",
    ]


def test_select_tools_keeps_all_tools_for_unmatched_question():
    assert select_tools("概括一下当前项目") == []


def test_select_tools_returns_all_tools_for_explicit_request():
    assert select_tools("请调用所有工具完成这个任务") is ALL_TOOLS


def test_normal_route_exposes_at_most_three_tools():
    tools = select_tools("检索知识库，分析文档，再用 Python 计算并发送邮件")

    assert len(tools) <= 3


def test_tool_registry_declares_risk_and_category_for_each_tool():
    assert {spec.name for spec in TOOL_SPECS} == {
        "search_tool",
        "query_db",
        "analyze_doc",
        "run_python",
        "send_email",
    }
    assert all(spec.category and spec.risk for spec in TOOL_SPECS)
    assert next(spec for spec in TOOL_SPECS if spec.name == "send_email").requires_confirmation
    assert next(spec for spec in TOOL_SPECS if spec.name == "query_db").read_only
