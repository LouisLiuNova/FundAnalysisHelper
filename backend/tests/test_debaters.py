import pytest
from unittest.mock import AsyncMock
from app.agents.debaters.bull import BullDebater
from app.agents.debaters.bear import BearDebater
from app.agents.debaters.cio import CIODecider


@pytest.mark.asyncio
async def test_bull_看多方发表看多观点():
    bull = BullDebater(model="test", base_url="http://x", api_key="k")
    bull._llm = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.content = "我坚定看多，因为基本面强劲..."
    bull._llm.ainvoke = AsyncMock(return_value=mock_resp)

    result = await bull.argue(
        fund_code="000001.OF",
        fund_name="华夏成长混合",
        analyst_reports={"基本面": "基本面良好..."},
        opponent_last="我坚持看空...",
        round_num=1,
    )
    assert "看多" in result


@pytest.mark.asyncio
async def test_bear_看空方发表看空观点():
    bear = BearDebater(model="test", base_url="http://x", api_key="k")
    bear._llm = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.content = "我坚持看空，因为估值过高..."
    bear._llm.ainvoke = AsyncMock(return_value=mock_resp)

    result = await bear.argue(
        fund_code="000001.OF",
        fund_name="华夏成长混合",
        analyst_reports={"基本面": "基本面良好..."},
        opponent_last="我坚定看多...",
        round_num=1,
    )
    assert "看空" in result


@pytest.mark.asyncio
async def test_cio_做出最终裁决():
    cio = CIODecider(model="test", base_url="http://x", api_key="k")
    cio._llm = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.content = "## 核心分歧总结\n\n综合来看，建议谨慎持有..."
    cio._llm.ainvoke = AsyncMock(return_value=mock_resp)

    result = await cio.decide(
        fund_code="000001.OF",
        fund_name="华夏成长混合",
        analyst_reports={"基本面": "..."},
        debate_record={"bull": ["看多..."], "bear": ["看空..."]},
        risk_level="moderate",
    )
    assert len(result) > 0
