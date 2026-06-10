"""Tests for AKshare data source adapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.datasource.cache import RedisCache


@pytest.fixture
def akshare_adapter():
    """Create AKshareAdapter with mocked AKShare and cache."""
    from app.datasource.akshare_adapter import AKshareAdapter

    cache = AsyncMock(spec=RedisCache)
    cache.get.return_value = None  # Cache miss by default
    adapter = AKshareAdapter(cache=cache)
    return adapter, cache


@pytest.mark.asyncio
async def test_get_fund_basic_获取基金基本信息(akshare_adapter):
    """Verify basic fund info is fetched from AKShare and mapped correctly."""
    adapter, cache = akshare_adapter

    mock_info_df = pd.DataFrame(
        [
            {"item": "基金代码", "value": "000001"},
            {"item": "基金名称", "value": "华夏成长混合"},
            {"item": "基金全称", "value": "华夏成长证券投资基金"},
            {"item": "基金类型", "value": "混合型-偏股"},
            {"item": "成立时间", "value": "2001-12-18"},
            {"item": "最新规模", "value": "26.44亿"},
            {"item": "基金公司", "value": "华夏基金管理有限公司"},
        ]
    )

    with patch(
        "app.datasource.akshare_adapter.ak.fund_individual_basic_info_xq",
        return_value=mock_info_df,
    ):
        result = await adapter.get_fund_basic("000001")

    assert result.code == "000001"
    assert result.name == "华夏成长混合"
    assert result.fund_type == "混合型-偏股"
    assert result.establish_date == "2001-12-18"
    assert result.aum and result.aum > 0


@pytest.mark.asyncio
async def test_get_fund_basic_代码后缀自动移除(akshare_adapter):
    """Verify Tushare-style code with .OF suffix is normalized for AKShare."""
    adapter, cache = akshare_adapter

    mock_info_df = pd.DataFrame(
        [
            {"item": "基金代码", "value": "000001"},
            {"item": "基金名称", "value": "华夏成长混合"},
            {"item": "基金类型", "value": "混合型"},
        ]
    )

    with patch(
        "app.datasource.akshare_adapter.ak.fund_individual_basic_info_xq",
        return_value=mock_info_df,
    ) as mock_api:
        await adapter.get_fund_basic("000001.OF")
        mock_api.assert_called_once_with(symbol="000001", timeout=15)


@pytest.mark.asyncio
async def test_get_fund_nav_获取净值历史(akshare_adapter):
    """Verify NAV history is fetched and mapped correctly."""
    adapter, cache = akshare_adapter

    mock_unit_nav = pd.DataFrame(
        {
            "净值日期": ["2026-06-05", "2026-06-04", "2026-06-03"],
            "单位净值": [1.2345, 1.2200, 1.2150],
            "日增长率": [0.0119, 0.0041, -0.0082],
        }
    )
    mock_acc_nav = pd.DataFrame(
        {
            "净值日期": ["2026-06-05", "2026-06-04", "2026-06-03"],
            "累计净值": [4.5678, 4.5200, 4.5100],
        }
    )

    with patch(
        "app.datasource.akshare_adapter.ak.fund_open_fund_info_em",
        side_effect=[mock_unit_nav, mock_acc_nav],
    ) as mock_api:
        result = await adapter.get_fund_nav("000001", days=90)

    assert len(result) == 3
    assert result[0].nav == 1.2345
    assert result[0].acc_nav == 4.5678
    assert result[0].date == "2026-06-05"
    assert result[0].daily_return is not None


@pytest.mark.asyncio
async def test_get_fund_nav_空数据返回空列表(akshare_adapter):
    """Verify empty NAV data returns empty list without error."""
    adapter, cache = akshare_adapter

    empty_df = pd.DataFrame({"净值日期": [], "单位净值": []})

    with patch(
        "app.datasource.akshare_adapter.ak.fund_open_fund_info_em",
        side_effect=[empty_df, empty_df],
    ):
        result = await adapter.get_fund_nav("999999", days=90)

    assert result == []


@pytest.mark.asyncio
async def test_get_fund_manager_获取基金经理信息(akshare_adapter):
    """Verify manager info for a specific fund's manager is fetched."""
    adapter, cache = akshare_adapter

    mock_manager_df = pd.DataFrame(
        {
            "序号": [1, 2],
            "姓名": ["刘睿聪", "郑晓辉"],
            "所属公司": ["华夏基金", "华夏基金"],
            "现任基金代码": ["000001,001924", "000001"],
            "现任基金": ["华夏成长混合,华夏国企改革混合", "华夏成长混合"],
            "累计从业时间": [2000, 5000],
            "现任基金资产总规模": [50.0, 120.0],
            "现任基金最佳回报": [41.44, 150.0],
        }
    )

    with patch(
        "app.datasource.akshare_adapter.ak.fund_manager_em",
        return_value=mock_manager_df,
    ):
        result = await adapter.get_fund_manager("000001")

    assert result.name == "刘睿聪"
    assert result.experience_years is not None


