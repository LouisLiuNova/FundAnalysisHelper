import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.graph.workflow import (
    fetch_data_node,
    should_continue_debate,
    compile_workflow,
)
from app.graph.state import GraphState


@pytest.mark.asyncio
async def test_fetch_data_node_设置基金名称和数据():
    with patch("app.graph.workflow.get_datasource") as mock_ds:
        mock_basic = MagicMock()
        mock_basic.name = "测试基金"
        mock_basic.model_dump.return_value = {"code": "000001.OF", "name": "测试基金"}
        mock_ds.return_value.get_fund_basic = AsyncMock(return_value=mock_basic)

        mock_nav = MagicMock()
        mock_nav.model_dump.return_value = {"date": "2026-06-05", "nav": 1.23, "acc_nav": 4.56}
        mock_ds.return_value.get_fund_nav = AsyncMock(return_value=[mock_nav])
        mock_ds.return_value.get_macro = AsyncMock(return_value=[
            {"date": "2026-06-05", "on": 1.5}
        ])

        state: GraphState = {"fund_code": "000001.OF", "risk_level": "moderate"}
        result = await fetch_data_node(state)
        assert result["fund_name"] == "测试基金"
        assert "nav" in result["fund_data"]


def test_should_continue_debate_达成共识时进cio():
    state: GraphState = {
        "fund_code": "000001.OF",
        "consensus_reached": True,
        "debate_round": 2,
    }
    assert should_continue_debate(state) == "cio"


def test_should_continue_debate_满3轮进cio():
    state: GraphState = {
        "fund_code": "000001.OF",
        "consensus_reached": False,
        "debate_round": 3,
    }
    assert should_continue_debate(state) == "cio"


def test_should_continue_debate_继续辩论():
    state: GraphState = {
        "fund_code": "000001.OF",
        "consensus_reached": False,
        "debate_round": 1,
    }
    assert should_continue_debate(state) == "debate"


def test_compile_workflow_返回编译后的图():
    graph = compile_workflow()
    assert graph is not None
    assert hasattr(graph, "ainvoke")
