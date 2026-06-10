"""Composite data source that combines AKshare (primary) + Tushare (fallback).

Strategy per method:

* **get_fund_basic** — AKshare primary (free, good coverage); Tushare fallback for
  fields AKshare doesn't provide (fee rates).
* **get_fund_nav** — AKshare primary; Tushare fallback.
* **get_fund_manager** — Try both in parallel; merge results (AKshare for name/tenure,
  Tushare for education/style when available).
* **get_fund_portfolio** — Try both; prefer the one with richer holdings data.
* **get_macro** — AKshare primary (free); Tushare fallback.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.datasource.base import BaseDataSource
from app.models.fund import (
    FundBasicInfo,
    ManagerInfo,
    NAVRecord,
    Portfolio,
)

if TYPE_CHECKING:
    from app.datasource.akshare_adapter import AKshareAdapter
    from app.datasource.tushare import TushareAdapter

logger = logging.getLogger(__name__)


class CompositeDataSource(BaseDataSource):
    """Combine multiple data sources with fallback & merge semantics.

    *primary* (AKshare) is tried first for most methods because it is free
    and has no rate limits.  *fallback* (Tushare) is used when the primary
    fails or returns incomplete data.
    """

    def __init__(
        self,
        primary: AKshareAdapter,
        fallback: TushareAdapter | None = None,
    ):
        self._primary = primary
        self._fallback = fallback

    # ------------------------------------------------------------------
    # BaseDataSource implementation
    # ------------------------------------------------------------------

    async def get_fund_nav(self, code: str, days: int = 90) -> list[NAVRecord]:
        # AKshare primary.
        try:
            records = await self._primary.get_fund_nav(code, days=days)
            if records:
                return records
        except Exception as exc:
            logger.debug("AKshare NAV failed for %s: %s", code, exc)

        # Tushare fallback.
        if self._fallback is not None:
            try:
                return await self._fallback.get_fund_nav(code, days=days)
            except Exception as exc:
                logger.debug("Tushare NAV fallback also failed for %s: %s", code, exc)

        return []

    async def get_fund_basic(self, code: str) -> FundBasicInfo:
        # AKshare primary.
        basic: FundBasicInfo | None = None
        try:
            basic = await self._primary.get_fund_basic(code)
        except Exception as exc:
            logger.debug("AKshare basic info failed for %s: %s", code, exc)

        # Tushare fallback / enrichment for fee fields.
        if self._fallback is not None:
            try:
                ts_basic = await self._fallback.get_fund_basic(code)
                if basic is None:
                    basic = ts_basic
                else:
                    # Enrich with Tushare-only fields (fees, benchmark).
                    if basic.management_fee is None and ts_basic.management_fee is not None:
                        basic.management_fee = ts_basic.management_fee
                    if basic.custodian_fee is None and ts_basic.custodian_fee is not None:
                        basic.custodian_fee = ts_basic.custodian_fee
                    if not basic.benchmark and ts_basic.benchmark:
                        basic.benchmark = ts_basic.benchmark
            except Exception as exc:
                logger.debug("Tushare basic info enrichment failed for %s: %s", code, exc)

        if basic is None:
            raise ValueError(f"未找到基金: {code}（所有数据源均失败）")

        return basic

    async def get_fund_manager(self, code: str) -> ManagerInfo:
        # Run both in parallel and merge.
        akshare_task = asyncio.create_task(self._try_get_manager_akshare(code))
        tushare_task = None
        if self._fallback is not None:
            tushare_task = asyncio.create_task(self._try_get_manager_tushare(code))

        akshare_mgr = await akshare_task
        tushare_mgr = await tushare_task if tushare_task else None

        if akshare_mgr is None and tushare_mgr is None:
            raise ValueError(f"未找到管理基金 {code} 的基金经理（所有数据源均失败）")

        # Merge: AKshare wins for name/id/total_aum, Tushare fills education/style.
        if akshare_mgr is not None:
            result = akshare_mgr
            if tushare_mgr is not None:
                if result.education is None:
                    result.education = tushare_mgr.education
                if result.style is None:
                    result.style = tushare_mgr.style
            return result

        return tushare_mgr  # type: ignore[return-value]

    async def get_fund_portfolio(self, code: str) -> Portfolio:
        # Try both; prefer the one with more holdings.
        akshare_task = asyncio.create_task(self._try_get_portfolio_akshare(code))
        tushare_task = None
        if self._fallback is not None:
            tushare_task = asyncio.create_task(self._try_get_portfolio_tushare(code))

        akshare_pf = await akshare_task
        tushare_pf = await tushare_task if tushare_task else None

        # Prefer AKshare (usually has richer stock-level data).
        if akshare_pf is not None and len(akshare_pf.top_10_stocks) > 0:
            return akshare_pf
        if tushare_pf is not None and len(tushare_pf.top_10_stocks) > 0:
            return tushare_pf
        if akshare_pf is not None:
            return akshare_pf
        if tushare_pf is not None:
            return tushare_pf

        # Both failed — return empty portfolio.
        return Portfolio(fund_code=code, report_date="")

    async def get_macro(self, indicator: str) -> dict:
        # AKshare primary.
        try:
            result = await self._primary.get_macro(indicator)
            if result:
                return result
        except Exception as exc:
            logger.debug("AKshare macro (%s) failed: %s", indicator, exc)

        # Tushare fallback.
        if self._fallback is not None:
            try:
                return await self._fallback.get_macro(indicator)
            except Exception as exc:
                logger.debug("Tushare macro fallback (%s) failed: %s", indicator, exc)

        return []

    async def close(self) -> None:
        await self._primary.close()
        if self._fallback is not None:
            await self._fallback.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _try_get_manager_akshare(self, code: str) -> ManagerInfo | None:
        try:
            return await self._primary.get_fund_manager(code)
        except Exception as exc:
            logger.debug("AKshare manager failed for %s: %s", code, exc)
            return None

    async def _try_get_manager_tushare(self, code: str) -> ManagerInfo | None:
        try:
            return await self._fallback.get_fund_manager(code)  # type: ignore[union-attr]
        except Exception as exc:
            logger.debug("Tushare manager failed for %s: %s", code, exc)
            return None

    async def _try_get_portfolio_akshare(self, code: str) -> Portfolio | None:
        try:
            return await self._primary.get_fund_portfolio(code)
        except Exception as exc:
            logger.debug("AKshare portfolio failed for %s: %s", code, exc)
            return None

    async def _try_get_portfolio_tushare(self, code: str) -> Portfolio | None:
        try:
            return await self._fallback.get_fund_portfolio(code)  # type: ignore[union-attr]
        except Exception as exc:
            logger.debug("Tushare portfolio failed for %s: %s", code, exc)
            return None
