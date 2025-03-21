from typing import Dict, Any, Optional
import asyncio
from redis.asyncio import Redis
import logging

logger = logging.getLogger(__name__)

class DatabaseCache:
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._redis: Optional[Redis] = None
        try:
            self._redis = Redis(host='localhost', port=6379)
            # Test connection
            asyncio.get_event_loop().run_until_complete(self._redis.ping())
        except Exception as e:
            logger.warning(f'Redis connection failed: {e}. Using in-memory cache only')
            self._redis = None

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(key)

    async def set(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        self._cache[key] = data
        if self._redis and ttl:
            await self._redis.set(key, str(data), ex=ttl)

    async def get_cached_data(self, cache_key: str, params: Dict[str, Any], ttl: int) -> Dict[str, Any]:
        key = self._generate_cache_key(cache_key, params)
        return await self.get(key)

    async def set_cached_data(self, cache_key: str, params: Dict[str, Any], data: Dict[str, Any]) -> None:
        key = self._generate_cache_key(cache_key, params)
        await self.set(key, data)

    async def clear_cache(self, cache_key: str) -> None:
        keys_to_remove = [key for key in self._cache if key.startswith(cache_key)]
        for key in keys_to_remove:
            del self._cache[key]

    async def close(self):
        if self._redis:
            await self._redis.aclose()
        self._cache.clear()

    async def get_client(self) -> Redis:
        if not self._redis:
            self._redis = Redis.from_url('redis://localhost')
        return self._redis

    async def get_account_info(self, key: str) -> Optional[Dict[str, Any]]:
        if self._redis:
            data = await self._redis.get(key)
            if data:
                return eval(data)
            return None
        return self._cache.get(key)

    async def set_account_info(self, key: str, data: Dict[str, Any], ttl: int) -> None:
        if self._redis:
            await self._redis.set(key, str(data), ex=ttl)
        else:
            self._cache[key] = data

    async def release(self, client: Any) -> None:
        pass

    def _generate_cache_key(self, cache_key: str, params: Dict[str, Any]) -> str:
        param_str = '&'.join(f'{k}={v}' for k, v in sorted(params.items()))
        return f'{cache_key}?{param_str}'

async def get_database_cache() -> DatabaseCache:
    cache = DatabaseCache()
    await cache.get_client()
    return cache
