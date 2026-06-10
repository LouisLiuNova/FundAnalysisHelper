"""Data source layer — abstract interface, factory, composite, and adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.datasource.base import BaseDataSource
    from app.datasource.cache import RedisCache


def create_datasource(
    source_type: str,
    *,
    tushare_token: str = "",
    cache: RedisCache | None = None,
) -> BaseDataSource:
    """Factory: return the configured data source adapter(s).

    Args:
        source_type: ``"tushare"``, ``"akshare"``, or ``"composite"`` (both).
        tushare_token: Required when *source_type* includes ``"tushare"``.
        cache: Optional Redis cache instance shared across adapters.
    """
    source_type = source_type.lower().strip()

    if source_type == "composite":
        from app.datasource.akshare_adapter import AKshareAdapter
        from app.datasource.composite import CompositeDataSource
        from app.datasource.tushare import TushareAdapter

        akshare = AKshareAdapter(cache=cache)
        tushare = TushareAdapter(token=tushare_token, cache=cache) if tushare_token else None
        return CompositeDataSource(primary=akshare, fallback=tushare)

    if source_type == "akshare":
        from app.datasource.akshare_adapter import AKshareAdapter

        return AKshareAdapter(cache=cache)

    if source_type == "tushare":
        from app.datasource.tushare import TushareAdapter

        if not tushare_token:
            raise ValueError("Tushare adapter requires a token. Set tushare.token in config.yaml.")
        return TushareAdapter(token=tushare_token, cache=cache)

    raise ValueError(
        f"Unknown datasource type: {source_type!r}. Expected 'tushare', 'akshare', or 'composite'."
    )
