"""
Solana RPC Client Module - Handles RPC connections and requests
"""
import asyncio
import logging
import os
import random
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
from httpx import ReadTimeout, ConnectTimeout
from dotenv import load_dotenv

from ..config import (
    HELIUS_API_KEY,
    RATE_CONFIG,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    POOL_SIZE
)

from .solana_rate_limiter import SolanaRateLimiter

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Custom exceptions
class RPCError(Exception):
    """Base class for RPC errors"""
    pass

class RateLimitError(RPCError):
    """Raised when rate limit is exceeded"""
    pass

class RetryableError(RPCError):
    """Base class for errors that can be retried"""
    pass

class NodeBehindError(RetryableError):
    """Raised when node is behind"""
    pass

class NodeUnhealthyError(RetryableError):
    """Raised when node is unhealthy"""
    pass

class MissingBlocksError(RetryableError):
    """Raised when blocks are missing"""
    pass

class SlotSkippedError(RetryableError):
    """Raised when a slot is skipped"""
    pass

# Well-known RPC providers
KNOWN_RPC_PROVIDERS = {
    # Soleco-specific endpoints
    "mainnet.helius-rpc.com": f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}",
    "rpc.ankr.com": "https://rpc.ankr.com/solana",
    "solana.public-rpc.com": "https://solana.public-rpc.com",
}

# Default RPC endpoints to use for fallback
DEFAULT_RPC_ENDPOINTS = [
    f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}",
    "http://145.40.126.143:8899",
    "https://api.devnet.solana.com",
    "http://38.58.176.230:8899",
    "http://147.75.92.135:8899",
    "http://139.178.73.255:8899",
    "http://149-255-37-170.static.hvvc.us:8899",
    "http://84.32.186.110:8899",
    "http://66.45.229.34:8899",
    "http://149.255.37.170:8899",
    "http://144.202.50.238:8899",
    "http://147.28.133.107:8899",
    "http://149.255.37.174:8899",
    "http://141.95.97.47:8899",
    "http://207.148.14.220:8899",
    "http://192.158.239.143:8899",
    "http://37.27.229.67:8899",
    "http://147.75.193.169:8899",
    "http://80.77.161.202:8899",
    "http://80.77.175.84:8899",
    "http://57.129.37.153:8899",
    "http://80.77.161.201:8899",
    "http://216.238.102.89:8899",
    "http://147.75.198.219:8899",
    "http://45.76.3.216:8899",
    "http://18.195.65.66:8899",
    "http://137.220.59.111:8899",
    "http://207.246.119.26:8899",
    "https://api.mainnet-beta.solana.com",
    "http://145.40.64.255:8899",
    "http://80.77.161.207:8899",
    "http://64.176.11.113:8899",
    "http://67.213.115.17:8899",
    "http://149.248.62.208:8899",
    "http://145.40.126.95:8899",
    "http://74.50.65.194:8899",
    "http://74.50.65.226:8899",
    "http://149-255-37-154.static.hvvc.us:8899",
    "http://173.231.14.98:8899",
    "http://107.182.163.194:8899",
]

# Filter out None values and empty strings from endpoints
DEFAULT_RPC_ENDPOINTS = [ep for ep in DEFAULT_RPC_ENDPOINTS if ep]

logger.debug("Solana RPC module initialized with endpoints: %s", DEFAULT_RPC_ENDPOINTS)

