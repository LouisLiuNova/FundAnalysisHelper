from app.agents.base import BaseAgent
from app.agents.prompts.debaters import BEAR_PROMPT


class BearDebater(BaseAgent):
    def __init__(self, model: str, base_url: str, api_key: str, **kwargs):
        super().__init__(
            name="看空方辩论代表",
            system_prompt=BEAR_PROMPT,
            model=model,
            base_url=base_url,
            api_key=api_key,
            **kwargs,
        )

    async def argue(
        self,
        fund_code: str,
        fund_name: str,
        analyst_reports: dict[str, str],
        opponent_last: str | None = None,
        round_num: int = 1,
    ) -> str:
        reports_text = "\n\n---\n\n".join(
            f"### {name}\n{content}" for name, content in analyst_reports.items()
        )
        message = (
            f"## 基金: {fund_name}（{fund_code}）\n"
            f"## 辩论第 {round_num} 轮\n\n"
            f"## 分析师报告\n{reports_text}\n\n"
        )
        if opponent_last:
            message += f"## 对方（看多方）上一轮观点\n{opponent_last}\n\n"
            message += "请针对对方的观点进行反驳，并重申你的看空立场。"
        else:
            message += "请发表你的开场看空观点。"
        return await self.invoke(message)
