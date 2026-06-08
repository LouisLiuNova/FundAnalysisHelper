from functools import lru_cache
from app.core.config import load_config, Config
from app.services.analysis import AnalysisService

_service: AnalysisService | None = None


@lru_cache
def get_config() -> Config:
    return load_config()


def get_analysis_service() -> AnalysisService:
    global _service
    if _service is None:
        config = get_config()
        _service = AnalysisService(
            mongodb_uri=config.mongodb.uri,
            db_name=config.mongodb.database,
            redis_host=config.redis.host,
            redis_port=config.redis.port,
            tushare_token=config.tushare.token,
        )
    return _service
