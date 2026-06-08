import pytest
from datetime import datetime
from app.models.fund import FundBasicInfo, NAVRecord, ManagerInfo
from app.models.analysis import AnalysisRequest, AnalysisStatus, AnalysisProgress
from app.models.report import Report, ReportSection, DebateRecord, DataSource


class TestFundModels:
    def test_fund_basic_info_字段校验(self):
        info = FundBasicInfo(
            code="000001.OF",
            name="华夏成长混合",
            fund_type="混合型",
            establish_date="2001-08-28",
            management_fee=1.5,
            aum=128_0000_0000.0,
        )
        assert info.code == "000001.OF"
        assert info.aum == 128_0000_0000.0

    def test_nav_record_净值记录校验(self):
        nav = NAVRecord(date="2026-06-05", nav=1.2345, acc_nav=4.5678)
        assert nav.nav == 1.2345


class TestAnalysisModels:
    def test_analysis_request_默认风险偏好(self):
        req = AnalysisRequest(fund_code="000001.OF")
        assert req.risk_level == "moderate"

    def test_analysis_request_自定义风险偏好(self):
        req = AnalysisRequest(fund_code="000001.OF", risk_level="conservative")
        assert req.risk_level == "conservative"

    def test_analysis_progress_百分比计算(self):
        progress = AnalysisProgress(
            analysis_id="abc123",
            status=AnalysisStatus.ANALYZING,
            current_step="基本面分析",
            completed_steps=["数据获取"],
            total_steps=12,
        )
        assert progress.percent == pytest.approx(8.3, abs=0.1)


class TestReportModels:
    def test_report_序列化(self):
        report = Report(
            fund_code="000001.OF",
            fund_name="华夏成长混合",
            timestamp=datetime(2026, 6, 7, 15, 0, 0),
            evidence_level="ESTIMATE",
            sections={
                "summary": ReportSection(title="总结", content="## 总结\n...", order=0),
            },
            debate_record=DebateRecord(
                bull=["看好理由1"],
                bear=["看空理由1"],
                consensus=False,
                rounds=3,
                cio_verdict="综合来看...",
            ),
            data_sources=[DataSource(name="Tushare", endpoint="fund_nav", fetch_time="2026-06-07T15:00:00")],
            model_versions={"analysts": "deepseek-v4-pro[1m]"},
            final_report="# 完整报告\n...",
        )
        d = report.model_dump()
        assert d["fund_code"] == "000001.OF"
        assert d["debate_record"]["consensus"] is False
