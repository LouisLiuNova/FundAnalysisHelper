from pydantic import BaseModel, Field


class FundBasicInfo(BaseModel):
    code: str = Field(description="基金代码，如 000001.OF")
    name: str = Field(description="基金名称")
    fund_type: str | None = None
    establish_date: str | None = None
    management_fee: float | None = None
    custodian_fee: float | None = None
    benchmark: str | None = None
    aum: float | None = Field(default=None, description="管理规模(元)")


class NAVRecord(BaseModel):
    date: str
    nav: float = Field(description="单位净值")
    acc_nav: float = Field(description="累计净值")
    daily_return: float | None = None


class ManagerInfo(BaseModel):
    id: str
    name: str
    experience_years: float | None = None
    managed_funds: int | None = None
    total_aum: float | None = None
    education: str | None = None
    style: str | None = None


class StockHolding(BaseModel):
    stock_code: str
    stock_name: str
    weight_pct: float = 0.0
    shares: float | None = None
    market_value: float | None = None


class Portfolio(BaseModel):
    fund_code: str
    report_date: str
    top_10_stocks: list[StockHolding] = Field(default_factory=list)
    sector_allocation: dict[str, float] = Field(default_factory=dict)
    asset_allocation: dict[str, float] = Field(default_factory=dict)
