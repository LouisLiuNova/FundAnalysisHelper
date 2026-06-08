import pytest
from unittest.mock import AsyncMock, patch
from app.datasource.cache import RedisCache


@pytest.fixture
def redis_cache():
    with patch("app.datasource.cache.aioredis.Redis") as mock_redis_cls:
        mock_redis = AsyncMock()
        mock_redis_cls.return_value = mock_redis
        cache = RedisCache(host="localhost", port=6379)
        yield cache, mock_redis


@pytest.mark.asyncio
async def test_cache_get_缓存未命中返回None(redis_cache):
    cache, mock_redis = redis_cache
    mock_redis.get.return_value = None
    result = await cache.get("key1")
    assert result is None


@pytest.mark.asyncio
async def test_cache_get_缓存命中返回字典(redis_cache):
    cache, mock_redis = redis_cache
    mock_redis.get.return_value = b'{"nav": 1.23}'
    result = await cache.get("key1")
    assert result == {"nav": 1.23}


@pytest.mark.asyncio
async def test_cache_set_带TTL写入(redis_cache):
    cache, mock_redis = redis_cache
    await cache.set("key1", {"nav": 1.23}, ttl=3600)
    mock_redis.setex.assert_called_once_with("key1", 3600, '{"nav": 1.23}')


@pytest.mark.asyncio
async def test_cache_delete_删除键(redis_cache):
    cache, mock_redis = redis_cache
    await cache.delete("key1")
    mock_redis.delete.assert_called_once_with("key1")
