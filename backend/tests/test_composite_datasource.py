"""Tests for the composite data source (AKshare + Tushare fallback)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.datasource.composite import CompositeDataSource


@pytest.fixture
def composite():
    """Create CompositeDataSource with mocked AKshare (primary) and Tushare (fallback)."""
    primary = MagicMock()
    primary.get_fund_basic = AsyncMock()
    primary.get_fund_nav = AsyncMock()
    primary.get_fund_manager = AsyncMock()
    primary.get_fund_portfolio = AsyncMock()
    primary.get_macro = AsyncMock()
    primary.get_fund_portfolio_industry_allocation = AsyncMock()
    primary.get_fund_announcements = AsyncMock()
    primary.close = AsyncMock()

    fallback = MagicMock()
    fallback.get_fund_basic = AsyncMock()
    fallback.get_fund_nav = AsyncMock()
    fallback.get_fund_manager = AsyncMock()
    fallback.get_fund_portfolio = AsyncMock()
    fallback.get_macro = AsyncMock()
    fallback.get_fund_portfolio_industry_allocation = AsyncMock()
    fallback.get_fund_announcements = AsyncMock()
    fallback.close = AsyncMock()

    ds = CompositeDataSource(primary=primary, fallback=fallback)
    return ds, primary, fallback


@pytest.mark.asyncio
async def test_get_fund_nav_primary_succeeds(composite):
    """When AKshare returns data, use it and skip fallback."""
    ds, primary, fallback = composite
    from app.models.fund import NAVRecord

    primary.get_fund_nav.return_value = [
        NAVRecord(date="2026-06-05", nav=1.5, acc_nav=3.0),
    ]

    result = await ds.get_fund_nav("000001", days=90)
    assert len(result) == 1
    assert result[0].nav == 1.5
    # Fallback is NOT called.
    fallback.get_fund_nav.assert_not_called()


@pytest.mark.asyncio
async def test_get_fund_nav_primary_empty_falls_back(composite):
    """When AKshare returns empty, fall back to Tushare."""
    ds, primary, fallback = composite
    from app.models.fund import NAVRecord

    primary.get_fund_nav.return_value = []
    fallback.get_fund_nav.return_value = [
        NAVRecord(date="2026-06-05", nav=1.2, acc_nav=2.4),
    ]

    result = await ds.get_fund_nav("000001", days=90)
    assert len(result) == 1
    assert result[0].nav == 1.2


@pytest.mark.asyncio
async def test_get_fund_nav_primary_raises_falls_back(composite):
    """When AKshare raises, silently catch and fall back."""
    ds, primary, fallback = composite
    from app.models.fund import NAVRecord

    primary.get_fund_nav.side_effect = RuntimeError("network error")
    fallback.get_fund_nav.return_value = [
        NAVRecord(date="2026-06-05", nav=1.8, acc_nav=3.6),
    ]

    result = await ds.get_fund_nav("000001", days=90)
    assert len(result) == 1
    assert result[0].nav == 1.8


@pytest.mark.asyncio
async def test_get_fund_nav_all_fail_returns_empty(composite):
    """When both sources fail, return empty list."""
    ds, primary, fallback = composite
    primary.get_fund_nav.side_effect = RuntimeError("fail")
    fallback.get_fund_nav.side_effect = RuntimeError("fail too")

    result = await ds.get_fund_nav("000001", days=90)
    assert result == []


@pytest.mark.asyncio
async def test_get_fund_basic_aks_primary_tushare_enriches(composite):
    """AKshare gets basic info; Tushare fills in missing fee fields."""
    ds, primary, fallback = composite
    from app.models.fund import FundBasicInfo

    primary.get_fund_basic.return_value = FundBasicInfo(
        code="000001",
        name="华夏成长",
        fund_type="混合型",
        establish_date="2001-12-18",
        aum=2.6e9,
    )
    fallback.get_fund_basic.return_value = FundBasicInfo(
        code="000001.OF",
        name="华夏成长混合",
        fund_type="混合型",
        management_fee=1.5,
        custodian_fee=0.25,
        benchmark="沪深300",
    )

    result = await ds.get_fund_basic("000001")
    assert result.code == "000001"
    assert result.name == "华夏成长"  # AKshare name preferred
    assert result.management_fee == 1.5  # enriched from Tushare
    assert result.custodian_fee == 0.25
    assert result.benchmark == "沪深300"


@pytest.mark.asyncio
async def test_get_fund_basic_primary_fails_fallback_succeeds(composite):
    """When AKshare fails, Tushare provides everything."""
    ds, primary, fallback = composite
    from app.models.fund import FundBasicInfo

    primary.get_fund_basic.side_effect = ValueError("not found")
    fallback.get_fund_basic.return_value = FundBasicInfo(
        code="000001.OF",
        name="华夏成长",
        fund_type="混合型",
        management_fee=1.5,
    )

    result = await ds.get_fund_basic("000001")
    assert result.name == "华夏成长"


@pytest.mark.asyncio
async def test_get_fund_basic_all_fail_raises(composite):
    """Both sources fail → ValueError."""
    ds, primary, fallback = composite
    primary.get_fund_basic.side_effect = ValueError("nope")
    fallback.get_fund_basic.side_effect = ValueError("nope too")

    with pytest.raises(ValueError, match="所有数据源均失败"):
        await ds.get_fund_basic("000001")


@pytest.mark.asyncio
async def test_get_fund_manager_merge(composite):
    """AKshare provides basic manager info; Tushare adds education/style."""
    ds, primary, fallback = composite
    from app.models.fund import ManagerInfo

    primary.get_fund_manager.return_value = ManagerInfo(
        id="1", name="刘睿聪", experience_years=5.5, managed_funds=2, total_aum=50.0,
    )
    fallback.get_fund_manager.return_value = ManagerInfo(
        id="mgr1", name="刘睿聪", education="硕士", style="成长型",
    )

    result = await ds.get_fund_manager("000001")
    assert result.name == "刘睿聪"  # AKshare preferred
    assert result.experience_years == 5.5
    assert result.education == "硕士"  # enriched from Tushare
    assert result.style == "成长型"


@pytest.mark.asyncio
async def test_get_fund_manager_both_fail_raises(composite):
    """Both fail → ValueError."""
    ds, primary, fallback = composite
    primary.get_fund_manager.side_effect = ValueError("nope")
    fallback.get_fund_manager.side_effect = ValueError("nope too")

    with pytest.raises(ValueError, match="所有数据源均失败"):
        await ds.get_fund_manager("000001")


@pytest.mark.asyncio
async def test_get_fund_portfolio_prefer_akshare(composite):
    """AKshare has richer holdings → prefer its data."""
    ds, primary, fallback = composite
    from app.models.fund import Portfolio, StockHolding

    primary.get_fund_portfolio.return_value = Portfolio(
        fund_code="000001",
        report_date="2026Q1",
        top_10_stocks=[
            StockHolding(stock_code="002025", stock_name="航天电器", weight_pct=5.5),
            StockHolding(stock_code="300395", stock_name="菲利华", weight_pct=3.4),
        ],
    )
    fallback.get_fund_portfolio.return_value = Portfolio(
        fund_code="000001.OF",
        report_date="2026Q1",
        top_10_stocks=[
            StockHolding(stock_code="002025", stock_name="航天电器", weight_pct=5.0),
        ],
    )

    result = await ds.get_fund_portfolio("000001")
    assert len(result.top_10_stocks) == 2  # AKshare (more holdings)


@pytest.mark.asyncio
async def test_get_fund_portfolio_akshare_empty_fallback_used(composite):
    """AKshare returns empty → fall back to Tushare."""
    ds, primary, fallback = composite
    from app.models.fund import Portfolio, StockHolding

    primary.get_fund_portfolio.return_value = Portfolio(fund_code="000001", report_date="")
    fallback.get_fund_portfolio.return_value = Portfolio(
        fund_code="000001.OF",
        report_date="2026Q1",
        top_10_stocks=[
            StockHolding(stock_code="600519", stock_name="贵州茅台", weight_pct=7.2),
        ],
    )

    result = await ds.get_fund_portfolio("000001")
    assert len(result.top_10_stocks) == 1
    assert result.top_10_stocks[0].stock_name == "贵州茅台"


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_portfolio_industry_allocation_primary_succeeds(composite):
    """When AKshare returns industry allocation data, use it and skip fallback."""
    ds, primary, fallback = composite

    primary.get_fund_portfolio_industry_allocation.return_value = [
        {"行业类别": "制造业", "占净值比例": 35.5},
        {"行业类别": "金融业", "占净值比例": 20.1},
    ]

    result = await ds.get_fund_portfolio_industry_allocation("000001")
    assert len(result) == 2
    assert result[0]["行业类别"] == "制造业"
    assert result[0]["占净值比例"] == 35.5
    fallback.get_fund_portfolio_industry_allocation.assert_not_called()


@pytest.mark.asyncio
async def test_get_portfolio_industry_allocation_primary_fails_fallback(composite):
    """When AKshare raises, fallback returns data."""
    ds, primary, fallback = composite

    primary.get_fund_portfolio_industry_allocation.side_effect = RuntimeError(
        "network error"
    )
    fallback.get_fund_portfolio_industry_allocation.return_value = [
        {"行业类别": "信息技术", "占净值比例": 15.3},
    ]

    result = await ds.get_fund_portfolio_industry_allocation("000001")
    assert len(result) == 1
    assert result[0]["行业类别"] == "信息技术"


@pytest.mark.asyncio
async def test_get_portfolio_industry_allocation_both_fail(composite):
    """When both sources fail, return empty list."""
    ds, primary, fallback = composite

    primary.get_fund_portfolio_industry_allocation.side_effect = RuntimeError("fail")
    fallback.get_fund_portfolio_industry_allocation.side_effect = RuntimeError(
        "fail too"
    )

    result = await ds.get_fund_portfolio_industry_allocation("000001")
    assert result == []


@pytest.mark.asyncio
async def test_get_announcements_primary_succeeds(composite):
    """When AKshare returns announcements, use it and skip fallback."""
    ds, primary, fallback = composite

    primary.get_fund_announcements.return_value = [
        {"报告名称": "2025年年度报告", "报告日期": "2025-03-28"},
    ]

    result = await ds.get_fund_announcements("000001")
    assert len(result) == 1
    assert result[0]["报告名称"] == "2025年年度报告"
    assert result[0]["报告日期"] == "2025-03-28"
    fallback.get_fund_announcements.assert_not_called()


@pytest.mark.asyncio
async def test_get_announcements_primary_fails_fallback(composite):
    """When AKshare raises, fallback returns data."""
    ds, primary, fallback = composite

    primary.get_fund_announcements.side_effect = RuntimeError("network error")
    fallback.get_fund_announcements.return_value = [
        {"报告名称": "2025年第四季度报告", "报告日期": "2025-01-20"},
    ]

    result = await ds.get_fund_announcements("000001")
    assert len(result) == 1
    assert result[0]["报告名称"] == "2025年第四季度报告"


@pytest.mark.asyncio
async def test_get_announcements_both_fail(composite):
    """When both sources fail, return empty list."""
    ds, primary, fallback = composite

    primary.get_fund_announcements.side_effect = RuntimeError("fail")
    fallback.get_fund_announcements.side_effect = RuntimeError("fail too")

    result = await ds.get_fund_announcements("000001")
    assert result == []


async def test_get_macro_primary_then_fallback(composite):
    """AKshare primary for macro, Tushare fallback."""
    ds, primary, fallback = composite

    primary.get_macro.return_value = [{"date": "2026-06-05", "O/N-定价": 1.5}]
    result = await ds.get_macro("shibor")
    assert len(result) == 1
    fallback.get_macro.assert_not_called()

    primary.get_macro.return_value = []
    fallback.get_macro.return_value = [{"date": "2026-06-05"}]
    result = await ds.get_macro("cpi")
    assert len(result) == 1
