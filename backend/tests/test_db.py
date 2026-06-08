import pytest
from unittest.mock import AsyncMock, patch
from app.db.client import get_db, init_db, close_db
from motor.motor_asyncio import AsyncIOMotorDatabase


@pytest.mark.asyncio
async def test_init_db_创建客户端并获取数据库():
    with patch("app.db.client.AsyncIOMotorClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client

        await init_db("mongodb://localhost:27017", "fund_analysis")

        db = get_db()
        assert db is not None
        await close_db()


@pytest.mark.asyncio
async def test_get_db_未初始化时抛出异常():
    import app.db.client as client_mod
    original = client_mod._db
    client_mod._db = None
    with pytest.raises(RuntimeError, match="Database not initialized"):
        get_db()
    client_mod._db = original
