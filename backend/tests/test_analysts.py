import pytest
from unittest.mock import AsyncMock
from app.agents.analysts.fund import FundamentalAnalyst
from app.agents.analysts.technical import TechnicalAnalyst
from app.agents.analysts.sector import SectorAnalyst
from app.agents.analysts.manager import ManagerAnalyst
from app.agents.analysts.sentiment import SentimentAnalyst
from app.agents.analysts.news import NewsAnalyst
from app.agents.analysts.macro import MacroAnalyst


ANALYST_CLASSES = [
    FundamentalAnalyst, TechnicalAnalyst, SectorAnalyst,
    ManagerAnalyst, SentimentAnalyst, NewsAnalyst, MacroAnalyst,
]


@pytest.mark.parametrize("cls", ANALYST_CLASSES)
def test_分析师有名称(cls):
    agent = cls(model="test", base_url="http://x", api_key="k")
    assert agent.name
    assert len(agent.name) > 0


@pytest.mark.parametrize("cls", ANALYST_CLASSES)
def test_分析师有系统提示词(cls):
    agent = cls(model="test", base_url="http://x", api_key="k")
    assert agent.system_prompt
    assert len(agent.system_prompt) > 100


@pytest.mark.parametrize("cls", ANALYST_CLASSES)
@pytest.mark.asyncio
async def test_分析师analyze返回字符串(cls):
    agent = cls(model="test", base_url="http://x", api_key="k")
    agent._llm = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.content = f"## {cls.__name__} 报告\n\n分析内容..."
    agent._llm.ainvoke = AsyncMock(return_value=mock_resp)

    result = await agent.analyze(
        fund_code="000001.OF",
        fund_name="华夏成长混合",
        data={"nav": [{"date": "2026-06-05", "nav": 1.23}]},
    )
    assert isinstance(result, str)
    assert len(result) > 0


def test_7个分析师名称各不相同():
    agents = [
        cls(model="test", base_url="http://x", api_key="k")
        for cls in ANALYST_CLASSES
    ]
    names = [a.name for a in agents]
    assert len(names) == len(set(names))
