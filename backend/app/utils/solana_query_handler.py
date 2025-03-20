from typing import Dict, Optional
import asyncio
from .cache.database_cache import DatabaseCache
from .solana_rpc import get_connection_pool, safe_rpc_call_async

class SolanaQueryHandler:
    def __init__(self, cache: DatabaseCache):
        self.cache = cache

    async def get_token_info(self, token_address: str) -> Optional[Dict[str, Any]]:
        # First try to get from cache
        cached_info = await self.get_cached_token_info(token_address)
        if cached_info:
            return cached_info

        # If not in cache, fetch from RPC
        try:
            pool = await get_connection_pool()
            async with pool.acquire() as client:
                result = await safe_rpc_call_async(
                    'getTokenAccountBalance',
                    client,
                    params=[token_address]
                )
                if result:
                    # Cache the result
                    await self.cache.set_account_info(
                        f'token_info:{token_address}',
                        result,
                        ttl=3600  # Cache for 1 hour
                    )
                    return result
        except Exception as e:
            print(f'Error fetching token info: {e}')
        return None

    async def get_cached_token_info(self, token_address: str) -> Optional[Dict[str, Any]]:
        return await self.cache.get_account_info(f'token_info:{token_address}')

    async def clear_token_info_cache(self, token_address: str) -> None:
        await self.cache.clear_cache(f'token_info:{token_address}')
