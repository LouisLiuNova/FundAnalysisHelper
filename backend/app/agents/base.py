from langchain_core.messages import HumanMessage, SystemMessage
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
