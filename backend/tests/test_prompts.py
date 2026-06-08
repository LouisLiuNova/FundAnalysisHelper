from app.agents.prompts.analysts import (
    FUNDAMENTAL_PROMPT, TECHNICAL_PROMPT, SECTOR_PROMPT,
    MANAGER_PROMPT, SENTIMENT_PROMPT, NEWS_PROMPT, MACRO_PROMPT,
)
from app.agents.prompts.debaters import BULL_PROMPT, BEAR_PROMPT, CIO_PROMPT
from app.agents.prompts.reporter import REPORTER_PROMPT


def test_基本面提示词包含角色定义():
    assert "基本面分析师" in FUNDAMENTAL_PROMPT
    assert len(FUNDAMENTAL_PROMPT) > 200


def test_全部7个分析师提示词都存在():
    prompts = [
        FUNDAMENTAL_PROMPT, TECHNICAL_PROMPT, SECTOR_PROMPT,
        MANAGER_PROMPT, SENTIMENT_PROMPT, NEWS_PROMPT, MACRO_PROMPT,
    ]
    for p in prompts:
        assert isinstance(p, str)
        assert len(p) > 100


def test_看多看空提示词内容不同():
    assert BULL_PROMPT != BEAR_PROMPT
    assert "看多" in BULL_PROMPT
    assert "看空" in BEAR_PROMPT


def test_cio提示词包含裁决指引():
    assert "裁决" in CIO_PROMPT or "破局" in CIO_PROMPT
    assert len(CIO_PROMPT) > 200


def test_报告编写提示词包含结构要求():
    assert "报告" in REPORTER_PROMPT or "Markdown" in REPORTER_PROMPT
    assert len(REPORTER_PROMPT) > 200
