import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd
from app.datasource.tushare import TushareAdapter
from app.datasource.cache import RedisCache


@pytest.fixture
def tushare_adapter():
    with patch("app.datasource.tushare.ts") as mock_ts:
        cache = AsyncMock(spec=RedisCache)
        cache.get.return_value = None  # 默认缓存未命中
        adapter = TushareAdapter(token="test-token", cache=cache)
        adapter._pro = MagicMock()
        yield adapter


@pytest.mark.asyncio
async def test_get_fund_basic_获取基金基本信息(tushare_adapter):
    df = pd.DataFrame([{"ts_code": "000001.OF", "name": "华夏成长混合", "fund_type": "混合型", "found_date": "20010828", "m_fee": 1.5}])
    tushare_adapter._pro.fund_basic.return_value = df
    result = await tushare_adapter.get_fund_basic("000001.OF")
    assert result.code == "000001.OF"
    assert result.name == "华夏成长混合"


@pytest.mark.asyncio
async def test_get_fund_nav_获取净值历史(tushare_adapter):
    df = pd.DataFrame([
        {"nav_date": "20260605", "unit_nav": 1.2345, "accum_nav": 4.5678},
        {"nav_date": "20260604", "unit_nav": 1.2200, "accum_nav": 4.5200},
    ])
    tushare_adapter._pro.fund_nav.return_value = df
    result = await tushare_adapter.get_fund_nav("000001.OF", days=90)
    assert len(result) == 2
    assert result[0].nav == 1.2345


@pytest.mark.asyncio
async def test_cache_hit_缓存命中时不调API(tushare_adapter):
    tushare_adapter._cache.get.return_value = {"code": "000001.OF", "name": "华夏成长混合", "fund_type": "混合型"}
    result = await tushare_adapter.get_fund_basic("000001.OF")
    tushare_adapter._pro.fund_basic.assert_not_called()
    assert result.code == "000001.OF"


@pytest.mark.asyncio
async def test_get_macro_获取宏观数据(tushare_adapter):
    df = pd.DataFrame([{"date": "20260605", "on": 1.5, "1w": 1.8}])
    mock_shibor = MagicMock()
    mock_shibor.to_json.return_value = df.to_json(orient="records")
    tushare_adapter._pro.shibor.return_value = mock_shibor
    result = await tushare_adapter.get_macro("shibor")
    assert len(result) == 1
    assert result[0]["on"] == 1.5
