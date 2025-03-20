"""
Solana connection pool management
"""
from typing import Dict, List, Optional, Any, Union
import logging
import asyncio
from solana.rpc.async_api import AsyncClient
from .solana_error import RPCError
from .logging_config import setup_logging
from .solana_ssl_config import should_bypass_ssl_verification
import time
from datetime import datetime

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
        timeout: float = 20.0,
        ssl_verify: bool = True,
        endpoint: str = None
    ):
        """Initialize the connection pool"""
        # Handle both endpoint and endpoints parameters for backward compatibility
        if endpoint is not None:
            self.endpoints = [endpoint]
        else:
            self.endpoints = endpoints
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.ssl_verify = ssl_verify
        
        # Initialize empty pool
        self._pool: List[AsyncClient] = []
        self._current_client_index = 0
        self._pool_lock = asyncio.Lock()
        self._initialized = False
        
        # Track endpoint-specific settings
        self._endpoint_settings: Dict[str, Dict[str, Any]] = {}
        
    def get_primary_endpoint(self) -> str:
        """Get the primary endpoint URL."""
        return self.endpoints[0] if self.endpoints else ""
        
    def _get_endpoint_ssl_setting(self, endpoint: str) -> bool:
        """Get the SSL verification setting for a specific endpoint."""
        # Check if we should bypass SSL verification for this endpoint
        if should_bypass_ssl_verification(endpoint):
            logger.info(f"Bypassing SSL verification for endpoint: {endpoint}")
            return False
            
        # Use the default setting if not specified
        return self.ssl_verify
        
    async def initialize(self, endpoints=None):
        """Initialize the connection pool."""
        if endpoints is None:
            endpoints = self.endpoints
            
        if self._initialized:
            return
            
        async with self._pool_lock:
            if self._initialized:
                return
                
            logger.info("Initializing Solana RPC connection pool...")
            
            for endpoint in endpoints:
                try:
                    # Get SSL verification setting for this endpoint
                    ssl_verify = self._get_endpoint_ssl_setting(endpoint)
                    
                    # Store endpoint settings
                    self._endpoint_settings[endpoint] = {
                        "ssl_verify": ssl_verify
                    }
                    
                    client = await self._create_client(endpoint, ssl_verify)
                    if client:
                        self._pool.append(client)
                        logger.info(f"Successfully connected to endpoint: {endpoint} (SSL verify: {ssl_verify})")
                except Exception as e:
                    logger.error(f"Failed to connect to endpoint {endpoint}: {str(e)}")
                    
                    # If SSL error, try again with SSL verification disabled
                    if "SSL" in str(e) and self.ssl_verify:
                        try:
                            logger.info(f"Retrying endpoint {endpoint} with SSL verification disabled")
                            client = await self._create_client(endpoint, False)
                            if client:
                                self._pool.append(client)
                                
                                # Update endpoint settings
                                self._endpoint_settings[endpoint] = {
                                    "ssl_verify": False
                                }
                                
                                # Add to SSL bypass list for future use
                                from .solana_ssl_config import add_ssl_bypass_endpoint
                                add_ssl_bypass_endpoint(endpoint)
                                
                                logger.info(f"Successfully connected to endpoint: {endpoint} (SSL verify: False)")
                        except Exception as retry_e:
                            logger.error(f"Failed to connect to endpoint {endpoint} even with SSL verification disabled: {str(retry_e)}")
                    
            if not self._pool:
                raise RPCError("Failed to initialize any RPC connections")
                
            self._initialized = True
            logger.info(f"Connection pool initialized with {len(self._pool)} clients")
            
    async def _create_client(self, endpoint: str, ssl_verify: bool = True) -> Optional[AsyncClient]:
        """Create a new client instance"""
        try:
            logger.debug(f"Attempting to create client for endpoint: {endpoint} (SSL verify: {ssl_verify})")
            
            # Create client with appropriate SSL settings
            from .solana_rpc import SolanaClient
            client = SolanaClient(
                endpoint=endpoint,
                timeout=self.timeout,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
                ssl_verify=ssl_verify
            )
            
            # Test connection
            await client.connect()
            await client.get_health()
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

    async def get_endpoint_health(self) -> List[Dict[str, Any]]:
        """Get health status of all RPC endpoints"""
        if not self._initialized:
            await self.initialize()
            
        results = []
        for endpoint in self.endpoints:
            try:
                # Create a temporary client to test the endpoint
                ssl_verify = self._get_endpoint_ssl_setting(endpoint)
                from .solana_rpc import SolanaClient
                client = SolanaClient(
                    endpoint=endpoint,
                    timeout=5.0,  # Short timeout for health check
                    max_retries=1,
                    retry_delay=0.5,
                    ssl_verify=ssl_verify
                )
                
                # Test the endpoint
                await client.connect()
                start_time = time.time()
                health = await client.get_health()
                latency = time.time() - start_time
                
                # Get version info
                version_info = await client.get_version()
                
                # Add to results
                results.append({
                    "endpoint": endpoint,
                    "status": "healthy" if health == "ok" else health,
                    "latency_ms": round(latency * 1000, 2),
                    "version": version_info.get("solana-core", "unknown"),
                    "feature_set": version_info.get("feature-set", "unknown"),
                    "ssl_verify": ssl_verify,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Close the client
                await client.close()
                
            except Exception as e:
                results.append({
                    "endpoint": endpoint,
                    "status": "error",
                    "error": str(e),
                    "ssl_verify": self._get_endpoint_ssl_setting(endpoint),
                    "timestamp": datetime.now().isoformat()
                })
                
        # Sort by status (healthy first) and then by latency
        results.sort(key=lambda x: (0 if x.get("status") == "healthy" else 1, 
                                   x.get("latency_ms", float("inf"))))
        
        return results
        
    async def get_endpoint_health_detail(self, endpoint: str) -> Dict[str, Any]:
        """Get detailed health status for specific endpoint"""
        if not endpoint in self.endpoints:
            return {
                "endpoint": endpoint,
                "status": "error",
                "error": "Endpoint not in pool",
                "timestamp": datetime.now().isoformat()
            }
            
        try:
            # Create a temporary client to test the endpoint
            ssl_verify = self._get_endpoint_ssl_setting(endpoint)
            from .solana_rpc import SolanaClient
            client = SolanaClient(
                endpoint=endpoint,
                timeout=10.0,
                max_retries=1,
                retry_delay=0.5,
                ssl_verify=ssl_verify
            )
            
            # Connect and get basic info
            await client.connect()
            result = {
                "endpoint": endpoint,
                "ssl_verify": ssl_verify,
                "timestamp": datetime.now().isoformat(),
                "tests": {}
            }
            
            # Test health
            start_time = time.time()
            health = await client.get_health()
            latency = time.time() - start_time
            result["status"] = "healthy" if health == "ok" else health
            result["latency_ms"] = round(latency * 1000, 2)
            result["tests"]["health"] = {
                "status": "success" if health == "ok" else "error",
                "latency_ms": round(latency * 1000, 2),
                "result": health
            }
            
            # Test version
            try:
                start_time = time.time()
                version = await client.get_version()
                latency = time.time() - start_time
                result["version"] = version.get("solana-core", "unknown")
                result["feature_set"] = version.get("feature-set", "unknown")
                result["tests"]["version"] = {
                    "status": "success",
                    "latency_ms": round(latency * 1000, 2),
                    "result": version
                }
            except Exception as e:
                result["tests"]["version"] = {
                    "status": "error",
                    "error": str(e)
                }
                
            # Test slot
            try:
                start_time = time.time()
                slot = await client.get_slot()
                latency = time.time() - start_time
                result["slot"] = slot
                result["tests"]["slot"] = {
                    "status": "success",
                    "latency_ms": round(latency * 1000, 2),
                    "result": slot
                }
            except Exception as e:
                result["tests"]["slot"] = {
                    "status": "error",
                    "error": str(e)
                }
                
            # Test block production
            try:
                start_time = time.time()
                block_production = await client.get_block_production()
                latency = time.time() - start_time
                result["tests"]["block_production"] = {
                    "status": "success",
                    "latency_ms": round(latency * 1000, 2),
                    "result": "supported"
                }
            except Exception as e:
                result["tests"]["block_production"] = {
                    "status": "error",
                    "error": str(e),
                    "result": "not supported" if "Method not found" in str(e) else "error"
                }
                
            # Close the client
            await client.close()
            
            return result
            
        except Exception as e:
            return {
                "endpoint": endpoint,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get current RPC pool status"""
        if not self._initialized:
            await self.initialize()
            
        return {
            "initialized": self._initialized,
            "pool_size": len(self._pool),
            "endpoints": self.endpoints,
            "current_index": self._current_client_index,
            "timestamp": datetime.now().isoformat()
        }
        
    async def rotate_endpoint(self) -> Dict[str, Any]:
        """Force rotation to next endpoint"""
        if not self._initialized:
            await self.initialize()
            
        async with self._pool_lock:
            old_index = self._current_client_index
            self._current_client_index = (self._current_client_index + 1) % len(self._pool)
            
            return {
                "success": True,
                "previous_index": old_index,
                "new_index": self._current_client_index,
                "previous_endpoint": self.endpoints[old_index] if old_index < len(self.endpoints) else None,
                "new_endpoint": self.endpoints[self._current_client_index] if self._current_client_index < len(self.endpoints) else None,
                "timestamp": datetime.now().isoformat()
            }
            
    def get_endpoints(self) -> List[Dict[str, Any]]:
        """List available endpoints"""
        return [
            {
                "endpoint": endpoint,
                "ssl_verify": self._get_endpoint_ssl_setting(endpoint),
                "index": i
            }
            for i, endpoint in enumerate(self.endpoints)
        ]

# Global connection pool instance
_connection_pool: Optional[SolanaConnectionPool] = None
_pool_lock = asyncio.Lock()

async def get_connection_pool(endpoints: List[str] = None, ssl_verify: bool = True) -> SolanaConnectionPool:
    """
    Get or create the global connection pool instance
    
    Args:
        endpoints: Optional list of RPC endpoints to use
        ssl_verify: Whether to verify SSL certificates by default
        
    Returns:
        The global connection pool instance
    """
    global _connection_pool
    
    if _connection_pool is None:
        async with _pool_lock:
            if _connection_pool is None:
                from .solana_rpc_constants import DEFAULT_RPC_ENDPOINTS
                _connection_pool = SolanaConnectionPool(
                    endpoints=endpoints or DEFAULT_RPC_ENDPOINTS,
                    ssl_verify=ssl_verify
                )
                await _connection_pool.initialize()
    elif endpoints:
        # If endpoints are provided and the pool exists, reinitialize with new endpoints
        async with _pool_lock:
            # Close existing connections
            await _connection_pool.close()
            
            # Update endpoints and reinitialize
            _connection_pool.endpoints = endpoints
            _connection_pool.ssl_verify = ssl_verify
            _connection_pool._initialized = False
            await _connection_pool.initialize()
                
    return _connection_pool
