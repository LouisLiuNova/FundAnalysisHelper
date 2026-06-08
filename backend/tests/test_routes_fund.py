import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def mock_datasource():
    with patch("app.api.routes.fund.get_datasource") as mock_fn:
        mock_ds = MagicMock()
        mock_fn.return_value = mock_ds
        yield mock_ds


@pytest.mark.asyncio
async def test_fund_search_返回搜索结果(mock_datasource):
    mock_datasource.get_fund_basic = AsyncMock(return_value=MagicMock(
        code="000001.OF",
        name="华夏成长混合",
        fund_type="混合型",
        establish_date="2001-08-28",
    ))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/funds/search?q=000001")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["code"] == "000001.OF"


@pytest.mark.asyncio
async def test_fund_search_空查询返回空列表(mock_datasource):
    mock_datasource.get_fund_basic = AsyncMock(side_effect=Exception("not found"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/funds/search?q=xyz")
    assert response.status_code == 200
    assert response.json() == []
