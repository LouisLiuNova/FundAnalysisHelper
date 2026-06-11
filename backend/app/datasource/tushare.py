import json
from collections.abc import Callable

import tushare as ts

from app.datasource.base import BaseDataSource
from app.datasource.cache import RedisCache
from app.models.fund import FundBasicInfo, ManagerInfo, NAVRecord, Portfolio


class TushareAdapter(BaseDataSource):
    def __init__(self, token: str, cache: RedisCache):
        ts.set_token(token)
        self._pro = ts.pro_api()
        self._cache = cache

    async def _cached(
        self, key: str, fetcher: Callable[[], object], ttl: int = 3600
    ) -> dict | list:
        cached = await self._cache.get(key)
        if cached is not None:
            return cached
        data = fetcher()
        await self._cache.set(key, data, ttl=ttl)
        return data

    async def get_fund_nav(self, code: str, days: int = 90) -> list[NAVRecord]:
        def fetch() -> list[dict]:
            df = self._pro.fund_nav(ts_code=code, limit=days)
            records: list[dict] = []
            for _, row in df.iterrows():
                records.append(
                    {
                        "date": row["nav_date"],
                        "nav": float(row["unit_nav"]),
                        "acc_nav": float(row["accum_nav"]),
                    }
                )
            return records

        key = f"nav:{code}:{days}d"
        data = await self._cached(key, fetch, ttl=21600)
        return [NAVRecord(**r) for r in data]

    async def get_fund_basic(self, code: str) -> FundBasicInfo:
        def fetch() -> dict:
            df = self._pro.fund_basic(ts_code=code)
            if df.empty:
                raise ValueError(f"未找到基金: {code}")
            row = df.iloc[0]
            return {
                "code": row["ts_code"],
                "name": row["name"],
                "fund_type": row.get("fund_type"),
                "establish_date": row.get("found_date"),
                "management_fee": float(row["m_fee"]) if row.get("m_fee") else None,
                "custodian_fee": float(row["c_fee"]) if row.get("c_fee") else None,
                "benchmark": row.get("benchmark"),
            }

        key = f"fund:{code}"
        data = await self._cached(key, fetch, ttl=86400)
        return FundBasicInfo(**data)

    async def get_fund_manager(self, code: str) -> ManagerInfo:
        def fetch() -> dict:
            df = self._pro.fund_manager(ts_code=code)
            if df.empty:
                raise ValueError(f"未找到基金经理: {code}")
            row = df.iloc[0]
            return {
                "id": str(row.get("mgr_id", "")),
                "name": row["name"],
                "experience_years": float(row["exp_years"]) if row.get("exp_years") else None,
                "managed_funds": int(row["fund_nums"]) if row.get("fund_nums") else None,
                "total_aum": float(row["fund_aum"]) if row.get("fund_aum") else None,
                "education": row.get("edu"),
                "style": row.get("style"),
            }

        key = f"mgr:{code}"
        data = await self._cached(key, fetch, ttl=86400)
        return ManagerInfo(**data)

    async def get_fund_portfolio(self, code: str) -> Portfolio:
        def fetch() -> dict:
            empty = {
                "fund_code": code,
                "report_date": "",
                "top_10_stocks": [],
                "sector_allocation": {},
                "asset_allocation": {},
            }
            df = self._pro.fund_portfolio(ts_code=code)
            if df.empty:
                return empty

            report_date = ""
            if "end_date" in df.columns:
                report_date = str(df.iloc[0]["end_date"])

            stocks: list[dict] = []
            for _, row in df.iterrows():
                stocks.append(
                    {
                        "stock_code": str(row.get("symbol", "")),
                        "stock_name": str(row.get("name", row.get("symbol", ""))),
                        "weight_pct": float(row.get("stk_mkv_ratio", 0) or 0),
                        "shares": float(row["amount"]) if row.get("amount") else None,
                        "market_value": float(row["mkv"]) if row.get("mkv") else None,
                    }
                )

            return {
                "fund_code": code,
                "report_date": report_date,
                "top_10_stocks": stocks,
                "sector_allocation": {},
                "asset_allocation": {},
            }

        key = f"portfolio:{code}"
        data = await self._cached(key, fetch, ttl=86400)
        return Portfolio(**data)

    async def get_macro(self, indicator: str) -> dict:
        indicators = {
            "shibor": lambda: self._pro.shibor(),
            "cpi": lambda: self._pro.cpi(),
            "gdp": lambda: self._pro.gdp(),
        }
        if indicator not in indicators:
            raise ValueError(f"不支持的宏观指标: {indicator}")

        def fetch() -> list[dict]:
            df = indicators[indicator]()
            return json.loads(df.to_json(orient="records"))

        key = f"macro:{indicator}"
        return await self._cached(key, fetch, ttl=86400)

    async def get_fund_portfolio_industry_allocation(self, code: str) -> list[dict]:
        # Tushare does not provide a corresponding API for industry allocation.
        logger = __import__("logging").getLogger(__name__)
        logger.debug("Tushare: get_fund_portfolio_industry_allocation not available for %s", code)
        return []

    async def get_fund_announcements(self, code: str, limit: int = 5) -> list[dict]:
        # Tushare does not provide a corresponding API for fund announcements.
        logger = __import__("logging").getLogger(__name__)
        logger.debug("Tushare: get_fund_announcements not available for %s", code)
        return []

    async def close(self) -> None:
        await self._cache.close()
