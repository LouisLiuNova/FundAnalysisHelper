from enum import StrEnum
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    FETCHING_DATA = "fetching_data"
    ANALYZING = "analyzing"
    DEBATING = "debating"
    WRITING_REPORT = "writing_report"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRequest(BaseModel):
    fund_code: str = Field(description="基金代码，如 000001.OF")
    risk_level: RiskLevel = RiskLevel.MODERATE


class AnalysisProgress(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    current_step: str
    completed_steps: list[str] = Field(default_factory=list)
    total_steps: int = 12
    error: str | None = None

    @property
    def percent(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return round(len(self.completed_steps) / self.total_steps * 100, 1)


class AnalysisResponse(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
