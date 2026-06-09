from app.agents.base import BaseAgent
from app.agents.prompts.reporter import REPORTER_PROMPT


class Reporter(BaseAgent):
    def __init__(self, model: str, base_url: str, api_key: str, **kwargs):
        super().__init__(
            name="报告编写师",
            system_prompt=REPORTER_PROMPT,
            model=model,
            base_url=base_url,
            api_key=api_key,
            **kwargs,
        )

    async def write_report(
        self,
        fund_code: str,
        fund_name: str,
        analyst_reports: dict[str, str],
        debate_record: dict,
        cio_verdict: str | None,
        risk_level: str,
    ) -> str:
        reports_text = "\n\n---\n\n".join(
            f"### {name} 分析报告\n{content}" for name, content in analyst_reports.items()
        )
        bull_args = debate_record.get("bull", [])
        bear_args = debate_record.get("bear", [])

        debate_parts = []
        for i, (b, br) in enumerate(zip(bull_args, bear_args, strict=False)):
            debate_parts.append(f"**第{i + 1}轮:**\n- 看多: {b}\n- 看空: {br}")
        if len(bull_args) > len(bear_args):
            for i in range(len(bear_args), len(bull_args)):
                debate_parts.append(f"**第{i + 1}轮 看多:** {bull_args[i]}")
        debate_text = "\n\n".join(debate_parts)

        prompt = REPORTER_PROMPT.replace("{fund_name}", fund_name)
        prompt = prompt.replace("{fund_code}", fund_code)
        prompt = prompt.replace("{risk_level}", risk_level)

        original_prompt = self.system_prompt
        self.system_prompt = prompt

        message = (
            f"请基于以下内容编写 {fund_name}（{fund_code}）的完整投资分析报告。\n\n"
            f"## 投资者风险偏好: {risk_level}\n\n"
            f"## 分析师报告\n{reports_text}\n\n"
            f"## 辩论记录\n{debate_text}\n\n"
            f"## CIO裁决\n{cio_verdict or '未达成裁决'}\n\n"
            f"请严格按照报告结构模板编写完整的 Markdown 报告。"
        )

        result = await self.invoke(message)
        self.system_prompt = original_prompt
        return result
