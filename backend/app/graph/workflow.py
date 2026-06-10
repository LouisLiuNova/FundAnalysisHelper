from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from app.graph.state import GraphState

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from app.core.config import Config
    from app.datasource.base import BaseDataSource

ANALYST_NAMES = [
    "fundamental",
    "technical",
    "sector",
    "manager",
    "sentiment",
    "news",
    "macro",
]


async def fetch_data_node(state: GraphState) -> dict:
    ds = get_datasource()
    code = state["fund_code"]

    try:
        basic = await ds.get_fund_basic(code)
        nav = await ds.get_fund_nav(code, days=90)
        macro = await ds.get_macro("shibor")
    except Exception as e:
        return {"error": str(e)}

    return {
        "fund_name": basic.name,
        "fund_data": {
            "basic": basic.model_dump(),
            "nav": [n.model_dump() for n in nav],
            "macro": macro,
        },
    }


async def analyst_node(state: GraphState, analyst_type: str) -> dict:
    from app.agents.analysts.fund import FundamentalAnalyst
    from app.agents.analysts.macro import MacroAnalyst
    from app.agents.analysts.manager import ManagerAnalyst
    from app.agents.analysts.news import NewsAnalyst
    from app.agents.analysts.sector import SectorAnalyst
    from app.agents.analysts.sentiment import SentimentAnalyst
    from app.agents.analysts.technical import TechnicalAnalyst
    from app.agents.tools import get_tools_for_agent

    config = get_config()
    classes = {
        "fundamental": FundamentalAnalyst,
        "technical": TechnicalAnalyst,
        "sector": SectorAnalyst,
        "manager": ManagerAnalyst,
        "sentiment": SentimentAnalyst,
        "news": NewsAnalyst,
        "macro": MacroAnalyst,
    }

    agent = classes[analyst_type](
        model=config.llm.analyst_model,
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
    )

    fund_name = state.get("fund_name", "")
    fund_code = state["fund_code"]
    message = f"请对基金 {fund_name}（{fund_code}）进行{analyst_type}分析。"

    tools = get_tools_for_agent(analyst_type)
    result = await agent.run_with_tools(
        user_message=message,
        tools=tools,
        context=state.get("fund_data", {}),
        max_rounds=3,
    )
    return {"analyst_reports": {analyst_type: result}}


async def bull_node(state: GraphState) -> dict:
    from app.agents.debaters.bull import BullDebater

    config = get_config()
    bull = BullDebater(
        model=config.llm.debater_model,
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
    )
    debate = state.get("debate_record", {})
    bull_history = list(debate.get("bull", []))
    bear_history = list(debate.get("bear", []))
    round_num = state.get("debate_round", 0) + 1
    opponent_last = bear_history[-1] if bear_history else None

    argument = await bull.argue(
        fund_code=state["fund_code"],
        fund_name=state.get("fund_name", ""),
        analyst_reports=state.get("analyst_reports", {}),
        opponent_last=opponent_last,
        round_num=round_num,
    )
    bull_history.append(argument)

    consensus = False
    if bear_history and round_num > 1 and ("同意" in argument or "认可" in argument):
        consensus = True

    return {
        "debate_record": {"bull": bull_history, "bear": bear_history},
        "debate_round": round_num,
        "consensus_reached": consensus,
    }


async def bear_node(state: GraphState) -> dict:
    from app.agents.debaters.bear import BearDebater

    config = get_config()
    bear = BearDebater(
        model=config.llm.debater_model,
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
    )
    debate = state.get("debate_record", {})
    bull_history = list(debate.get("bull", []))
    bear_history = list(debate.get("bear", []))
    opponent_last = bull_history[-1] if bull_history else None

    argument = await bear.argue(
        fund_code=state["fund_code"],
        fund_name=state.get("fund_name", ""),
        analyst_reports=state.get("analyst_reports", {}),
        opponent_last=opponent_last,
        round_num=state.get("debate_round", 0),
    )
    bear_history.append(argument)

    return {
        "debate_record": {"bull": bull_history, "bear": bear_history},
    }


async def cio_node(state: GraphState) -> dict:
    from app.agents.debaters.cio import CIODecider

    config = get_config()
    cio = CIODecider(
        model=config.llm.debater_model,
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
    )
    verdict = await cio.decide(
        fund_code=state["fund_code"],
        fund_name=state.get("fund_name", ""),
        analyst_reports=state.get("analyst_reports", {}),
        debate_record=state.get("debate_record", {}),
        risk_level=state.get("risk_level", "moderate"),
    )
    return {"cio_verdict": verdict}


async def reporter_node(state: GraphState) -> dict:
    from app.agents.reporter import Reporter

    config = get_config()
    reporter = Reporter(
        model=config.llm.report_model,
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
    )
    report = await reporter.write_report(
        fund_code=state["fund_code"],
        fund_name=state.get("fund_name", ""),
        analyst_reports=state.get("analyst_reports", {}),
        debate_record=state.get("debate_record", {}),
        cio_verdict=state.get("cio_verdict"),
        risk_level=state.get("risk_level", "moderate"),
    )
    return {"final_report": report}


def should_continue_debate(state: GraphState) -> str:
    if state.get("consensus_reached", False):
        return "cio"
    if state.get("debate_round", 0) >= 3:
        return "cio"
    return "debate"


def compile_workflow() -> CompiledStateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("fetch_data", fetch_data_node)
    builder.add_node("bull", bull_node)
    builder.add_node("bear", bear_node)
    builder.add_node("cio", cio_node)
    builder.add_node("reporter", reporter_node)

    for name in ANALYST_NAMES:

        async def make_analyst(state: GraphState, name: str = name) -> dict:
            return await analyst_node(state, name)

        builder.add_node(f"analyst_{name}", make_analyst)

    builder.add_edge(START, "fetch_data")

    for name in ANALYST_NAMES:
        builder.add_edge("fetch_data", f"analyst_{name}")

    for name in ANALYST_NAMES:
        builder.add_edge(f"analyst_{name}", "bull")

    builder.add_edge("bull", "bear")

    builder.add_conditional_edges(
        "bear",
        should_continue_debate,
        {"debate": "bull", "cio": "cio"},
    )

    builder.add_edge("cio", "reporter")
    builder.add_edge("reporter", END)

    return builder.compile()


# Module-level dependency injection
_config = None
_datasource = None


def set_config(config: Config) -> None:
    global _config
    _config = config


def get_config() -> Config:
    global _config
    if _config is None:
        from app.core.config import load_config

        _config = load_config()
    return _config


def set_datasource(ds: BaseDataSource) -> None:
    global _datasource
    _datasource = ds


def get_datasource() -> BaseDataSource:
    global _datasource
    if _datasource is None:
        raise RuntimeError("Datasource not initialized. Call set_datasource() first.")
    return _datasource
