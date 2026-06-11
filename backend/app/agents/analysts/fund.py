from app.agents.base import BaseAgent
from app.agents.prompts.analysts import FUNDAMENTAL_PROMPT


class FundamentalAnalyst(BaseAgent):
    def __init__(self, model: str, base_url: str, api_key: str, **kwargs):
        super().__init__(
            name="基本面分析师",
            system_prompt=FUNDAMENTAL_PROMPT,
            model=model,
            base_url=base_url,
            api_key=api_key,
            **kwargs,
        )

    # analyze() removed — analyst_node calls run_with_tools() directly