# Ensure we have at least one endpoint
if not DEFAULT_RPC_ENDPOINTS:
    DEFAULT_RPC_ENDPOINTS = [f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"]

# Additional fallback endpoints in case the primary ones fail
FALLBACK_RPC_ENDPOINTS = [
    "https://rpc.ankr.com/solana",
    "https://solana.public-rpc.com"
]

class RateLimits:
    """Track rate limit information from response headers"""
    
    def __init__(self):
        self.method_limit = 0
        self.method_remaining = 0
        self.rps_limit = 0
        self.rps_remaining = 0
        self.endpoint_limit = 0
        self.endpoint_remaining = 0
        self.last_update = time.time()
        self.consecutive_failures = 0
        self.cooldown_until = 0
        
    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """Update rate limit info from response headers"""
        try:
            # Parse rate limit headers
            self.method_limit = int(headers.get('x-ratelimit-method-limit', '0'))
            self.method_remaining = int(headers.get('x-ratelimit-method-remaining', '0'))
            self.rps_limit = int(headers.get('x-ratelimit-rps-limit', '0'))
            self.rps_remaining = int(headers.get('x-ratelimit-rps-remaining', '0'))
            
            # Track endpoint health
            self.endpoint_remaining = int(headers.get('x-ratelimit-endpoint-remaining', '0'))
            if self.endpoint_remaining < 0:
                self.consecutive_failures += 1
                if self.consecutive_failures >= 3:
                    # Circuit breaker: cooldown for 30-60 seconds after 3 consecutive failures
                    cooldown = random.uniform(30, 60)
                    self.cooldown_until = time.time() + cooldown
                    logger.warning(f"Circuit breaker triggered: cooling down for {cooldown:.1f}s")
            else:
                self.consecutive_failures = 0
                
            self.last_update = time.time()
            
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Error parsing rate limit headers: {e}")

    def should_throttle(self) -> bool:
        """Check if we should throttle requests based on rate limits"""
        now = time.time()
        
        # Honor circuit breaker cooldown
        if now < self.cooldown_until:
            return True
            
        # Check method and RPS limits
        if self.method_remaining <= 1 or self.rps_remaining <= 1:
            return True
            
        # Add basic rate limiting if headers not available
        if now - self.last_update < 0.1:  # Max 10 RPS as fallback
            return True
            
        return False

    def get_backoff_time(self) -> float:
        """Get the time to back off in seconds"""
        now = time.time()
        
        if now < self.cooldown_until:
            return self.cooldown_until - now
            
        if self.method_remaining <= 1:
            return random.uniform(1.0, 2.0)
            
        if self.rps_remaining <= 1:
            return random.uniform(0.2, 0.5)
            
        return 0.1  # Minimum backoff

class QueueItem:
    """Wrapper class for priority queue items to enable proper comparison"""
    def __init__(self, priority: int, method: str, params: List[Any], future: asyncio.Future):
        self.priority = priority
        self.method = method
        self.params = params
        self.future = future
        self.timestamp = time.time()
        
    def __lt__(self, other):
        if not isinstance(other, QueueItem):
            return NotImplemented
        # First compare by priority (lower number = higher priority)
        if self.priority != other.priority:
            return self.priority < other.priority
        # Then by timestamp (older = higher priority)
        return self.timestamp < other.timestamp

class SolanaClient:
    """Client for interacting with Solana RPC nodes."""
    
    def __init__(
        self,
        endpoint: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        rate_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the Solana RPC client"""
        self.endpoint = endpoint
        self.timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._client = None
        self._latencies: List[float] = []
        self._max_latencies = 100
        self._rate_limiter = SolanaRateLimiter(rate_config or RATE_CONFIG)
        self._last_request_time = 0.0
        self._min_request_interval = 1.0 / (rate_config.get('max_rate', 5.0) if rate_config else 5.0)
        
        logger.debug(f"Initialized SolanaClient for endpoint: {endpoint}")

    async def connect(self) -> None:
        """Initialize the HTTP client and test the connection."""
        try:
            if self._client:
                await self._client.aclose()
            
            # Create new client with limits
            limits = httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0
            )
            
            # Initialize client with connection pooling
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=limits,
                http2=True
            )
            
            # Test connection with a light request
            start = time.time()
            result = await self._make_rpc_call("getHealth", [])
            latency = time.time() - start
            
            if result.get("result") != "ok":
                raise NodeUnhealthyError(f"Node health check failed: {result}")
            
            self._record_latency(latency)
            # Logging moved to connection pool to avoid duplication
            
        except Exception as e:
            if self._client:
                await self._client.aclose()
                self._client = None
            raise ConnectionError(f"Failed to connect to {self.endpoint}: {str(e)}")

    async def close(self) -> None:
        """Close the client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug(f"Closed connection to {self.endpoint}")

    async def _handle_request_error(self, error_type: str):
        """Handle request errors by updating error tracking"""
        self.error_count += 1
        self.last_error = error_type
        self._cooldown_until = time.time() + self._backoff_time
        self._backoff_time = min(self._backoff_time * 2, 60.0)  # Max 60 second backoff

    def _record_latency(self, latency: float):
        """Record latency measurement"""
        self._latencies.append(latency)
        if len(self._latencies) > self._max_latencies:
            self._latencies = self._latencies[-self._max_latencies:]

    async def _make_rpc_call(self, method: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Make an RPC call with rate limiting and retries."""
        if not self._client:
            await self.connect()

        # Ensure minimum time between requests
        now = time.time()
        time_since_last = now - self._last_request_time
        if time_since_last < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last)

        # Check rate limiter
        if not await self._rate_limiter.acquire():
            logger.warning(f"Rate limit exceeded for {method}, backing off")
            raise RateLimitError("Rate limit exceeded")

        start_time = time.time()
        try:
            # Prepare request
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": method,
                "params": params or []
            }

            # Log the request details for debugging
            logger.debug(f"Making RPC request to {self.endpoint}: {method} with params {params}")

            # Make request with timeout
            response = await self._client.post(
                self.endpoint,
                json=request,
                timeout=self.timeout
            )
            
            # Update rate limiter and latency tracking
            self._last_request_time = time.time()
            latency = self._last_request_time - start_time
            self._update_latency(latency)
            
            # Parse response
            result = response.json()
            
            if "error" in result:
                error = result["error"]
                error_code = error.get("code")
                
                if error_code == 429:
                    self._rate_limiter.update_rate(False)
                    raise RateLimitError(f"Rate limit exceeded: {result}")
                elif error_code == -32015:  # Transaction version error
                    raise RetryableError(f"Transaction version error: {result}")
                elif error_code == -32007:  # Skipped slot error
                    raise SlotSkippedError(f"Slot skipped or missing: {result}")
                elif error_code == -32009:  # Node is behind
                    raise NodeBehindError(f"Node is behind: {result}")
                elif error_code == -32016:  # Node is unhealthy
                    raise NodeUnhealthyError(f"Node is unhealthy: {result}")
                else:
                    raise RPCError(f"RPC error: {result}")
            
            self._rate_limiter.update_rate(True)
            return result

        except (ReadTimeout, ConnectTimeout) as e:
            logger.warning(f"Timeout error in {method}: {str(e)}")
            self._rate_limiter.update_rate(False)
            # Close and recreate client on timeout
            if self._client:
                await self._client.aclose()
                self._client = None
            raise RetryableError(f"Request timed out: {str(e)}")
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in {method}: {str(e)}")
            self._rate_limiter.update_rate(False)
            raise RetryableError(f"HTTP error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error in {method}: {str(e)}")
            self._rate_limiter.update_rate(False)
            raise

    def _update_latency(self, latency: float):
        """Update latency tracking."""
        self._latencies.append(latency)
        if len(self._latencies) > self._max_latencies:
            self._latencies.pop(0)

    async def get_transaction(
        self,
        signature: str,
        encoding: Optional[str] = None,
        commitment: Optional[str] = None,
        max_supported_transaction_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get transaction details by signature"""
        try:
            # Try native client first for better performance
            native_client = SolanaAsyncClient(self.endpoint)
            result = await native_client.get_transaction(
                Signature.from_string(signature),
                commitment=commitment,
                max_supported_transaction_version=max_supported_transaction_version
            )
            await native_client.close()
            if result is not None:
                return result.value
        except BaseException as e:
            logger.error(f"Native client failed for transaction {signature}: {str(e)}")
            # Fallback to custom implementation
            return await self._make_rpc_call(
                "getTransaction",
                [
                    str(signature),
                    {"commitment": commitment} if commitment else {},
                    {"maxSupportedTransactionVersion": max_supported_transaction_version} if max_supported_transaction_version else {}
                ]
            )

    async def get_block(
        self,
        slot: int,
        opts: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get block information."""
        try:
            # Prepare parameters
            params = [slot]
            if opts:
                params.append(opts)
            
            # Make RPC call
            return await self._make_rpc_call("getBlock", params)
            
        except SlotSkippedError as e:
            logger.warning(f"Slot {slot} was skipped, will try next slot")
            raise RetryableError(str(e))
            
        except Exception as e:
            logger.error(f"Error getting block {slot}: {str(e)}")
            raise

    async def get_slot(self, commitment: Optional[str] = None) -> int:
        """Get the current slot number."""
        try:
            params = {"commitment": commitment} if commitment else None
            result = await self._make_rpc_call("getSlot", [params] if params else [])
            
            if isinstance(result, int):
                return result
            elif "result" in result:
                return int(result["result"])
            else:
                raise RPCError(f"Invalid getSlot response format: {result}")
                
        except Exception as e:
            logger.error(f"Error getting slot: {str(e)}")
            raise

    async def get_signatures_for_address(
        self,
        address: str,
        before: Optional[str] = None,
        until: Optional[str] = None,
        limit: Optional[int] = None,
        commitment: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get signatures for address"""
        params = [address]
        
        config = {}
        if before:
            config["before"] = before
        if until:
            config["until"] = until
        if limit:
            config["limit"] = limit
        if commitment:
            config["commitment"] = commitment
            
        if config:
            params.append(config)
            
        try:
            result = await self._make_rpc_call("getSignaturesForAddress", params)
            return result or []
        except BaseException as e:
            logger.error(f"Error getting signatures for address {address}: {e}")
            return []

    async def get_latest_blockhash(self, commitment: Optional[str] = None) -> Dict[str, Any]:
        """Get the latest blockhash"""
        try:
            result = await self._make_rpc_call(
                "getLatestBlockhash",
                [{"commitment": commitment} if commitment else {}]
            )
            return result
        except BaseException as e:
            logger.error(f"Error getting latest blockhash: {e}")
            return {}

    async def get_account_info(self, address, *args, **kwargs):
        """
        Get information about an account.
        
        Args:
            address: The account address
            
        Returns:
            Dict: Account information
        """
        params = [str(address)]
        if args:
            params.extend(args)
        return await self._make_rpc_call("getAccountInfo", params)

    async def get_cluster_nodes(self, *args, **kwargs):
        """
        Get information about the cluster nodes.
        
        Returns:
            Dict: Information about cluster nodes
        """
        return await self._make_rpc_call("getClusterNodes", args or [])

    async def get_epoch_info(self, *args, **kwargs):
        """
        Get information about the current epoch.
        
        Returns:
            Dict: Information about the current epoch
        """
        return await self._make_rpc_call("getEpochInfo", args or [])

    async def get_block_production(self, *args, **kwargs):
        """
        Get block production information.
        
        Returns:
            Dict: Block production information
        """
        return await self._make_rpc_call("getBlockProduction", args or [])

    async def get_recent_performance_samples(self, *args, **kwargs):
        """
        Get recent performance samples.
        
        Returns:
            Dict: Recent performance samples
        """
        return await self._make_rpc_call("getRecentPerformanceSamples", args or [])

    async def get_version(self):
        """
        Returns the current Solana version running on the node.
        """
        return await self._make_rpc_call("getVersion", [])

    async def get_vote_accounts(self) -> Dict[str, Any]:
        """Get information about all vote accounts."""
        try:
            result = await self._make_rpc_call("getVoteAccounts", [])
            if "result" not in result:
                raise RPCError("Invalid response from getVoteAccounts")
            return result["result"]
        except Exception as e:
            logger.error(f"Error getting vote accounts: {str(e)}")
            raise

    async def get_block_height(self) -> int:
        """Get the current block height."""
        try:
            result = await self._make_rpc_call("getBlockHeight", [])
            return result.get("result", 0)
        except Exception as e:
            logger.error(f"Error getting block height: {str(e)}")
            raise

    async def simulate_transaction(self, transaction, *args, **kwargs):
        """
        Simulate a transaction.
        
        Args:
            transaction: The transaction to simulate
            
        Returns:
            Dict: Simulation results
        """
        params = [str(transaction)]
        if args:
            params.extend(args)
        return await self._make_rpc_call("simulateTransaction", params)

    @property
    def average_latency(self) -> float:
        if not self._latencies:
            return float('inf')
        return sum(self._latencies) / len(self._latencies)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

class SolanaConnectionPool:
    """Pool of Solana RPC clients with enhanced connection management."""
    
    def __init__(
            self,
            endpoints: List[str] = DEFAULT_RPC_ENDPOINTS,
            pool_size: int = POOL_SIZE,
            max_retries: int = DEFAULT_MAX_RETRIES,
            retry_delay: float = DEFAULT_RETRY_DELAY,
            timeout: float = DEFAULT_TIMEOUT
        ):
        """Initialize the connection pool."""
        # Create a new list to avoid modifying the default parameter
        endpoints = list(endpoints)
        
        # Always ensure Helius is the first endpoint if available
        helius_endpoint = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
        
        # Remove any existing Helius endpoints to avoid duplicates
        endpoints = [ep for ep in endpoints if "helius-rpc.com" not in ep]
        
        # Add Helius as the first endpoint if API key is available
        if HELIUS_API_KEY:
            endpoints = [helius_endpoint] + endpoints
            
        # Add our top performing endpoints as fallbacks
        top_performing_endpoints = [
            "http://66.45.229.34:8899",     # 1.929s response time
            "http://145.40.126.95:8899",    # 1.984s response time
            "http://74.50.65.194:8899",     # 2.294s response time
            "http://207.148.14.220:8899",   # 2.316s response time
            "http://149-255-37-170.static.hvvc.us:8899",  # 3.307s response time
            "http://74.50.65.226:8899",     # 3.577s response time
            "http://149-255-37-154.static.hvvc.us:8899",  # 4.301s response time
            "http://173.231.14.98:8899",    # 1.459s response time
            "http://107.182.163.194:8899",  # 1.671s response time
            "http://66.45.229.34:8899",     # 2.035s response time
            "http://38.58.176.230:8899",    # 2.738s response time
            "http://147.75.198.219:8899",   # 3.462s response time
        ]
        
        # Add top performing endpoints if they're not already in the list
        for endpoint in top_performing_endpoints:
            if endpoint not in endpoints:
                endpoints.append(endpoint)
                
        self.endpoints = endpoints
        self.pool_size = min(pool_size, len(endpoints))  # Don't exceed available endpoints
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # Initialize empty pool
        self._pool: List[Tuple[SolanaClient, int]] = []  # (client, failure_count)
        self._pool_lock = asyncio.Lock()
        self._initialized = False
        self._current_index = -1
        
        # Track endpoint performance
        self.endpoint_stats = {}  # endpoint -> {success_count, failure_count, avg_latency}
        self.endpoint_failures = {}  # endpoint -> current failure count
        
        logger.debug(f"Created connection pool with {len(endpoints)} available endpoints")

    async def initialize(self, force: bool = False) -> None:
        """Initialize the connection pool by creating initial connections."""
        if self._initialized and not force:
            return

        async with self._pool_lock:
            if self._initialized and not force:  # Double check under lock
                return
                
            # Clear existing pool
            self._pool = []
            self._current_index = -1
            
            logger.info(f"Initializing connection pool with endpoints: {self.endpoints}")
            
            # Try to initialize connections
            successful_connections = 0
            for endpoint in self.endpoints:
                try:
                    client = SolanaClient(
                        endpoint,
                        timeout=self.timeout,
                        max_retries=self.max_retries,
                        retry_delay=self.retry_delay
                    )
                    await client.connect()
                    self._pool.append((client, 0))  # (client, failure_count)
                    successful_connections += 1
                    logger.info(f"Successfully connected to endpoint: {endpoint}")
                    
                    if successful_connections >= self.pool_size:
                        logger.info(f"Reached pool size limit of {self.pool_size}, stopping initialization")
                        break
                        
                except Exception as e:
                    logger.error(f"Error creating client for {endpoint}: {str(e)}")
                    continue
            
            if not self._pool:
                error_msg = "Failed to initialize any connections in pool"
                logger.error(error_msg)
                raise ConnectionError(error_msg)
                
            self._initialized = True
            logger.info(f"Connection pool initialized with {len(self._pool)} clients")

    async def close(self):
        """Close all clients and cleanup resources"""
        async with self._pool_lock:
            for client, _ in self._pool:
                await client.close()
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

    async def get_client(self) -> SolanaClient:
        """Get a healthy client from the pool using round-robin with failure tracking."""
        async with self._pool_lock:
            if not self._initialized:
                await self.initialize()
            
            # If pool is empty, try to reinitialize
            if not self._pool:
                logger.warning("Connection pool is empty, attempting to reinitialize")
                await self.initialize()
                if not self._pool:
                    raise ConnectionError("Failed to initialize any connections in pool")
            
            # Try clients in order of least failures first
            sorted_pool = sorted(self._pool, key=lambda x: x[1])  # Sort by failure count
            
            # Try each client until we find a healthy one
            for i, (client, failures) in enumerate(sorted_pool):
                # Skip clients with too many failures
                if failures > 5:  # Consider a threshold for "too many" failures
                    continue
                    
                try:
                    # Update the current index to match the client we're returning
                    for j, (c, _) in enumerate(self._pool):
                        if c.endpoint == client.endpoint:
                            self._current_index = j
                            break
                            
                    # Update stats for this endpoint
                    if client.endpoint not in self.endpoint_stats:
                        self.endpoint_stats[client.endpoint] = {
                            "success_count": 0,
                            "failure_count": 0,
                            "avg_latency": 0,
                            "success_rate": 0
                        }
                    
                    return client
                except Exception as e:
                    logger.error(f"Error checking client health: {str(e)}")
                    continue
            
            # If we get here, all clients have too many failures
            # Reset failure counts and try again
            self._pool = [(client, 0) for client, _ in self._pool]
            
            # Round-robin as a fallback
            self._current_index = (self._current_index + 1) % len(self._pool)
            client, failures = self._pool[self._current_index]
            
            return client

    async def acquire(self) -> 'ClientContextManager':
        """
        Acquire a client from the pool.
        
        Returns:
            ClientContextManager: A context manager for a client from the pool
            
        Usage:
            async with pool.acquire() as client:
                result = await client.get_block(123)
        """
        class ClientContextManager:
            def __init__(self, pool, client):
                self.pool = pool
                self.client = client
                self.start_time = None
                self.success = True
                
            async def __aenter__(self):
                self.start_time = time.time()
                return self.client
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                latency = time.time() - self.start_time if self.start_time else None
                self.success = exc_type is None
                await self.pool.release(self.client, self.success, latency)
                
        client = await self.get_client()
        return ClientContextManager(self, client)
    
    async def release(self, client: SolanaClient, success: bool = True, latency: float = None):
        """
        Release a client back to the pool and update its stats.
        
        Args:
            client: The client to release
            success: Whether the operation with this client was successful
            latency: The latency of the operation in seconds
        """
        # Handle case where client is a ClientContextManager
        if hasattr(client, 'client'):
            client = client.client
            
        async with self._pool_lock:
            # Find the client in the pool
            for i, (c, failures) in enumerate(self._pool):
                if c.endpoint == client.endpoint:
                    # Update failure count
                    if success:
                        self._pool[i] = (c, max(0, failures - 1))  # Decrease failure count on success
                        
                        # Update endpoint stats
                        if client.endpoint in self.endpoint_stats:
                            stats = self.endpoint_stats[client.endpoint]
                            stats["success_count"] += 1
                            
                            # Update average latency
                            if latency is not None:
                                avg_latency = stats["avg_latency"]
                                total_ops = stats["success_count"] + stats["failure_count"]
                                stats["avg_latency"] = (avg_latency * (total_ops - 1) + latency) / total_ops
                    else:
                        self._pool[i] = (c, failures + 1)  # Increase failure count on failure
                        
                        # Update endpoint stats
                        if client.endpoint in self.endpoint_stats:
                            stats = self.endpoint_stats[client.endpoint]
                            stats["failure_count"] += 1
                    
                    break

    async def get_latest_block(self) -> int:
        """
        Get the latest finalized block height.

        Returns:
            int: Latest block height

        Raises:
            RPCError: If unable to get block height after retries
        """
        client = await self.get_client()
        if not client:
            raise RPCError("No available RPC clients")

        try:
            result = await client._make_rpc_call(
                "getSlot",
                [{"commitment": "finalized"}]
            )
            
            if isinstance(result, int):
                return result
            elif "result" in result:
                return int(result["result"])
            else:
                raise RPCError(f"Invalid block height response format: {result}")
                
        except Exception as e:
            raise RPCError(f"Failed to get latest block: {str(e)}") from e

    async def get_endpoint_stats(self) -> Dict[str, Any]:
        """
        Get statistics about endpoint performance.
        
        Returns:
            Dict: Statistics about each endpoint
        """
        async with self._pool_lock:
            stats = {}
            
            # Add stats for endpoints in the pool
            for client, failures in self._pool:
                endpoint = client.endpoint
                if endpoint in self.endpoint_stats:
                    endpoint_stats = self.endpoint_stats[endpoint].copy()
                    endpoint_stats["current_failures"] = failures
                    endpoint_stats["in_pool"] = True
                    
                    # Calculate success rate
                    total = endpoint_stats["success_count"] + endpoint_stats["failure_count"]
                    if total > 0:
                        endpoint_stats["success_rate"] = endpoint_stats["success_count"] / total * 100
                    else:
                        endpoint_stats["success_rate"] = 0
                        
                    stats[endpoint] = endpoint_stats
                else:
                    stats[endpoint] = {
                        "success_count": 0,
                        "failure_count": 0,
                        "avg_latency": 0,
                        "current_failures": failures,
                        "in_pool": True,
                        "success_rate": 0
                    }
            
            # Add stats for endpoints not in the pool
            for endpoint, endpoint_stats in self.endpoint_stats.items():
                if endpoint not in stats:
                    endpoint_stats = endpoint_stats.copy()
                    endpoint_stats["in_pool"] = False
                    endpoint_stats["current_failures"] = "N/A"
                    
                    # Calculate success rate
                    total = endpoint_stats["success_count"] + endpoint_stats["failure_count"]
                    if total > 0:
                        endpoint_stats["success_rate"] = endpoint_stats["success_count"] / total * 100
                    else:
                        endpoint_stats["success_rate"] = 0
                        
                    stats[endpoint] = endpoint_stats
            
            return stats

    async def update_endpoint_stats(self, endpoint: str, success: bool, latency: float = 0.0) -> None:
        """
        Update statistics for a specific RPC endpoint.
        
        Args:
            endpoint: The endpoint URL
            success: Whether the operation was successful
            latency: The latency of the operation (if successful)
        """
        if endpoint in self.endpoint_stats:
            if success:
                self.endpoint_stats[endpoint]["success_count"] = self.endpoint_stats[endpoint].get("success_count", 0) + 1
                # Update latency using exponential moving average
                alpha = 0.3  # Weight for new value
                self.endpoint_stats[endpoint]["avg_latency"] = alpha * latency + (1 - alpha) * self.endpoint_stats[endpoint].get("avg_latency", 0)
                # Reset current failures
                self.endpoint_failures[endpoint] = 0
            else:
                self.endpoint_stats[endpoint]["failure_count"] = self.endpoint_stats[endpoint].get("failure_count", 0) + 1
                self.endpoint_stats[endpoint]["current_failures"] = self.endpoint_stats[endpoint].get("current_failures", 0) + 1
        else:
            self.endpoint_stats[endpoint] = {
                "success_count": 1 if success else 0,
                "failure_count": 0 if success else 1,
                "avg_latency": latency if success else 0,
                "current_failures": 0 if success else 1
            }
    
    async def sort_endpoints_by_performance(self) -> List[str]:
        """
        Sort endpoints based on performance metrics.
        
        This method prioritizes endpoints based on:
        1. Success rate (higher is better)
        2. Average latency (lower is better)
        3. Current failure count (lower is better)
        
        Returns:
            List[str]: Sorted list of endpoints
        """
        # Start with the Helius endpoint if it exists
        helius_endpoint = next((ep for ep in self.endpoints if "helius-rpc.com" in ep), None)
        sorted_endpoints = [helius_endpoint] if helius_endpoint else []
        
        # Get remaining endpoints
        remaining_endpoints = [ep for ep in self.endpoints if ep not in sorted_endpoints]
        
        # Sort remaining endpoints by performance metrics
        endpoint_scores = []
        for endpoint in remaining_endpoints:
            stats = self.endpoint_stats.get(endpoint, {
                "success_count": 0,
                "failure_count": 0,
                "avg_latency": float('inf'),
                "current_failures": 0,
                "in_pool": False,
                "success_rate": 0
            })
            
            total_requests = stats["success_count"] + stats["failure_count"]
            success_rate = stats["success_count"] / total_requests if total_requests > 0 else 0
            avg_latency = stats["avg_latency"] if stats["avg_latency"] > 0 else float('inf')
            current_failures = stats.get("current_failures", 0)
            
            # Calculate score (higher is better)
            # Prioritize success rate, then latency, then failure count
            score = (success_rate * 100) - (avg_latency * 10) - (current_failures * 5)
            
            endpoint_scores.append((endpoint, score))
        
        # Sort by score (higher is better)
        endpoint_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Add sorted endpoints to the list
        sorted_endpoints.extend([ep for ep, _ in endpoint_scores])
        
        # Log the sorted endpoints
        logger.debug(f"Sorted endpoints by performance: {sorted_endpoints[:5]}...")
        
        return sorted_endpoints

    async def update_endpoints(self, new_endpoints: List[str]) -> None:
        """
        Update the pool with a new list of endpoints.
        
        This method will:
        1. Add any new endpoints to the pool
        2. Remove endpoints that are no longer in the list
        3. Sort endpoints by performance
        4. Re-initialize the pool with the sorted endpoints
        
        Args:
            new_endpoints: The new list of endpoints to use
        """
        logger.info(f"Updating connection pool with {len(new_endpoints)} endpoints")
        
        # Store current endpoints for comparison
        old_endpoints = self.endpoints.copy()
        
        # Update the endpoints list
        self.endpoints = new_endpoints.copy()
        
        # Sort endpoints by performance
        sorted_endpoints = await self.sort_endpoints_by_performance()
        self.endpoints = sorted_endpoints
        
        # Adjust pool size if needed
        self.pool_size = min(self.pool_size, len(self.endpoints))
        
        # Re-initialize the pool
        await self.initialize(force=True)
        
        # Log changes
        added = [ep for ep in new_endpoints if ep not in old_endpoints]
        removed = [ep for ep in old_endpoints if ep not in new_endpoints]
        
        if added:
            logger.info(f"Added {len(added)} new endpoints to the pool")
            for ep in added[:5]:  # Log first 5 for brevity
                logger.debug(f"  Added: {ep}")
            if len(added) > 5:
                logger.debug(f"  ... and {len(added) - 5} more")
                
        if removed:
            logger.info(f"Removed {len(removed)} endpoints from the pool")
            for ep in removed[:5]:  # Log first 5 for brevity
                logger.debug(f"  Removed: {ep}")
            if len(removed) > 5:
                logger.debug(f"  ... and {len(removed) - 5} more")

    async def check_endpoint_health(self, endpoint: str) -> bool:
        """
        Check the health of an endpoint and update its performance metrics.
        
        Args:
            endpoint: The endpoint to check
            
        Returns:
            True if the endpoint is healthy, False otherwise
        """
        try:
            # Create a temporary client for this endpoint
            client = SolanaClient(endpoint)
            
            # Record start time
            start_time = time.time()
            
            # Check health by getting version (a lightweight RPC call)
            version_result = await client.get_version()
            
            # Calculate latency
            latency = time.time() - start_time
            
            # Update endpoint stats
            if endpoint not in self.endpoint_stats:
                self.endpoint_stats[endpoint] = {
                    "success_count": 0,
                    "failure_count": 0,
                    "avg_latency": 0,
                    "success_rate": 0
                }
            
            stats = self.endpoint_stats[endpoint]
            stats["success_count"] += 1
            
            # Update average latency using exponential moving average
            alpha = 0.3  # Weight for new value
            stats["avg_latency"] = alpha * latency + (1 - alpha) * stats["avg_latency"]
            
            # Update success rate
            total_requests = stats["success_count"] + stats["failure_count"]
            stats["success_rate"] = stats["success_count"] / total_requests if total_requests > 0 else 0
            
            # Reset current failures
            self.endpoint_failures[endpoint] = 0
            
            logger.info(f"Endpoint health check successful for {endpoint} - Latency: {latency:.3f}s")
            return True
            
        except Exception as e:
            # Update endpoint stats
            if endpoint not in self.endpoint_stats:
                self.endpoint_stats[endpoint] = {
                    "success_count": 0,
                    "failure_count": 0,
                    "avg_latency": 0,
                    "success_rate": 0
                }
            
            stats = self.endpoint_stats[endpoint]
            stats["failure_count"] += 1
            
            # Update success rate
            total_requests = stats["success_count"] + stats["failure_count"]
            stats["success_rate"] = stats["success_count"] / total_requests if total_requests > 0 else 0
            
            # Increment failure count
            self.endpoint_failures[endpoint] = self.endpoint_failures.get(endpoint, 0) + 1
            
            logger.warning(f"Endpoint health check failed for {endpoint}: {str(e)}")
            return False

    async def check_all_endpoints_health(self) -> None:
        """
        Check the health of all endpoints in the pool and update their performance metrics.
        Re-sorts the endpoints based on updated metrics.
        """
        logger.info(f"Checking health of all {len(self.endpoints)} endpoints in the pool")
        
        # Check health of all endpoints concurrently
        tasks = []
        for endpoint in self.endpoints:
            task = asyncio.create_task(self.check_endpoint_health(endpoint))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count healthy endpoints
        healthy_count = sum(1 for result in results if result is True)
        logger.info(f"Health check completed: {healthy_count}/{len(self.endpoints)} endpoints are healthy")
        
        # Re-sort endpoints based on updated metrics
        sorted_endpoints = await self.sort_endpoints_by_performance()
        
        # Update endpoints
        self.endpoints = sorted_endpoints
        
        # Log top 5 endpoints
        logger.info("Top 5 endpoints after health check:")
        for i, endpoint in enumerate(self.endpoints[:5]):
            stats = self.endpoint_stats.get(endpoint, {})
            logger.info(f"  {i+1}. {endpoint} - " +
                       f"Success Rate: {stats.get('success_rate', 0):.2f}, " +
                       f"Avg Latency: {stats.get('avg_latency', 0):.3f}s, " +
                       f"Failures: {self.endpoint_failures.get(endpoint, 0)}")

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the connection pool.
        
        Returns:
            Dict with statistics about the connection pool
        """
        async with self._pool_lock:
            # Count active and available clients
            active_clients = len([c for c in self._pool if c[1] == 0])
            available_clients = len([c for c in self._pool if c[1] > 0])
            
            # Calculate success rates and sort endpoints by performance
            performers = []
            for endpoint, stats in self.endpoint_stats.items():
                total_requests = stats.get("success_count", 0) + stats.get("failure_count", 0)
                if total_requests > 0:
                    success_rate = stats.get("success_count", 0) / total_requests
                else:
                    success_rate = 0
                
                performers.append({
                    "endpoint": endpoint,
                    "success_rate": success_rate,
                    "avg_latency": stats.get("avg_latency", 0),
                    "success_count": stats.get("success_count", 0),
                    "failure_count": stats.get("failure_count", 0),
                    "current_failures": stats.get("current_failures", 0),
                    "in_pool": endpoint in self.endpoints
                })
            
            # Sort by success rate (higher is better) and then by latency (lower is better)
            sorted_performers = sorted(
                performers,
                key=lambda p: (-p["success_rate"], p["avg_latency"])
            )
            
            # Filter out performers with no requests
            filtered_performers = [p for p in sorted_performers if p["success_count"] + p["failure_count"] > 0]
            
            return {
                "active_clients": active_clients,
                "available_clients": available_clients,
                "total_endpoints": len(self.endpoints),
                "top_performers": filtered_performers
            }

    def get_rpc_stats(self):
        """
        Get detailed statistics about RPC endpoint performance.
        
        Returns:
            Dict: Detailed statistics about each endpoint and summary metrics
        """
        # Get stats for each endpoint
        stats = {}
        total_success = 0
        total_failures = 0
        
        for url in self.endpoint_stats:
            endpoint_stats = self.endpoint_stats[url]
            success_count = endpoint_stats.get("success_count", 0)
            failure_count = endpoint_stats.get("failure_count", 0)
            
            # Calculate success rate
            total_requests = success_count + failure_count
            success_rate = success_count / max(total_requests, 1) * 100
            
            # Update totals
            total_success += success_count
            total_failures += failure_count
            
            # Add to stats
            stats[url] = {
                "success_count": success_count,
                "failure_count": failure_count,
                "avg_latency": endpoint_stats.get("avg_latency", 0),
                "current_failures": endpoint_stats.get("current_failures", 0),
                "in_pool": url in [client.endpoint for client, _ in self._pool],
                "success_rate": success_rate
            }
        
        # Get top performers
        top_performers = []
        for url, data in stats.items():
            if data["success_count"] > 0:
                top_performers.append({
                    "endpoint": url,
                    "avg_latency": data["avg_latency"],
                    "success_rate": data["success_rate"],
                    "success_count": data["success_count"],
                    "failure_count": data["failure_count"]
                })
        
        # Sort by success rate (desc) and latency (asc)
        top_performers.sort(key=lambda x: (-x["success_rate"], x["avg_latency"]))
        
        # Take top 5
        top_performers = top_performers[:5]
        
        return {
            "stats": stats,
            "summary": {
                "total_endpoints": len(stats),
                "endpoints_in_pool": len(self._pool),
                "total_requests": total_success + total_failures,
                "total_successes": total_success,
                "total_failures": total_failures,
                "overall_success_rate": total_success / max(total_success + total_failures, 1) * 100
            },
            "top_performers": top_performers
        }

    def get_filtered_rpc_stats(self):
        """
        Get detailed statistics about RPC endpoint performance, excluding Helius endpoints.
        
        Returns:
            Dict: Detailed statistics about each endpoint and summary metrics, with Helius endpoints filtered out
        """
        # Get the full stats first
        full_stats = self.get_rpc_stats()
        
        # Filter out Helius endpoints from stats
        filtered_stats = {}
        for url, stat in full_stats.get("stats", {}).items():
            if "helius" not in url.lower():
                filtered_stats[url] = stat
        
        # Make sure we include all non-Helius endpoints in the pool, even if they haven't been used yet
        for endpoint in self.endpoints:
            if "helius" not in endpoint.lower() and endpoint not in filtered_stats:
                filtered_stats[endpoint] = {
                    "success_count": 0,
                    "failure_count": 0,
                    "avg_latency": 0,
                    "current_failures": 0,
                    "in_pool": endpoint in [client.endpoint for client, _ in self._pool],
                    "success_rate": 0
                }
        
        # Filter top performers to exclude Helius
        filtered_performers = []
        for performer in full_stats.get("top_performers", []):
            if "helius" not in performer.get("endpoint", "").lower():
                filtered_performers.append(performer)
        
        # If we have no top performers after filtering, try to get some from the endpoints
        if not filtered_performers and filtered_stats:
            # Convert stats dict to list of objects with endpoint info
            endpoints = [
                {
                    "endpoint": url,
                    "avg_latency": data.get("avg_latency", 0),
                    "success_rate": data.get("success_rate", 0),
                    "success_count": data.get("success_count", 0),
                    "failure_count": data.get("failure_count", 0)
                }
                for url, data in filtered_stats.items()
                if data.get("success_count", 0) > 0
            ]
            
            # Sort by success rate (desc) and latency (asc)
            endpoints.sort(key=lambda x: (-x["success_rate"], x["avg_latency"]))
            
            # Take top 5
            filtered_performers = endpoints[:5]
        
        # Update summary to reflect filtered stats
        total_success = sum(stat.get("success_count", 0) for stat in filtered_stats.values())
        total_failures = sum(stat.get("failure_count", 0) for stat in filtered_stats.values())
        active_endpoints = sum(1 for stat in filtered_stats.values() if stat.get("success_count", 0) > 0)
        latencies = [stat.get("avg_latency", 0) for stat in filtered_stats.values() if stat.get("success_count", 0) > 0]
        avg_latency = sum(latencies) / max(len(latencies), 1) if latencies else 0
        
        return {
            "stats": filtered_stats,
            "summary": {
                "total_endpoints": len(filtered_stats),
                "active_endpoints": active_endpoints,
                "average_latency": round(avg_latency, 3),
                "total_success": total_success,
                "total_failures": total_failures,
                "overall_success_rate": round(total_success / max(total_success + total_failures, 1) * 100, 2)
            },
            "top_performers": filtered_performers
        }

async def get_connection_pool() -> SolanaConnectionPool:
    """Get or create a shared connection pool."""
    global _connection_pool
    
    if _connection_pool is None:
        async with _pool_lock:
            if _connection_pool is None:  # Double-check under lock
                # Create new pool with default configuration
                _connection_pool = SolanaConnectionPool(
                    endpoints=DEFAULT_RPC_ENDPOINTS,
                    pool_size=POOL_SIZE,
                    max_retries=DEFAULT_MAX_RETRIES,
                    retry_delay=DEFAULT_RETRY_DELAY,
                    timeout=DEFAULT_TIMEOUT
                )
                await _connection_pool.initialize()
                logger.info("Created and initialized new connection pool")
    
    return _connection_pool

async def create_robust_client() -> SolanaClient:
    """
    Create a Solana RPC client with robust configuration and full method support
    
    Returns:
        SolanaClient: Our custom Solana RPC client
    """
    try:
        # Get the connection pool
        pool = await get_connection_pool()
        
        # Get a client from the pool
        client = await pool.get_client()
        if not client:
            raise ConnectionError("No healthy Solana RPC clients available")
            
        logger.info(f"Successfully connected to Solana RPC at {client.endpoint}")
        return client
        
    except BaseException as e:
        logger.error(f"Error creating Solana client: {str(e)}")
        raise

_connection_pool: Optional[SolanaConnectionPool] = None
_pool_lock = asyncio.Lock()
