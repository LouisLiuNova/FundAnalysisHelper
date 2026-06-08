import pytest
from unittest.mock import AsyncMock
from app.agents.reporter import Reporter


@pytest.mark.asyncio
async def test_reporter_生成markdown报告():
    reporter = Reporter(model="test", base_url="http://x", api_key="k")
    reporter._llm = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.content = "# 华夏成长混合（000001.OF）投资分析报告\n\n## 一、报告摘要\n\n..."
    reporter._llm.ainvoke = AsyncMock(return_value=mock_resp)

    result = await reporter.write_report(
        fund_code="000001.OF",
        fund_name="华夏成长混合",
        analyst_reports={"基本面": "基本面良好...", "技术面": "技术指标偏多..."},
        debate_record={"bull": ["看多理由..."], "bear": ["看空理由..."]},
        cio_verdict="综合来看，建议谨慎持有...",
        risk_level="moderate",
    )
    assert "华夏成长混合" in result
    assert "#" in result  # Markdown 标题
