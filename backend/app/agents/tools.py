"""Agent tool definitions for fund analysis.

Each tool wraps a datasource method obtained via ``get_datasource()``.
Tools are grouped by domain and mapped to specific agent types.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from langchain_core.tools import tool

if TYPE_CHECKING:
    from collections.abc import Callable

from app.graph.workflow import get_datasource

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


@tool
async def get_fund_nav_detail(code: str, days: int = 365) -> str:
    """获取基金净值详情，包括单位净值和累计净值。

    返回指定天数的净值记录，包含日期、单位净值、累计净值和日收益率。

    Args:
        code: 基金代码 (e.g., "000001")
        days: 历史天数，默认 365 天

    Returns:
        JSON 字符串，每条记录包含 date, nav, acc_nav, daily_return
    """
    try:
        ds = get_datasource()
        records = await ds.get_fund_nav(code, days=days)
        return json.dumps(
            [r.model_dump() if hasattr(r, "model_dump") else r for r in records],
            ensure_ascii=False,
            default=str,
        )
    except Exception as e:
        return json.dumps({"error": f"获取净值数据失败: {str(e)}"}, ensure_ascii=False)


@tool
async def get_fund_portfolio(code: str) -> str:
    """获取基金前十大持仓。

    返回基金最新的前十大重仓股信息，包括股票代码、股票名称、
    占净值比例、持股数和持仓市值。

    Args:
        code: 基金代码 (e.g., "000001")

    Returns:
        JSON 字符串，包含 fund_code, report_date, top_10_stocks 列表
    """
    try:
        ds = get_datasource()
        portfolio = await ds.get_fund_portfolio(code)
        return json.dumps(
            portfolio.model_dump() if hasattr(portfolio, "model_dump") else portfolio,
            ensure_ascii=False,
            default=str,
        )
    except Exception as e:
        return json.dumps({"error": f"获取持仓数据失败: {str(e)}"}, ensure_ascii=False)


@tool
async def get_sector_allocation(code: str) -> str:
    """获取基金行业配置数据。

    返回基金在各行业（如制造业、金融业、信息技术等）的投资比例分布。

    Args:
        code: 基金代码 (e.g., "000001")

    Returns:
        JSON 字符串，包含行业配置明细列表（行业名称、配置比例等）
    """
    try:
        ds = get_datasource()
        records = await ds.get_fund_portfolio_industry_allocation(code)
        return json.dumps(records, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"获取行业配置数据失败: {str(e)}"}, ensure_ascii=False)


@tool
async def get_fund_manager(code: str) -> str:
    """获取基金经理信息。

    返回管理该基金的基金经理背景资料，包括姓名、从业年限、
    管理基金数量、管理资产规模等。

    Args:
        code: 基金代码 (e.g., "000001")

    Returns:
        JSON 字符串，包含基金经理详细信息
    """
    try:
        ds = get_datasource()
        info = await ds.get_fund_manager(code)
        return json.dumps(
            info.model_dump() if hasattr(info, "model_dump") else info,
            ensure_ascii=False,
            default=str,
        )
    except Exception as e:
        return json.dumps({"error": f"获取基金经理数据失败: {str(e)}"}, ensure_ascii=False)


@tool
async def get_macro_cpi() -> str:
    """获取中国 CPI（居民消费价格指数）年度历史数据。

    返回历年 CPI 数据，用于分析通胀趋势和宏观经济环境。

    Args:
        无参数

    Returns:
        JSON 字符串，包含各年份的 CPI 数据
    """
    try:
        ds = get_datasource()
        data = await ds.get_macro("cpi")
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"获取CPI数据失败: {str(e)}"}, ensure_ascii=False)


@tool
async def get_macro_gdp() -> str:
    """获取中国 GDP（国内生产总值）年度历史数据。

    返回历年 GDP 数据，用于分析经济增长趋势和宏观经济环境。

    Args:
        无参数

    Returns:
        JSON 字符串，包含各年份的 GDP 数据
    """
    try:
        ds = get_datasource()
        data = await ds.get_macro("gdp")
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"获取GDP数据失败: {str(e)}"}, ensure_ascii=False)


@tool
async def get_fund_announcements(code: str, limit: int = 5) -> str:
    """获取基金公告信息。

    返回该基金最近发布的官方公告，包括公告标题和发布日期。

    Args:
        code: 基金代码 (e.g., "000001")
        limit: 返回公告数量，默认 5 条

    Returns:
        JSON 字符串，包含公告列表（标题、日期等）
    """
    try:
        ds = get_datasource()
        records = await ds.get_fund_announcements(code, limit=limit)
        return json.dumps(records, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"获取基金公告数据失败: {str(e)}"}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool groups
# ---------------------------------------------------------------------------

TOOL_GROUPS: dict[str, list[str]] = {
    "general": ["get_fund_nav_detail"],
    "portfolio": ["get_fund_portfolio", "get_sector_allocation"],
    "manager": ["get_fund_manager"],
    "macro": ["get_macro_cpi", "get_macro_gdp"],
    "news": ["get_fund_announcements"],
}

# ---------------------------------------------------------------------------
# Agent-to-tool mapping
# ---------------------------------------------------------------------------

AGENT_TOOL_GROUPS: dict[str, list[str]] = {
    "fundamental": ["general"],
    "technical": ["general"],
    "sector": ["general", "portfolio"],
    "manager": ["general", "manager"],
    "sentiment": ["general", "news"],
    "news": ["general", "news"],
    "macro": ["general", "macro"],
}

# All tool functions keyed by name for programmatic lookup
_all_tools: dict[str, Callable[..., Any]] = {
    "get_fund_nav_detail": get_fund_nav_detail,
    "get_fund_portfolio": get_fund_portfolio,
    "get_sector_allocation": get_sector_allocation,
    "get_fund_manager": get_fund_manager,
    "get_macro_cpi": get_macro_cpi,
    "get_macro_gdp": get_macro_gdp,
    "get_fund_announcements": get_fund_announcements,
}


def get_tools_for_agent(agent_type: str) -> list[Callable[..., Any]]:
    """Return the list of tool functions for a given analyst type.

    Args:
        agent_type: One of the 7 analyst types (e.g. "sector", "macro")

    Returns:
        List of LangChain tool functions (decorated with @tool)

    Raises:
        ValueError: If *agent_type* is not a recognised analyst type.
    """
    if agent_type not in AGENT_TOOL_GROUPS:
        msg = f"Unknown agent type: {agent_type}. Valid types: {list(AGENT_TOOL_GROUPS)}"
        raise ValueError(msg)

    tool_names: list[str] = []
    for group_name in AGENT_TOOL_GROUPS[agent_type]:
        tool_names.extend(TOOL_GROUPS[group_name])

    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique_tool_names: list[str] = []
    for name in tool_names:
        if name not in seen:
            seen.add(name)
            unique_tool_names.append(name)

    return [_all_tools[name] for name in unique_tool_names]
