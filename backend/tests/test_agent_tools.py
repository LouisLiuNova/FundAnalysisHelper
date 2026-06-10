"""Tests for app.agents.tools — tool definitions, groups, mapping and factory."""

from __future__ import annotations

import pytest

from app.agents.tools import (
    AGENT_TOOL_GROUPS,
    TOOL_GROUPS,
    get_fund_announcements,
    get_fund_manager,
    get_fund_nav_detail,
    get_fund_portfolio,
    get_macro_cpi,
    get_macro_gdp,
    get_sector_allocation,
    get_tools_for_agent,
)

# ---------------------------------------------------------------------------
# Tool existence
# ---------------------------------------------------------------------------


def test_all_7_tools_defined():
    """Verify all 7 tool names exist and are structured tools."""
    tool_names = [
        "get_fund_nav_detail",
        "get_fund_portfolio",
        "get_sector_allocation",
        "get_fund_manager",
        "get_macro_cpi",
        "get_macro_gdp",
        "get_fund_announcements",
    ]
    for name in tool_names:
        tool_func = globals()[name]
        assert hasattr(tool_func, "name"), f"{name} should have 'name' attribute"
        assert tool_func.name == name, f"tool_func.name should be '{name}'"
        assert hasattr(tool_func, "ainvoke"), f"{name} should have 'ainvoke' method"
        assert hasattr(tool_func, "invoke"), f"{name} should have 'invoke' method"


# ---------------------------------------------------------------------------
# Tool groups structure
# ---------------------------------------------------------------------------


def test_tool_groups_structure():
    """Verify TOOL_GROUPS has the correct 5 groups with expected tool counts."""
    assert isinstance(TOOL_GROUPS, dict)

    expected_groups = {
        "general": 1,
        "portfolio": 2,
        "manager": 1,
        "macro": 2,
        "news": 1,
    }
    assert set(TOOL_GROUPS.keys()) == set(expected_groups.keys()), (
        f"Expected groups {set(expected_groups)} but got {set(TOOL_GROUPS)}"
    )
    for group, expected_count in expected_groups.items():
        assert len(TOOL_GROUPS[group]) == expected_count, (
            f"Group '{group}' expected {expected_count} tools, got {len(TOOL_GROUPS[group])}"
        )


# ---------------------------------------------------------------------------
# Agent-to-tool-group mapping
# ---------------------------------------------------------------------------


def test_agent_tool_groups_mapping():
    """Verify AGENT_TOOL_GROUPS maps all 7 analysts to correct groups."""
    assert isinstance(AGENT_TOOL_GROUPS, dict)

    expected_mapping = {
        "fundamental": ["general"],
        "technical": ["general"],
        "sector": ["general", "portfolio"],
        "manager": ["general", "manager"],
        "sentiment": ["general", "news"],
        "news": ["general", "news"],
        "macro": ["general", "macro"],
    }
    assert set(AGENT_TOOL_GROUPS.keys()) == set(expected_mapping.keys()), (
        f"Expected agents {set(expected_mapping)} but got {set(AGENT_TOOL_GROUPS)}"
    )
    for agent, expected_groups in expected_mapping.items():
        assert AGENT_TOOL_GROUPS[agent] == expected_groups, (
            f"Agent '{agent}' expected groups {expected_groups}, got {AGENT_TOOL_GROUPS[agent]}"
        )


# ---------------------------------------------------------------------------
# Factory: get_tools_for_agent
# ---------------------------------------------------------------------------


def test_get_tools_for_agent_fundamental_返回通用工具():
    """fundamental agent 只应拿到 general 组工具（1 个：get_fund_nav_detail）。"""
    tools = get_tools_for_agent("fundamental")
    assert len(tools) == 1
    assert tools[0].name == "get_fund_nav_detail"


def test_get_tools_for_agent_sector_返回通用加组合工具():
    """sector agent 应拿到 general + portfolio 组工具（共 3 个）。"""
    tools = get_tools_for_agent("sector")
    assert len(tools) == 3
    names = {t.name for t in tools}
    assert names == {"get_fund_nav_detail", "get_fund_portfolio", "get_sector_allocation"}


def test_get_tools_for_agent_macro_返回通用加宏观工具():
    """macro agent 应拿到 general + macro 组工具（共 3 个）。"""
    tools = get_tools_for_agent("macro")
    assert len(tools) == 3
    names = {t.name for t in tools}
    assert names == {"get_fund_nav_detail", "get_macro_cpi", "get_macro_gdp"}


def test_get_tools_for_agent_news_返回通用加新闻工具():
    """news agent 应拿到 general + news 组工具（共 2 个）。"""
    tools = get_tools_for_agent("news")
    assert len(tools) == 2
    names = {t.name for t in tools}
    assert names == {"get_fund_nav_detail", "get_fund_announcements"}


def test_get_tools_for_agent_no_duplicates_共享工具不重复():
    """get_fund_nav_detail 同时在 general 和 manager 组，但不重复出现。"""
    tools = get_tools_for_agent("manager")
    assert len(tools) == 2
    names = [t.name for t in tools]
    assert names.count("get_fund_nav_detail") == 1, "Shared tool should appear only once"


def test_get_tools_for_agent_invalid_type_未知类型抛出():
    """传入不存在的 agent type 应抛出 ValueError。"""
    with pytest.raises(ValueError, match="Unknown agent type"):
        get_tools_for_agent("nonexistent_analyst")


# ---------------------------------------------------------------------------
# Docstring check
# ---------------------------------------------------------------------------


def test_tool_has_docstring_每个工具有文档字符串():
    """Each tool function must have a non-empty docstring."""
    all_tool_funcs = [
        get_fund_nav_detail,
        get_fund_portfolio,
        get_sector_allocation,
        get_fund_manager,
        get_macro_cpi,
        get_macro_gdp,
        get_fund_announcements,
    ]
    for func in all_tool_funcs:
        assert func.__doc__ and func.__doc__.strip(), f"{func.__name__} is missing a docstring"
