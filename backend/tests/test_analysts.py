import pytest
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
