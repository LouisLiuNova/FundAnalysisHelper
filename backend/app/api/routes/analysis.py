from fastapi import APIRouter, HTTPException

from app.api.deps import get_analysis_service
from app.models.analysis import (
    AnalysisProgress,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
)
from app.models.report import Report

router = APIRouter(prefix="/api/v1/analysis", tags=["分析"])


@router.post("", status_code=202, response_model=AnalysisResponse)
async def start_analysis(request: AnalysisRequest) -> AnalysisResponse:
    service = get_analysis_service()
    analysis_id = await service.start_analysis(request)
    return AnalysisResponse(
        analysis_id=analysis_id,
        status=AnalysisStatus.PENDING,
    )


@router.get("/{analysis_id}/status")
async def get_analysis_status(analysis_id: str) -> AnalysisProgress:
    service = get_analysis_service()
    progress = await service.get_status(analysis_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="分析任务未找到")
    return progress


@router.get("/{analysis_id}")
async def get_analysis_report(analysis_id: str) -> Report:
    service = get_analysis_service()
    report = await service.get_report(analysis_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告未找到")
    return report
