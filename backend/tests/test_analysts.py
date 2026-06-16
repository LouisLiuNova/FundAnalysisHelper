import pytest
from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage

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


def test_7个分析师名称各不相同():
    agents = [
        cls(model="test", base_url="http://x", api_key="k")
        for cls in ANALYST_CLASSES
    ]
    names = [a.name for a in agents]
    assert len(names) == len(set(names))


@pytest.mark.asyncio
@pytest.mark.parametrize("cls", ANALYST_CLASSES)
async def test_分析师run_with_tools返回字符串(cls):
    """每个分析师子类调用 run_with_tools() 应返回非空字符串。"""
    agent = cls(model="test", base_url="http://x", api_key="k")

    mock_llm = MagicMock()
    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(
        return_value=AIMessage(content="模拟分析结果")
    )
    mock_llm.bind_tools = MagicMock(return_value=mock_bound)
    agent._llm = mock_llm

    result = await agent.run_with_tools(
        user_message="分析基金 000001",
        tools=[],
        max_rounds=3,
    )

    assert isinstance(result, str)
    assert len(result) > 0
