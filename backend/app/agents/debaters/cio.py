from app.agents.base import BaseAgent
from app.agents.prompts.debaters import CIO_PROMPT


class CIODecider(BaseAgent):
    def __init__(self, model: str, base_url: str, api_key: str, **kwargs):
        super().__init__(
            name="首席投资官",
            system_prompt=CIO_PROMPT,
            model=model,
            base_url=base_url,
            api_key=api_key,
            **kwargs,
        )

    async def decide(
        self,
        fund_code: str,
        fund_name: str,
        analyst_reports: dict[str, str],
        debate_record: dict,
        risk_level: str = "moderate",
    ) -> str:
        reports_text = "\n\n---\n\n".join(
            f"### {name}\n{content}" for name, content in analyst_reports.items()
        )
        bull_args = debate_record.get("bull", [])
        bear_args = debate_record.get("bear", [])
        debate_lines = []
        for i, arg in enumerate(bull_args):
            bear_arg = bear_args[i] if i < len(bear_args) else "..."
            debate_lines.append(
                f"**看多方 第{i+1}轮:** {arg}\n\n**看空方 第{i+1}轮:** {bear_arg}"
            )
        debate_text = "\n\n".join(debate_lines)

        prompt = CIO_PROMPT.replace("{risk_level}", risk_level)
        original_prompt = self.system_prompt
        self.system_prompt = prompt

        message = (
            f"## 基金: {fund_name}（{fund_code}）\n"
            f"## 投资者风险偏好: {risk_level}\n\n"
            f"## 分析师报告\n{reports_text}\n\n"
            f"## 辩论记录\n{debate_text}\n\n"
            f"辩论双方已僵持不下。请作为CIO做出最终裁决。"
        )

        result = await self.invoke(message)
        self.system_prompt = original_prompt
        return result
