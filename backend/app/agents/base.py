from collections.abc import Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI


class BaseAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str,
        base_url: str,
        api_key: str,
        temperature: float = 0.3,
        max_tokens: int = 16384,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self._llm = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def invoke(self, user_message: str, context: dict | None = None) -> str:
        messages: list[SystemMessage | HumanMessage] = [SystemMessage(content=self.system_prompt)]

        if context:
            ctx_str = "\n\n## 数据上下文\n" + "\n".join(f"- {k}: {v}" for k, v in context.items())
            user_message = user_message + ctx_str

        messages.append(HumanMessage(content=user_message))
        response = await self._llm.ainvoke(messages)
        return response.content

    async def run_with_tools(
        self,
        user_message: str,
        tools: list[Callable],
        context: dict | None = None,
        max_rounds: int = 3,
    ) -> str:
        """Run a ReAct tool-calling loop.

        The LLM iteratively decides whether to call tools or produce a final
        answer. The loop terminates when the LLM returns a response without
        ``tool_calls`` or when *max_rounds* is reached.

        Args:
            user_message: The user's input message.
            tools: List of LangChain ``@tool``-decorated functions.
            context: Optional data context appended to the user message.
            max_rounds: Maximum tool-calling iterations (default 3).

        Returns:
            The final response content from the LLM.
        """
        messages: list[SystemMessage | HumanMessage | AIMessage | ToolMessage] = [
            SystemMessage(content=self.system_prompt),
        ]

        if context:
            ctx_str = "\n\n## 数据上下文\n" + "\n".join(f"- {k}: {v}" for k, v in context.items())
            user_message = user_message + ctx_str

        messages.append(HumanMessage(content=user_message))

        llm_with_tools = self._llm.bind_tools(tools)
        tool_map = {t.name: t for t in tools}

        for _round in range(max_rounds):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            if not response.tool_calls:
                return response.content

            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_fn = tool_map.get(tool_call["name"])
                if tool_fn is None:
                    messages.append(
                        ToolMessage(
                            content=f"Error: unknown tool '{tool_call['name']}'",
                            tool_call_id=tool_call["id"],
                        )
                    )
                    continue
                result = await tool_fn.ainvoke(tool_call["args"])
                messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )

        # max_rounds reached without a final answer — return the last response
        return response.content
