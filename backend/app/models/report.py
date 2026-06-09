from datetime import datetime

from pydantic import BaseModel, Field


class ReportSection(BaseModel):
    title: str
    content: str
    order: int


class DebateRecord(BaseModel):
    bull: list[str] = Field(default_factory=list)
    bear: list[str] = Field(default_factory=list)
    consensus: bool = False
    rounds: int = 0
    cio_verdict: str | None = None


class DataSource(BaseModel):
    name: str
    endpoint: str
    fetch_time: str


class Report(BaseModel):
    analysis_id: str = ""
    fund_code: str
    fund_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    evidence_level: str = "ESTIMATE"
    sections: dict[str, ReportSection] = Field(default_factory=dict)
    debate_record: DebateRecord = Field(default_factory=DebateRecord)
    data_sources: list[DataSource] = Field(default_factory=list)
    model_versions: dict[str, str] = Field(default_factory=dict)
    final_report: str = ""
