import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.base import BaseAgent


@pytest.fixture
def base_agent():
    with patch("app.agents.base.ChatOpenAI") as mock_llm_cls:
        mock_llm = AsyncMock()
        mock_llm_cls.return_value = mock_llm
        agent = BaseAgent(
            name="测试Agent",
            system_prompt="你是一个测试助手。",
            model="test-model",
            base_url="https://test.api.com/v1",
            api_key="sk-test",
        )
        yield agent, mock_llm


@pytest.mark.asyncio
async def test_base_agent_invoke_发送系统提示词和用户消息(base_agent):
    agent, mock_llm = base_agent
    mock_response = MagicMock()
    mock_response.content = "测试回复"
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await agent.invoke("分析这只基金。")

    call_args = mock_llm.ainvoke.call_args[0][0]
    assert len(call_args) == 2
    assert isinstance(call_args[0], SystemMessage)
    assert call_args[0].content == "你是一个测试助手。"
    assert isinstance(call_args[1], HumanMessage)
    assert result == "测试回复"


@pytest.mark.asyncio
async def test_base_agent_invoke_带上下文注入(base_agent):
    agent, mock_llm = base_agent
    mock_response = MagicMock()
    mock_response.content = "带上下文的回复"
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await agent.invoke("分析", context={"fund_name": "测试基金"})

    call_args = mock_llm.ainvoke.call_args[0][0]
    human_msg = call_args[1].content
    assert "测试基金" in human_msg
