from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.client import get_db

COLLECTION_REPORTS = "fund_analysis_reports"
COLLECTION_CACHE = "fund_cache"
COLLECTION_LOGS = "analysis_logs"


def get_reports_col() -> AsyncIOMotorCollection:
    return get_db()[COLLECTION_REPORTS]


def get_cache_col() -> AsyncIOMotorCollection:
    return get_db()[COLLECTION_CACHE]


def get_logs_col() -> AsyncIOMotorCollection:
    return get_db()[COLLECTION_LOGS]
