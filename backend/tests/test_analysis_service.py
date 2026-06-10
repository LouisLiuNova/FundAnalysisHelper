import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.models.analysis import AnalysisRequest, AnalysisStatus
from app.services.analysis import AnalysisService


@pytest.fixture
def analysis_service():
    with patch("app.services.analysis.init_db"), \
         patch("app.services.analysis.RedisCache"), \
         patch("app.services.analysis.create_datasource"), \
         patch("app.services.analysis.set_datasource"):
        service = AnalysisService(
            mongodb_uri="mongodb://localhost:27017",
            db_name="fund_analysis",
            redis_host="localhost",
            redis_port=6379,
            tushare_token="test-token",
            datasource_type="composite",
        )
        service._db = AsyncMock()
        mock_coll = AsyncMock()
        service._db.__getitem__ = MagicMock(return_value=mock_coll)
        service._initialized = True
        yield service, mock_coll


@pytest.mark.asyncio
async def test_start_analysis_返回分析ID(analysis_service):
    service, mock_coll = analysis_service
    mock_coll.insert_one = AsyncMock()

    request = AnalysisRequest(fund_code="000001.OF", risk_level="moderate")
    analysis_id = await service.start_analysis(request)
    assert analysis_id
    assert len(analysis_id) > 0


@pytest.mark.asyncio
async def test_get_status_返回进度对象(analysis_service):
    service, mock_coll = analysis_service
    mock_coll.find_one = AsyncMock(return_value={
        "analysis_id": "abc123",
        "status": "analyzing",
        "current_step": "基本面分析",
        "completed_steps": ["数据获取"],
        "total_steps": 12,
        "error": None,
    })

    progress = await service.get_status("abc123")
    assert progress.analysis_id == "abc123"
    assert progress.status == AnalysisStatus.ANALYZING


@pytest.mark.asyncio
async def test_get_report_未找到时返回None(analysis_service):
    service, mock_coll = analysis_service
    mock_coll.find_one = AsyncMock(return_value=None)

    report = await service.get_report("nonexistent")
    assert report is None
