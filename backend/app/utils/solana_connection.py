"""
Solana connection pool management
"""
from typing import Dict, List, Optional, Any
import logging
import asyncio
from solana.rpc.async_api import AsyncClient
from .solana_types import RPCError
from .logging_config import setup_logging

# Configure logging
logger = setup_logging('solana.connection')

# Default RPC endpoints
DEFAULT_RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com"
]

class SolanaConnectionPool:
    """Pool of Solana RPC clients with enhanced connection management"""
    
    def __init__(
        self,
        endpoints: List[str] = DEFAULT_RPC_ENDPOINTS,
        pool_size: int = 3,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 20.0
    ):
        """Initialize the connection pool"""
        self.endpoints = endpoints
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # Initialize empty pool
        self._pool: List[AsyncClient] = []
        self._current_client_index = 0
        self._pool_lock = asyncio.Lock()
        self._initialized = False
        
    def get_primary_endpoint(self) -> str:
        """Get the primary endpoint URL."""
        return self.endpoints[0] if self.endpoints else ""
        
    async def initialize(self):
        """Initialize the connection pool by creating initial connections"""
        if self._initialized:
            return
            
        async with self._pool_lock:
            if self._initialized:
                return
                
            logger.info("Initializing Solana RPC connection pool...")
            
            for endpoint in self.endpoints:
                try:
                    client = await self._create_client(endpoint)
                    if client:
                        self._pool.append(client)
                        logger.info(f"Successfully connected to endpoint: {endpoint}")
                except Exception as e:
                    logger.error(f"Failed to connect to endpoint {endpoint}: {str(e)}")
                    
            if not self._pool:
                raise RPCError("Failed to initialize any RPC connections")
                
            self._initialized = True
            logger.info(f"Connection pool initialized with {len(self._pool)} clients")
            
    async def _create_client(self, endpoint: str) -> Optional[AsyncClient]:
        """Create a new client instance"""
        try:
            logger.debug(f"Attempting to create client for endpoint: {endpoint}")
            logger.debug(f"Connecting to Solana RPC endpoint: {endpoint}")
            
            client = AsyncClient(endpoint)
            # Test connection
            await client.is_connected()
            logger.info(f"Successfully connected to {endpoint}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create client for {endpoint}: {str(e)}")
            return None
            
    async def get_next_client(self) -> Optional[AsyncClient]:
        """Get the next available client from the pool using round-robin."""
        if not self._pool:
            return None
            
        async with self._pool_lock:
            self._current_client_index = (self._current_client_index + 1) % len(self._pool)
            return self._pool[self._current_client_index]
            
    async def get_client(self) -> AsyncClient:
        """Get a healthy client from the pool."""
        if not self._initialized:
            await self.initialize()
            
        async with self._pool_lock:
            if not self._pool:
                raise RPCError("No healthy clients available")
                
            client = self._pool[self._current_client_index]
            return client
            
    async def close(self):
        """Close all clients and cleanup resources"""
        async with self._pool_lock:
            for client in self._pool:
                try:
                    await client.close()
                except Exception as e:
                    logger.error(f"Error closing client: {str(e)}")
                    
            self._pool.clear()
            self._initialized = False
            
    async def cleanup(self):
        """Alias for close() to maintain compatibility"""
        await self.close()
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Global connection pool instance
_connection_pool: Optional[SolanaConnectionPool] = None
_pool_lock = asyncio.Lock()

async def get_connection_pool() -> SolanaConnectionPool:
    """Get or create the global connection pool instance"""
    global _connection_pool
    
    if _connection_pool is None:
        async with _pool_lock:
            if _connection_pool is None:
                _connection_pool = SolanaConnectionPool()
                await _connection_pool.initialize()
                
    return _connection_pool
