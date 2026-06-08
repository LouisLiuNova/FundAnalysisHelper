from typing import Annotated, TypedDict


def _merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}


class GraphState(TypedDict, total=False):
    fund_code: str
    risk_level: str
    fund_name: str
    fund_data: dict
    analyst_reports: Annotated[dict[str, str], _merge_dicts]
    debate_record: dict
    consensus_reached: bool
    debate_round: int
    cio_verdict: str
    final_report: str
    error: str | None
