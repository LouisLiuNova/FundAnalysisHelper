import asyncio
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.datasource.cache import RedisCache
from app.datasource.tushare import TushareAdapter
from app.db.client import init_db
from app.graph.workflow import compile_workflow, set_datasource
from app.models.analysis import AnalysisProgress, AnalysisRequest, AnalysisStatus
from app.models.report import DebateRecord, Report, ReportSection

if TYPE_CHECKING:
    from app.graph.state import GraphState


class AnalysisService:
    def __init__(
        self,
        mongodb_uri: str,
        db_name: str,
        redis_host: str,
        redis_port: int,
        tushare_token: str,
    ):
        self._mongodb_uri = mongodb_uri
        self._db_name = db_name
        self._redis_host = redis_host
        self._redis_port = redis_port
        self._tushare_token = tushare_token
        self._initialized = False
        self._db = None
        self._cache = None
        self._datasource = None

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._db = await init_db(self._mongodb_uri, self._db_name)
        self._cache = RedisCache(host=self._redis_host, port=self._redis_port)
        self._datasource = TushareAdapter(token=self._tushare_token, cache=self._cache)
        set_datasource(self._datasource)
        self._initialized = True

    def _reports_col(self) -> object:
        return self._db["fund_analysis_reports"]

    def _logs_col(self) -> object:
        return self._db["analysis_logs"]

    async def start_analysis(self, request: AnalysisRequest) -> str:
        await self._ensure_initialized()
        analysis_id = str(uuid.uuid4())[:8]

        await self._logs_col().insert_one(
            {
                "analysis_id": analysis_id,
                "status": AnalysisStatus.PENDING.value,
                "current_step": "",
                "completed_steps": [],
                "total_steps": 12,
                "error": None,
                "created_at": datetime.now(UTC),
            }
        )

        asyncio.create_task(self._run_analysis(analysis_id, request))
        return analysis_id

    async def _run_analysis(self, analysis_id: str, request: AnalysisRequest) -> None:
        try:
            await self._update_status(analysis_id, AnalysisStatus.FETCHING_DATA, "数据获取", [])
            graph = compile_workflow()

            initial_state: GraphState = {
                "fund_code": request.fund_code,
                "risk_level": request.risk_level.value,
            }
            result = await graph.ainvoke(initial_state)

            if result.get("error"):
                await self._update_status(
                    analysis_id,
                    AnalysisStatus.FAILED,
                    "",
                    [],
                    error=result["error"],
                )
                return

            await self._update_status(
                analysis_id,
                AnalysisStatus.WRITING_REPORT,
                "报告编写",
                [
                    "数据获取",
                    "基本面分析",
                    "技术面分析",
                    "行业分析",
                    "经理分析",
                    "情绪分析",
                    "新闻分析",
                    "宏观分析",
                    "辩论",
                    "CIO裁决",
                ],
            )

            debate = result.get("debate_record", {})
            report = Report(
                fund_code=request.fund_code,
                fund_name=result.get("fund_name", ""),
                timestamp=datetime.now(UTC),
                sections={
                    name: ReportSection(title=name, content=content, order=i)
                    for i, (name, content) in enumerate(result.get("analyst_reports", {}).items())
                },
                debate_record=DebateRecord(
                    bull=debate.get("bull", []),
                    bear=debate.get("bear", []),
                    consensus=result.get("consensus_reached", False),
                    rounds=result.get("debate_round", 0),
                    cio_verdict=result.get("cio_verdict"),
                ),
                final_report=result.get("final_report", ""),
            )

            await self._reports_col().insert_one(report.model_dump())

            await self._update_status(
                analysis_id,
                AnalysisStatus.COMPLETED,
                "完成",
                [
                    "数据获取",
                    "基本面分析",
                    "技术面分析",
                    "行业分析",
                    "经理分析",
                    "情绪分析",
                    "新闻分析",
                    "宏观分析",
                    "辩论",
                    "CIO裁决",
                    "报告编写",
                ],
            )
        except Exception as e:
            await self._update_status(analysis_id, AnalysisStatus.FAILED, "", [], error=str(e))

    async def _update_status(
        self,
        analysis_id: str,
        status: AnalysisStatus,
        current_step: str,
        completed_steps: list[str],
        error: str | None = None,
    ) -> None:
        await self._logs_col().update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": status.value,
                    "current_step": current_step,
                    "completed_steps": completed_steps,
                    "error": error,
                }
            },
            upsert=True,
        )

    async def get_status(self, analysis_id: str) -> AnalysisProgress | None:
        await self._ensure_initialized()
        doc = await self._logs_col().find_one({"analysis_id": analysis_id})
        if not doc:
            return None
        return AnalysisProgress(
            analysis_id=doc["analysis_id"],
            status=AnalysisStatus(doc["status"]),
            current_step=doc.get("current_step", ""),
            completed_steps=doc.get("completed_steps", []),
            total_steps=doc.get("total_steps", 12),
            error=doc.get("error"),
        )

    async def get_report(self, analysis_id: str) -> Report | None:
        await self._ensure_initialized()
        doc = await self._reports_col().find_one({"analysis_id": analysis_id})
        if not doc:
            return None
        return Report(**doc)
