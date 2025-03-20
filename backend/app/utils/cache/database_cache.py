from typing import Dict, Any, Optional
import asyncio
from redis.asyncio import Redis
<<<<<<< HEAD
import logging

logger = logging.getLogger(__name__)
=======
>>>>>>> origin/main

class DatabaseCache:
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._redis: Optional[Redis] = None
<<<<<<< HEAD
        try:
            self._redis = Redis(host='localhost', port=6379)
            # Test connection
            asyncio.get_event_loop().run_until_complete(self._redis.ping())
        except Exception as e:
            logger.warning(f'Redis connection failed: {e}. Using in-memory cache only')
            self._redis = None
=======
>>>>>>> origin/main

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(key)

<<<<<<< HEAD
    async def set(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        self._cache[key] = data
        if self._redis and ttl:
            await self._redis.set(key, data, ex=ttl)
=======
    async def set(self, key: str, data: Dict[str, Any]) -> None:
        self._cache[key] = data
>>>>>>> origin/main

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
<<<<<<< HEAD
        """Close all resources and clean up"""
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")
        self._redis = None
        self._cache.clear()
=======
        if self._redis:
            await self._redis.aclose()
>>>>>>> origin/main

    async def get_client(self) -> Redis:
        if not self._redis:
            self._redis = Redis.from_url('redis://localhost')
        return self._redis

    async def get_account_info(self, key: str) -> Optional[Dict[str, Any]]:
        if self._redis:
            return await self._redis.get(key)
        return self._cache.get(key)

    async def set_account_info(self, key: str, data: Dict[str, Any], ttl: int) -> None:
        if self._redis:
            await self._redis.set(key, data, ex=ttl)
        else:
            self._cache[key] = data

    async def release(self, client: Any) -> None:
        """Release a client back to the pool"""
        pass

    def _generate_cache_key(self, cache_key: str, params: Dict[str, Any]) -> str:
        param_str = '&'.join(f'{k}={v}' for k, v in sorted(params.items()))
        return f'{cache_key}?{param_str}'
<<<<<<< HEAD

async def get_database_cache() -> DatabaseCache:
    """Get an initialized database cache instance"""
    cache = DatabaseCache()
    await cache.get_client()  # Initialize Redis client
    return cache
=======
>>>>>>> origin/main
