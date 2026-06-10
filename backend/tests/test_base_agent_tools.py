"""Tests for BaseAgent.run_with_tools() — the ReAct tool-calling loop."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from app.agents.base import BaseAgent

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    """Return a BaseAgent whose _llm is replaced with a controllable mock."""
    a = BaseAgent(
        name="test",
        system_prompt="You are a test agent.",
        model="test",
        base_url="http://test",
        api_key="test",
    )
    # We'll set up mock_llm in each test individually
    return a


@tool
async def sample_tool(param: str) -> str:
    """A test tool that echoes its input."""
    return f"Result for {param}"


@tool
async def another_tool(x: int) -> str:
    """Another test tool."""
    return f"Another result: {x * 2}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_with_tools_no_tool_calls_单轮无工具调用():
    """LLM 直接返回最终结果，无 tool_calls，应在单轮结束。"""
    agent = BaseAgent(
        name="test",
        system_prompt="You are a test agent.",
        model="test",
        base_url="http://test",
        api_key="test",
    )

    mock_llm = MagicMock()
    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(
        return_value=AIMessage(content="Final answer without tools")
    )
    mock_llm.bind_tools = MagicMock(return_value=mock_bound)
    agent._llm = mock_llm

    result = await agent.run_with_tools(
        user_message="Analyze fund X",
        tools=[sample_tool],
        max_rounds=3,
    )

    assert "Final answer without tools" in result
    assert mock_bound.ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_run_with_tools_single_tool_call_单工具调用两轮():
    """LLM 先调用一个工具，得到结果后返回最终答案（2 轮）。"""
    agent = BaseAgent(
        name="test",
        system_prompt="You are a test agent.",
        model="test",
        base_url="http://test",
        api_key="test",
    )

    mock_llm = MagicMock()
    mock_bound = MagicMock()

    # Round 1: calls tool; Round 2: final answer
    mock_bound.ainvoke = AsyncMock(side_effect=[
        AIMessage(
            content="",
            tool_calls=[{"name": "sample_tool", "args": {"param": "hello"}, "id": "call_1"}],
        ),
        AIMessage(content="Analysis complete"),
    ])
    mock_llm.bind_tools = MagicMock(return_value=mock_bound)
    agent._llm = mock_llm

    result = await agent.run_with_tools(
        user_message="Analyze fund X",
        tools=[sample_tool],
        max_rounds=3,
    )

    assert "Analysis complete" in result
    assert mock_bound.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_run_with_tools_multiple_tool_calls_多工具一次调用():
    """LLM 一次返回多个 tool_calls，全部执行后返回最终答案。"""
    agent = BaseAgent(
        name="test",
        system_prompt="You are a test agent.",
        model="test",
        base_url="http://test",
        api_key="test",
    )

    mock_llm = MagicMock()
    mock_bound = MagicMock()

    # Round 1: 2 tool_calls at once; Round 2: final answer
    mock_bound.ainvoke = AsyncMock(side_effect=[
        AIMessage(
            content="",
            tool_calls=[
                {"name": "sample_tool", "args": {"param": "hello"}, "id": "call_1"},
                {"name": "another_tool", "args": {"x": 5}, "id": "call_2"},
            ],
        ),
        AIMessage(content="Sector analysis ready"),
    ])
    mock_llm.bind_tools = MagicMock(return_value=mock_bound)
    agent._llm = mock_llm

    result = await agent.run_with_tools(
        user_message="Analyze sectors",
        tools=[sample_tool, another_tool],
        max_rounds=3,
    )

    assert "Sector analysis ready" in result
    assert mock_bound.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_run_with_tools_max_rounds_达到最大轮数停止():
    """LLM 持续返回 tool_calls，max_rounds=2 后停止，返回最后一次内容。"""
    agent = BaseAgent(
        name="test",
        system_prompt="You are a test agent.",
        model="test",
        base_url="http://test",
        api_key="test",
    )

    mock_llm = MagicMock()
    mock_bound = MagicMock()

    # Both rounds return tool_calls — never a final answer
    mock_bound.ainvoke = AsyncMock(
        return_value=AIMessage(
            content="Thinking...",
            tool_calls=[{"name": "sample_tool", "args": {"param": "loop"}, "id": "call_1"}],
        ),
    )
    mock_llm.bind_tools = MagicMock(return_value=mock_bound)
    agent._llm = mock_llm

    result = await agent.run_with_tools(
        user_message="Loop test",
        tools=[sample_tool],
        max_rounds=2,
    )

    # Should return "Thinking..." (the last response content) after 2 rounds
    assert "Thinking..." in result
    assert mock_bound.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_run_with_tools_unknown_tool_name_未知工具优雅处理():
    """LLM 调用了一个不在 tools 列表中的工具，应返回错误 ToolMessage 并继续。"""
    agent = BaseAgent(
        name="test",
        system_prompt="You are a test agent.",
        model="test",
        base_url="http://test",
        api_key="test",
    )

    mock_llm = MagicMock()
    mock_bound = MagicMock()

    # Round 1: calls unknown tool; Round 2: final answer
    mock_bound.ainvoke = AsyncMock(side_effect=[
        AIMessage(
            content="",
            tool_calls=[{"name": "non_existent_tool", "args": {}, "id": "call_bad"}],
        ),
        AIMessage(content="Recovered from error"),
    ])
    mock_llm.bind_tools = MagicMock(return_value=mock_bound)
    agent._llm = mock_llm

    result = await agent.run_with_tools(
        user_message="Test unknown tool",
        tools=[sample_tool],
        max_rounds=3,
    )

    assert "Recovered from error" in result
    assert mock_bound.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_run_with_tools_tool_error_工具执行异常优雅处理():
    """工具执行抛出异常，应返回错误 ToolMessage，继续下一轮。"""
    agent = BaseAgent(
        name="test",
        system_prompt="You are a test agent.",
        model="test",
        base_url="http://test",
        api_key="test",
    )

    mock_llm = MagicMock()
    mock_bound = MagicMock()

    # Round 1: calls crashing_tool; Round 2: final answer
    mock_bound.ainvoke = AsyncMock(side_effect=[
        AIMessage(
            content="",
            tool_calls=[{"name": "crashing_tool", "args": {}, "id": "call_crash"}],
        ),
        AIMessage(content="Recovered from crash"),
    ])
    mock_llm.bind_tools = MagicMock(return_value=mock_bound)
    agent._llm = mock_llm

    # A tool that raises an exception
    @tool
    async def crashing_tool() -> str:
        """This tool always crashes."""
        msg = "Internal error"
        raise RuntimeError(msg)

    result = await agent.run_with_tools(
        user_message="Test crash",
        tools=[crashing_tool],
        max_rounds=3,
    )

    assert "Recovered from crash" in result
    assert mock_bound.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_run_with_tools_with_context_上下文注入():
    """context 字典应被拼接到用户消息中。"""
    agent = BaseAgent(
        name="test",
        system_prompt="You are a test agent.",
        model="test",
        base_url="http://test",
        api_key="test",
    )

    mock_llm = MagicMock()
    mock_bound = MagicMock()

    # Capture the messages passed to ainvoke
    captured_messages = []

    async def capture_ainvoke(messages):
        nonlocal captured_messages
        captured_messages = messages
        return AIMessage(content="Analysis with context")

    mock_bound.ainvoke = AsyncMock(side_effect=capture_ainvoke)
    mock_llm.bind_tools = MagicMock(return_value=mock_bound)
    agent._llm = mock_llm

    result = await agent.run_with_tools(
        user_message="Analyze fund X",
        tools=[sample_tool],
        context={"fund_name": "测试基金", "risk_level": "中等"},
        max_rounds=3,
    )

    assert "Analysis with context" in result
    # The second message (index 1) should be the HumanMessage with context appended
    human_msg = captured_messages[1]
    assert "测试基金" in human_msg.content
    assert "中等" in human_msg.content
    assert "数据上下文" in human_msg.content