@pytest.mark.asyncio
async def test_get_fund_manager_未找到时抛异常(akshare_adapter):
    """Verify exception is raised when no manager found for the fund."""
    adapter, cache = akshare_adapter

    mock_manager_df = pd.DataFrame(
        {
            "序号": [1],
            "姓名": ["张三"],
            "所属公司": ["其他基金"],
            "现任基金代码": ["999999"],
            "现任基金": ["其他"],
            "累计从业时间": [100],
            "现任基金资产总规模": [1.0],
            "现任基金最佳回报": [5.0],
        }
    )

    with patch(
        "app.datasource.akshare_adapter.ak.fund_manager_em",
        return_value=mock_manager_df,
    ):
        with pytest.raises(ValueError, match="未找到管理基金 000001 的基金经理"):
            await adapter.get_fund_manager("000001")


@pytest.mark.asyncio
async def test_get_fund_portfolio_获取持仓数据(akshare_adapter):
    """Verify portfolio holdings are fetched and mapped."""
    adapter, cache = akshare_adapter

    mock_portfolio = pd.DataFrame(
        {
            "序号": [1, 2],
            "股票代码": ["002025", "300395"],
            "股票名称": ["航天电器", "菲利华"],
            "占净值比例": [5.55, 3.43],
            "持股数": [260.0, 200.01],
            "持仓市值": [14456.15, 8942.29],
            "季度": ["2025年1季度股票投资明细", "2025年1季度股票投资明细"],
        }
    )

    with patch(
        "app.datasource.akshare_adapter.ak.fund_portfolio_hold_em",
        return_value=mock_portfolio,
    ):
        result = await adapter.get_fund_portfolio("000001")

    assert result.fund_code == "000001"
    assert len(result.top_10_stocks) == 2
    assert result.top_10_stocks[0].stock_name == "航天电器"
    assert result.top_10_stocks[0].weight_pct == 5.55
    assert result.report_date != ""


@pytest.mark.asyncio
async def test_get_fund_portfolio_空持仓(akshare_adapter):
    """Verify empty portfolio returns valid structure."""
    adapter, cache = akshare_adapter

    empty_df = pd.DataFrame(
        columns=["序号", "股票代码", "股票名称", "占净值比例", "持股数", "持仓市值", "季度"]
    )

    with patch(
        "app.datasource.akshare_adapter.ak.fund_portfolio_hold_em",
        return_value=empty_df,
    ):
        result = await adapter.get_fund_portfolio("000001")

    assert result.fund_code == "000001"
    assert result.top_10_stocks == []


@pytest.mark.asyncio
async def test_get_macro_shibor(akshare_adapter):
    """Verify Shibor macro data is fetched."""
    adapter, cache = akshare_adapter

    mock_shibor = pd.DataFrame(
        {
            "日期": ["2026-06-05"],
            "O/N-定价": [1.5],
            "1W-定价": [1.8],
        }
    )

    with patch(
        "app.datasource.akshare_adapter.ak.macro_china_shibor_all",
        return_value=mock_shibor,
    ) as mock_api:
        result = await adapter.get_macro("shibor")

    mock_api.assert_called_once()
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_get_macro_cpi(akshare_adapter):
    """Verify CPI macro data is fetched."""
    adapter, cache = akshare_adapter

    mock_cpi = pd.DataFrame({"日期": ["2026-01-01"], "今值": [2.5]})

    with patch(
        "app.datasource.akshare_adapter.ak.macro_china_cpi_yearly",
        return_value=mock_cpi,
    ):
        result = await adapter.get_macro("cpi")

    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_macro_unsupported_indicator(akshare_adapter):
    """Verify unsupported macro indicator raises ValueError."""
    adapter, cache = akshare_adapter

    with pytest.raises(ValueError, match="不支持的宏观指标"):
        await adapter.get_macro("unsupported_indicator")


@pytest.mark.asyncio
async def test_cache_hit_缓存命中时不调API(akshare_adapter):
    """Verify that a cache hit skips the AKShare API call."""
    adapter, cache = akshare_adapter
    cache.get.return_value = {
        "code": "000001",
        "name": "从缓存来的基金",
        "fund_type": "混合型",
        "establish_date": "2001-12-18",
    }

    with patch("app.datasource.akshare_adapter.ak.fund_individual_basic_info_xq") as mock_api:
        result = await adapter.get_fund_basic("000001")

    mock_api.assert_not_called()
    assert result.code == "000001"
    assert result.name == "从缓存来的基金"
