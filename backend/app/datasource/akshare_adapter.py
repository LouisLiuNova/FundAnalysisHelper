"""AKShare-based data source adapter for Chinese mutual fund data.

AKShare (https://akshare.akfamily.xyz/) is a free, open-source financial data
library. Unlike Tushare, it does not require a registration token.

All AKShare functions are synchronous; this adapter wraps them with
``asyncio.to_thread()`` to integrate into the async backend.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

import akshare as ak

from app.datasource.base import BaseDataSource
from app.models.fund import FundBasicInfo, ManagerInfo, NAVRecord, Portfolio, StockHolding

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.datasource.cache import RedisCache


def _normalise_code(code: str) -> str:
    """Strip ``.OF`` / ``.SH`` / ``.SZ`` suffix so AKShare gets a 6-digit code."""
    return code.split(".")[0]


class AKshareAdapter(BaseDataSource):
    """Data source backed by AKShare (free, no token needed)."""

    def __init__(self, cache: RedisCache | None = None):
        self._cache = cache

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _cached(
        self,
        key: str,
        fetcher: Callable[[], object],
        ttl: int = 3600,
    ) -> dict | list:
        """Return cached data if available, otherwise call *fetcher* and cache."""
        if self._cache is not None:
            cached = await self._cache.get(key)
            if cached is not None:
                return cached

        data = await asyncio.to_thread(fetcher)

        if self._cache is not None:
            await self._cache.set(key, data, ttl=ttl)
        return data

    # ------------------------------------------------------------------
    # BaseDataSource implementation
    # ------------------------------------------------------------------

    async def get_fund_nav(self, code: str, days: int = 90) -> list[NAVRecord]:
        code6 = _normalise_code(code)

        def fetch() -> list[dict]:
            # AKShare splits unit NAV and accumulated NAV into separate endpoints.
            unit = ak.fund_open_fund_info_em(
                symbol=code6, indicator="单位净值走势", period="成立来"
            )
            acc = ak.fund_open_fund_info_em(
                symbol=code6, indicator="累计净值走势", period="成立来"
            )

            # Build a date → acc_nav lookup.
            acc_map: dict[str, float] = {}
            if not acc.empty and "累计净值" in acc.columns:
                for _, row in acc.iterrows():
                    acc_map[str(row["净值日期"])] = float(row["累计净值"])

            records: list[dict] = []
            if unit.empty:
                return records

            for _, row in unit.iterrows():
                rec: dict = {
                    "date": str(row["净值日期"]),
                    "nav": float(row["单位净值"]),
                    "acc_nav": acc_map.get(str(row["净值日期"]), float(row["单位净值"])),
                }
                # 日增长率 is present for unit NAV; convert to decimal.
                if "日增长率" in unit.columns:
                    daily = row.get("日增长率")
                    if daily is not None and str(daily) != "nan":
                        rec["daily_return"] = float(daily) / 100.0
                records.append(rec)

            # Return at most *days* records (most recent first already).
            return records[:days]

        key = f"ak:nav:{code}:{days}d"
        data = await self._cached(key, fetch, ttl=21600)
        return [NAVRecord(**r) for r in data]

    async def get_fund_basic(self, code: str) -> FundBasicInfo:
        code6 = _normalise_code(code)

        def fetch() -> dict:
            df = ak.fund_individual_basic_info_xq(symbol=code6, timeout=15)
            if df is None or df.empty:
                raise ValueError(f"未找到基金: {code}")

            # AKShare returns item/value pairs.
            items: dict[str, str] = {}
            for _, row in df.iterrows():
                items[str(row["item"])] = str(row["value"]) if row["value"] else ""

            # Parse AUM from string like "26.44亿".
            aum: float | None = None
            raw_aum = items.get("最新规模", "")
            if raw_aum and raw_aum != "nan":
                try:
                    raw_aum = raw_aum.replace("亿", "").replace(",", "")
                    aum = float(raw_aum) * 1e8
                except (ValueError, TypeError):
                    aum = None

            return {
                "code": code,  # Keep the original code format.
                "name": items.get("基金名称", ""),
                "fund_type": items.get("基金类型"),
                "establish_date": items.get("成立时间"),
                "management_fee": None,  # AKShare basic info doesn't include fees.
                "custodian_fee": None,
                "benchmark": items.get("业绩比较基准"),
                "aum": aum,
            }

        key = f"ak:fund:{code}"
        data = await self._cached(key, fetch, ttl=86400)
        return FundBasicInfo(**data)

    async def get_fund_manager(self, code: str) -> ManagerInfo:
        code6 = _normalise_code(code)

        def fetch() -> dict:
            df = ak.fund_manager_em()
            if df is None or df.empty:
                raise ValueError(f"未找到管理基金 {code} 的基金经理")

            # Find the row where 现任基金代码 contains our code.
            mask = df["现任基金代码"].astype(str).str.contains(code6, na=False)
            matches = df[mask]
            if matches.empty:
                raise ValueError(f"未找到管理基金 {code} 的基金经理")

            # Pick the first manager (primary).
            row = matches.iloc[0]
            exp_days = float(row.get("累计从业时间", 0) or 0)
            experience_years = round(exp_days / 365.0, 1) if exp_days else None

            return {
                "id": str(row.get("序号", "")),
                "name": str(row["姓名"]),
                "experience_years": experience_years,
                "managed_funds": (
                    len(str(row.get("现任基金代码", "")).split(","))
                    if row.get("现任基金代码")
                    else None
                ),
                "total_aum": (
                    float(row["现任基金资产总规模"])
                    if row.get("现任基金资产总规模")
                    else None
                ),
                "education": None,
                "style": None,
            }

        key = f"ak:mgr:{code}"
        data = await self._cached(key, fetch, ttl=86400)
        return ManagerInfo(**data)

    async def get_fund_portfolio(self, code: str) -> Portfolio:
        code6 = _normalise_code(code)

        def fetch() -> dict:
            from datetime import datetime

            current_year = str(datetime.now().year)
            df = ak.fund_portfolio_hold_em(symbol=code6, date=current_year)
            if df is None or df.empty:
                return {
                    "fund_code": code,
                    "report_date": "",
                    "top_10_stocks": [],
                    "sector_allocation": {},
                    "asset_allocation": {},
                }

            report_dates = df["季度"].unique().tolist() if "季度" in df.columns else []
            report_date = report_dates[0] if report_dates else ""

            stocks: list[dict] = []
            for _, row in df.iterrows():
                stocks.append(
                    StockHolding(
                        stock_code=str(row.get("股票代码", "")),
                        stock_name=str(row.get("股票名称", "")),
                        weight_pct=float(row["占净值比例"]) if row.get("占净值比例") else 0.0,
                        shares=float(row["持股数"]) if row.get("持股数") else None,
                        market_value=float(row["持仓市值"]) if row.get("持仓市值") else None,
                    ).model_dump()
                )

            return {
                "fund_code": code,
                "report_date": report_date,
                "top_10_stocks": stocks,
                "sector_allocation": {},
                "asset_allocation": {},
            }

        key = f"ak:portfolio:{code}"
        data = await self._cached(key, fetch, ttl=86400)
        return Portfolio(**data)

    async def get_macro(self, indicator: str) -> dict:
        indicators = {
            "shibor": (ak.macro_china_shibor_all, "ak:macro:shibor"),
            "cpi": (ak.macro_china_cpi_yearly, "ak:macro:cpi"),
            "gdp": (ak.macro_china_gdp_yearly, "ak:macro:gdp"),
        }
        if indicator not in indicators:
            raise ValueError(f"不支持的宏观指标: {indicator}")

        fetch_fn, cache_key = indicators[indicator]

        def fetch() -> list[dict]:
            df = fetch_fn()
            if df is None or df.empty:
                return []
            return json.loads(df.head(100).to_json(orient="records"))

        return await self._cached(cache_key, fetch, ttl=86400)

    async def get_fund_portfolio_industry_allocation(self, code: str) -> list[dict]:
        code6 = _normalise_code(code)

        def fetch() -> list[dict]:
            from datetime import datetime

            current_year = str(datetime.now().year)
            df = ak.fund_portfolio_industry_allocation_em(symbol=code6, date=current_year)
            if df is None or df.empty:
                return []
            return df.to_dict(orient="records")

        key = f"ak:industry_allocation:{code}"
        return await self._cached(key, fetch, ttl=86400)

    async def get_fund_announcements(self, code: str, limit: int = 5) -> list[dict]:
        code6 = _normalise_code(code)

        def fetch() -> list[dict]:
            df = ak.fund_announcement_report_em(symbol=code6)
            if df is None or df.empty:
                return []
            records = df.head(limit).to_dict(orient="records")
            return records

        key = f"ak:announcements:{code}:{limit}"
        return await self._cached(key, fetch, ttl=3600)

    async def close(self) -> None:
        if self._cache is not None:
            await self._cache.close()
