import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_full_workflow_端到端全流程验证():
    """模拟完整分析流程：数据获取 → 7分析师 → 辩论 → CIO → 报告"""
    from app.graph.workflow import compile_workflow, set_config, set_datasource
    from app.graph.state import GraphState

    # Mock 配置
    mock_config = MagicMock()
    mock_config.llm.analyst_model = "test-model"
    mock_config.llm.debater_model = "test-model"
    mock_config.llm.report_model = "test-model"
    mock_config.llm.base_url = "https://test.api.com/v1"
    mock_config.llm.api_key = "sk-test"
    set_config(mock_config)

    # Mock 数据源
    mock_ds = MagicMock()
    mock_basic = MagicMock()
    mock_basic.name = "测试基金"
    mock_basic.model_dump.return_value = {"code": "000001.OF", "name": "测试基金"}
    mock_ds.get_fund_basic = AsyncMock(return_value=mock_basic)
    mock_nav = MagicMock()
    mock_nav.model_dump.return_value = {"date": "2026-06-05", "nav": 1.23, "acc_nav": 4.56, "daily_return": 0.01}
    mock_ds.get_fund_nav = AsyncMock(return_value=[mock_nav])
    mock_ds.get_macro = AsyncMock(return_value=[
        {"date": "2026-06-05", "on": 1.5, "1w": 1.8},
    ])
    set_datasource(mock_ds)

    # Mock 所有 LLM 调用
    mock_llm_response = MagicMock()
    mock_llm_response.content = "## 分析报告\n\n这是一个模拟的分析结果。"

    with patch("app.agents.base.ChatOpenAI") as mock_llm_cls:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

        # Mock bind_tools() to return an object whose ainvoke returns
        # a response with no tool_calls (so the ReAct loop exits immediately).
        mock_bound = AsyncMock()
        mock_bound.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_llm.bind_tools = MagicMock(return_value=mock_bound)

        mock_llm_cls.return_value = mock_llm

        graph = compile_workflow()
        initial_state: GraphState = {
            "fund_code": "000001.OF",
            "risk_level": "moderate",
        }
        result = await graph.ainvoke(initial_state)

    # 验证无错误
    assert result.get("error") is None
    assert result["fund_name"] == "测试基金"
    # 验证 7 个分析师都运行了
    assert len(result.get("analyst_reports", {})) == 7
    # 验证辩论发生了
    debate = result["debate_record"]
    assert len(debate.get("bull", [])) > 0
    assert len(debate.get("bear", [])) > 0
    # 验证最终报告
    assert result.get("final_report")
    assert len(result["final_report"]) > 0
