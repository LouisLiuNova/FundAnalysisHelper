from abc import ABC, abstractmethod
from app.models.fund import FundBasicInfo, NAVRecord, ManagerInfo, Portfolio


class BaseDataSource(ABC):
    @abstractmethod
    async def get_fund_nav(self, code: str, days: int = 90) -> list[NAVRecord]:
        ...

    @abstractmethod
    async def get_fund_basic(self, code: str) -> FundBasicInfo:
        ...

    @abstractmethod
    async def get_fund_manager(self, code: str) -> ManagerInfo:
        ...

    @abstractmethod
    async def get_fund_portfolio(self, code: str) -> Portfolio:
        ...

    @abstractmethod
    async def get_macro(self, indicator: str) -> dict:
        ...
