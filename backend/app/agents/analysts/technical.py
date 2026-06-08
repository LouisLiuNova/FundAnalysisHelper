from app.agents.base import BaseAgent
from app.agents.prompts.analysts import TECHNICAL_PROMPT


class TechnicalAnalyst(BaseAgent):
    def __init__(self, model: str, base_url: str, api_key: str, **kwargs):
        super().__init__(
            name="技术面分析师",
            system_prompt=TECHNICAL_PROMPT,
            model=model,
            base_url=base_url,
            api_key=api_key,
            **kwargs,
        )

    async def analyze(self, fund_code: str, fund_name: str, data: dict) -> str:
        message = f"请对基金 {fund_name}（{fund_code}）进行技术面分析。"
        return await self.invoke(message, context=data)
