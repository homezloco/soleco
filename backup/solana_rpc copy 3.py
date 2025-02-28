"""
Solana RPC connection management module.
This module handles all Solana RPC client initialization and connection pooling.
"""

import logging
import time
import os
from typing import Dict, Any, List, Optional, Union, Set
import asyncio
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solders.pubkey import Pubkey
from solders.signature import Signature
from dotenv import load_dotenv
from .solana_response import SolanaResponseHandler
import httpx

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Ensure we have a handler that will process DEBUG messages
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

# Default RPC endpoints with priority order
DEFAULT_RPC_ENDPOINTS = [
    # Helius endpoint with API key (preferred)
    f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}",
    # Shyft endpoint
    os.getenv('SHYFT_RPC_URL'),
    # Extrnode endpoint
    os.getenv('EXTRNODE_RPC_URL'),
    # Alchemy endpoint
    os.getenv('ALCHEMY_RPC_URL'),
    # Public endpoints as fallback
    "https://api.mainnet-beta.solana.com",
    "https://solana-api.projectserum.com"
]

# Filter out any None values from endpoints list
DEFAULT_RPC_ENDPOINTS = [endpoint for endpoint in DEFAULT_RPC_ENDPOINTS if endpoint]

if not DEFAULT_RPC_ENDPOINTS:
    raise ValueError("No valid RPC endpoints found in environment variables")

logger.debug("Solana RPC module initialized with endpoints: %s", DEFAULT_RPC_ENDPOINTS)

class SolanaClient:
    """Client for making RPC requests to a Solana node"""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self._client = None
        self.error_count = 0
        self.last_used = 0
        self.average_latency = 0
        self._latency_samples = []
        self._max_latency_samples = 10
        self._backoff_time = 1.0
        self._max_backoff = 30.0
        self._response_handler = SolanaResponseHandler()
        logger.debug(f"Creating new SolanaClient for endpoint {endpoint}")
        
    async def connect(self) -> bool:
        """Connect to the Solana RPC endpoint with robust testing"""
        try:
            logger.debug(f"Attempting to connect to {self.endpoint}")
            start_time = time.time()
            
            # Create client with reasonable timeout
            self._client = AsyncClient(self.endpoint, timeout=5)
            
            # Quick test with get_slot
            async with asyncio.timeout(3):
                await self.get_slot()
                
            elapsed = time.time() - start_time
            logger.debug(f"Successfully connected to {self.endpoint} in {elapsed:.2f}s")
            return True
            
        except Exception as e:
            logger.debug(f"Error connecting to {self.endpoint}: {str(e)}")
            await self.close()
            return False
            
    async def close(self):
        """Close the client connection"""
        if self._client:
            await self._client.close()
            self._client = None
            
    def _record_latency(self, latency: float):
        """Record request latency for averaging"""
        self._latency_samples.append(latency)
        if len(self._latency_samples) > self._max_latency_samples:
            self._latency_samples.pop(0)
        self.average_latency = sum(self._latency_samples) / len(self._latency_samples)
        
    async def _make_rpc_call(self, method: str, params: List[Any]) -> Dict[str, Any]:
        """Make an RPC call with error handling"""
        if not self._client:
            await self.connect()
            
        start_time = time.time()
        try:
            # Use httpx directly since solders AsyncClient doesn't support all methods
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.endpoint,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": method,
                        "params": params
                    }
                )
                response.raise_for_status()
                data = response.json()
                
            # Record successful request latency
            elapsed = time.time() - start_time
            self._record_latency(elapsed)
            
            # Parse and validate response
            return self._response_handler.handle_response(data)
            
        except Exception as e:
            elapsed = time.time() - start_time
            self.error_count += 1
            
            # Handle rate limiting
            if "429" in str(e) or "Too many requests" in str(e):
                retry_after = None
                if hasattr(e, 'headers') and 'Retry-After' in e.headers:
                    retry_after = int(e.headers['Retry-After'])
                raise RetryableError(f"Rate limited by {self.endpoint}", retry_after)
                
            # Handle connection errors
            if isinstance(e, (asyncio.TimeoutError, ConnectionError)):
                raise RetryableError(f"Connection error to {self.endpoint}: {str(e)}")
                
            # Handle other errors
            raise RPCError(f"RPC error from {self.endpoint}: {str(e)}")

    async def get_slot(self, commitment: Optional[str] = None) -> int:
        """Get the current slot number"""
        params = []
        if commitment:
            params = [{"commitment": commitment}]
        response = await self._make_rpc_call("getSlot", params)
        return response

    async def get_block(
            self,
            slot: int,
            encoding: Optional[str] = None,
            commitment: Optional[str] = None,
            max_supported_transaction_version: Optional[int] = None
        ) -> Optional[Dict[str, Any]]:
        """Get block information by slot"""
        params = [slot]
        if encoding or commitment or max_supported_transaction_version is not None:
            config = {}
            if encoding:
                config["encoding"] = encoding
            if commitment:
                config["commitment"] = commitment
            if max_supported_transaction_version is not None:
                config["maxSupportedTransactionVersion"] = max_supported_transaction_version
            params.append(config)
            
        response = await self._make_rpc_call("getBlock", params)
        return self._response_handler.validate_block_response(response, slot)

