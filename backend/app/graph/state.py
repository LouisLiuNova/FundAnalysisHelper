from typing import TypedDict


class GraphState(TypedDict, total=False):
    fund_code: str
    risk_level: str
    fund_name: str
    fund_data: dict
    analyst_reports: dict[str, str]
    debate_record: dict
    consensus_reached: bool
    debate_round: int
    cio_verdict: str
    final_report: str
    error: str | None
