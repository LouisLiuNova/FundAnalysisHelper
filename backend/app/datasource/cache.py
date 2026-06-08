import json
import redis.asyncio as aioredis


class RedisCache:
    def __init__(self, host: str, port: int, db: int = 0, password: str = ""):
        self._redis = aioredis.Redis(
            host=host,
            port=port,
            db=db,
            password=password or None,
            decode_responses=False,
        )

    async def get(self, key: str) -> dict | list | None:
        data = await self._redis.get(key)
        if data is None:
            return None
        return json.loads(data)

    async def set(self, key: str, value: dict | list, ttl: int = 3600) -> None:
        await self._redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def close(self) -> None:
        await self._redis.close()