class RetryableError(Exception):
    """Error that can be retried"""
    pass

class RPCError(Exception):
    """Non-retryable RPC error"""
    pass

class SolanaConnectionPool:
    """Pool of Solana RPC clients with basic health monitoring"""
    
    def __init__(self, endpoints: List[str] = DEFAULT_RPC_ENDPOINTS):
        self.endpoints = endpoints
        self._clients: Dict[str, SolanaClient] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        self._healthy_endpoints: Set[str] = set()
        self._rate_limited_until: Dict[str, float] = {}
        
    async def initialize(self) -> None:
        """Initialize by finding working endpoints"""
        if self._initialized and len(self._healthy_endpoints) > 0:
            return
            
        start_time = time.time()
        async with self._lock:
            if self._initialized and len(self._healthy_endpoints) > 0:
                return
                
            # Try endpoints one at a time until we get enough working ones
            for endpoint in self.endpoints:
                if len(self._healthy_endpoints) >= 2:  # We have enough working endpoints
                    break
                    
                try:
                    client = SolanaClient(endpoint)
                    if await client.connect():
                        # Test the connection
                        await client.get_slot()
                        self._clients[endpoint] = client
                        self._healthy_endpoints.add(endpoint)
                        logger.debug(f"Successfully connected to {endpoint}")
                    else:
                        await client.close()
                except Exception as e:
                    logger.debug(f"Failed to connect to {endpoint}: {str(e)}")
                    if endpoint in self._clients:
                        await self._clients[endpoint].close()
                        del self._clients[endpoint]
                        
            if not self._healthy_endpoints:
                raise ConnectionError("Failed to connect to any Solana RPC endpoint")
                
            self._initialized = True
            duration = time.time() - start_time
            logger.info(f"Connection pool initialized in {duration:.2f}s with {len(self._healthy_endpoints)} endpoints")
            
    async def get_client(self) -> SolanaClient:
        """Get the best available client"""
        await self.initialize()
        
        async with self._lock:
            now = time.time()
            available_endpoints = []
            
            # Filter out rate limited endpoints
            for endpoint in self._healthy_endpoints:
                rate_limited_until = self._rate_limited_until.get(endpoint, 0)
                if rate_limited_until <= now:
                    available_endpoints.append(endpoint)
                    
            if not available_endpoints:
                raise ConnectionError("No healthy endpoints available")
                
            # Use endpoint with lowest error count and latency
            best_endpoint = min(
                available_endpoints,
                key=lambda e: (
                    self._clients[e].error_count,
                    self._clients[e].average_latency
                )
            )
            
            client = self._clients[best_endpoint]
            client.last_used = now
            return client
            
    def mark_rate_limited(self, endpoint: str, retry_after: Optional[int] = None):
        """Mark an endpoint as rate limited"""
        now = time.time()
        cooldown = retry_after if retry_after else 60  # Default 60s cooldown
        self._rate_limited_until[endpoint] = now + cooldown
        logger.debug(f"Marked {endpoint} as rate limited for {cooldown}s")
        
    async def close(self):
        """Close all clients"""
        async with self._lock:
            for client in self._clients.values():
                await client.close()
            self._clients.clear()
            self._healthy_endpoints.clear()
            self._initialized = False

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
