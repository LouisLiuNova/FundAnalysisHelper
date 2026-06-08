from app.graph.state import GraphState


def test_graph_state_默认值():
    state = GraphState(fund_code="000001.OF", risk_level="moderate")
    assert state["fund_code"] == "000001.OF"
    assert state["risk_level"] == "moderate"
    assert state.get("error") is None


def test_graph_state_包含全部字段():
    expected_keys = {
        "fund_code", "risk_level", "fund_name", "fund_data",
        "analyst_reports", "debate_record", "consensus_reached",
        "debate_round", "cio_verdict", "final_report", "error",
    }
    assert set(GraphState.__annotations__.keys()) == expected_keys
