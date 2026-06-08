import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.analysis import AnalysisProgress, AnalysisStatus
from app.models.report import Report


@pytest.fixture
def mock_service():
    with patch("app.api.routes.analysis.get_analysis_service") as mock_fn:
        mock_svc = MagicMock()
        mock_svc.start_analysis = AsyncMock(return_value="abc12345")
        mock_svc.get_status = AsyncMock(return_value=AnalysisProgress(
            analysis_id="abc12345",
            status=AnalysisStatus.COMPLETED,
            current_step="完成",
            completed_steps=["数据获取"],
            total_steps=12,
        ))
        mock_svc.get_report = AsyncMock(return_value=Report(
            analysis_id="abc12345",
            fund_code="000001.OF",
            fund_name="测试基金",
            final_report="# 报告\n内容...",
        ))
        mock_fn.return_value = mock_svc
        yield mock_svc


@pytest.mark.asyncio
async def test_post_analysis_返回202(mock_service):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/analysis",
            json={"fund_code": "000001.OF", "risk_level": "moderate"},
        )
    assert response.status_code == 202
    data = response.json()
    assert data["analysis_id"] == "abc12345"


@pytest.mark.asyncio
async def test_get_analysis_status_返回进度(mock_service):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analysis/abc12345/status")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_get_analysis_report_返回报告(mock_service):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analysis/abc12345")
    assert response.status_code == 200
    assert response.json()["final_report"] == "# 报告\n内容..."


@pytest.mark.asyncio
async def test_get_analysis_not_found_返回404(mock_service):
    mock_service.get_report = AsyncMock(return_value=None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/analysis/nonexistent")
    assert response.status_code == 404
