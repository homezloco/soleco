"""
Solana RPC client for interacting with the Solana blockchain.
"""
import asyncio
import json
import logging
import random
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

import aiohttp
from solders.pubkey import Pubkey

from .solana_rate_limiter import SolanaRateLimiter
from .solana_types import EndpointConfig
from .solana_rpc_constants import DEFAULT_RPC_ENDPOINTS
from .solana_error import RetryableError, MethodNotSupportedError, RateLimitError, SlotSkippedError, NodeBehindError, NodeUnhealthyError, RPCError, NoClientsAvailableError
from .solana_ssl_config import should_bypass_ssl_verification
from app.config import HELIUS_API_KEY

logger = logging.getLogger(__name__)

# Default configuration for endpoints
DEFAULT_ENDPOINT_CONFIG = EndpointConfig(
    url="",
    requests_per_second=40.0,
    burst_limit=80,
    max_retries=3,
    retry_delay=1.0
)

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
            
        return 0.0

class SolanaClient:
    """
    Solana RPC client for making RPC calls to a Solana node.
    
    This client handles rate limiting, retries, and error handling.
    """
    
    def __init__(
        self,
        endpoint: str,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        ssl_verify: bool = True,
        connector_args: Optional[Dict[str, Any]] = None,
        rate_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the Solana RPC client"""
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.ssl_verify = ssl_verify
        self._client = None
        self._connector = None
        self._closed = True  # Initialize as closed
        self._latencies: List[float] = []
        self._max_latencies = 100
        self._connector_args = connector_args or {}
        
        # Check if endpoint is in SSL bypass list
        self._ssl_bypass = should_bypass_ssl_verification(endpoint)
        
        # Create a default endpoint config if none provided
        if not rate_config:
            rate_config = {
                "requests_per_second": 40.0,
                "burst_limit": 80
            }
            
        self._rate_limiter = SolanaRateLimiter(rate_config)
        self._last_request_time = 0.0
        self._min_request_interval = 1.0 / rate_config.get("requests_per_second", 5.0)
        
        logger.debug(f"Initialized SolanaClient for endpoint: {endpoint}")
    
    async def connect(self):
        """Connect to the Solana node"""
        if self._closed:
            # Set up connector with appropriate SSL settings
            connector_args = self._connector_args or {}
            
            # Handle SSL verification
            if not self.ssl_verify and self.endpoint.startswith("https"):
                connector_args["ssl"] = False
            
            # Create connector with appropriate settings
            self._connector = aiohttp.TCPConnector(**connector_args)
            
            # Create new client session with appropriate timeouts
            self._client = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=self.timeout,
                    connect=min(5.0, self.timeout / 2),  # Shorter connect timeout
                    sock_connect=min(5.0, self.timeout / 2),  # Shorter socket connect timeout
                    sock_read=self.timeout  # Keep the full timeout for reading
                ),
                connector=self._connector
            )
            
            # Test connection with a light request
            try:
                # Use a shorter timeout for the initial health check
                await asyncio.wait_for(self.get_health(), timeout=min(3.0, self.timeout / 2))
                logger.debug(f"Successfully connected to {self.endpoint}")
                self._closed = False
                return True
            except asyncio.TimeoutError:
                logger.warning(f"Connection timed out for {self.endpoint}")
                await self.close()
                raise ConnectionError(f"Connection timed out for {self.endpoint}")
            except Exception as e:
                logger.warning(f"Failed to connect to {self.endpoint}: {str(e)}")
                await self.close()
                raise
        
        return True
    
    async def close(self):
        """Close the client connection"""
        if self._client is not None:
            try:
                logger.debug(f"Closing client for {self.endpoint}")
                await self._client.close()
                logger.debug(f"Successfully closed client for {self.endpoint}")
            except Exception as e:
                logger.warning(f"Error closing client for {self.endpoint}: {str(e)}")
            finally:
                self._client = None
                self._closed = True
                
        if self._connector is not None:
            try:
                if not self._connector.closed:
                    await self._connector.close()
                    logger.debug(f"Successfully closed connector for {self.endpoint}")
            except Exception as e:
                logger.warning(f"Error closing connector for {self.endpoint}: {str(e)}")
            finally:
                self._connector = None
                
    def __del__(self):
        """Destructor to ensure client is closed when object is garbage collected"""
        if hasattr(self, '_closed') and not self._closed:
            # Try to close the client if it exists
            if hasattr(self, '_client') and self._client is not None:
                try:
                    # First try to get the event loop
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # If loop is running, schedule the close coroutine
                            asyncio.run_coroutine_threadsafe(self.close(), loop)
                            logger.debug(f"Scheduled client closure for {self.endpoint} in event loop")
                            return  # Exit early as we've scheduled proper cleanup
                    except (RuntimeError, AttributeError) as e:
                        # Expected error when no event loop is available
                        pass
                        
                    # Fallback to synchronous close
                    logger.debug(f"No running event loop found, closing client for {self.endpoint} synchronously")
                    if hasattr(self, '_client') and self._client is not None:
                        self._client._session.close()
                        self._client = None
                        self._closed = True
                except Exception as e:
                    logger.warning(f"Error in __del__ for {self.endpoint}: {str(e)}")
    
    def _record_latency(self, latency: float):
        """Record latency for this endpoint"""
        self._latencies.append(latency)
        if len(self._latencies) > self._max_latencies:
            self._latencies.pop(0)
    
    def get_avg_latency(self) -> float:
        """Get average latency for this endpoint"""
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)
    
    async def _make_rpc_call(self, method: str, params: Optional[List[Any]] = None, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Make an RPC call to the Solana node.
        
        Args:
            method: The RPC method to call
            params: The parameters to pass to the method
            timeout: Optional timeout override for this specific call
            
        Returns:
            The response from the RPC call
            
        Raises:
            RPCError: If the RPC call fails
            RetryableError: If the RPC call fails but can be retried
        """
        params = params or []
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params
        }
        
        start_time = time.time()
        client_created = False
        
        try:
            # Ensure we have a client
            if not self._client:
                await self.connect()
                client_created = True
            
            # Use the provided timeout or default to the client timeout
            call_timeout = timeout or self.timeout
            
            # Use asyncio.timeout for more granular control
            async with asyncio.timeout(call_timeout):
                async with self._client.post(
                    self.endpoint, 
                    json=payload
                ) as response:
                    latency = time.time() - start_time
                    self._record_latency(latency)
                    
                    # Check for HTTP errors
                    if response.status >= 400:
                        logger.warning(f"HTTP error {response.status} for {method}")
                        self._rate_limiter.update_rate(False)
                        raise RetryableError(f"HTTP error {response.status}")
                    
                    # Parse the response
                    try:
                        result = await response.json()
                    except Exception as e:
                        logger.warning(f"Failed to parse JSON response for {method}: {str(e)}")
                        content_type = response.headers.get('Content-Type', 'unknown')
                        self._rate_limiter.update_rate(False)
                        raise RetryableError(f"Failed to parse JSON response. Content-Type: {content_type}")
                    
                    # Handle RPC errors
                    if "error" in result:
                        error = result["error"]
                        error_msg = error.get("message", str(error))
                        error_code = error.get("code", 0)
                        
                        # Check for rate limiting
                        if error_code == -32005 or "rate limit" in error_msg.lower():
                            logger.warning(f"Rate limited on {method}: {error_msg}")
                            self._rate_limiter.update_rate(False)
                            raise RateLimitError(f"Rate limited: {error_msg}")
                        
                        # Check for API key errors
                        if "api key" in error_msg.lower():
                            logger.error(f"API key error for {method}: {error_msg}")
                            raise RPCError(f"RPC error: {error_msg}")
                        
                        # Check for method not supported
                        if error_code == -32601 or "method not found" in error_msg.lower():
                            logger.warning(f"Method {method} not supported: {error_msg}")
                            raise MethodNotSupportedError(f"Method not supported: {error_msg}")
                        
                        # Check for other retryable errors
                        if error_code in [-32603, -32002] or "internal error" in error_msg.lower():
                            logger.warning(f"Retryable RPC error for {method}: {error_msg}")
                            self._rate_limiter.update_rate(False)
                            raise RetryableError(f"Retryable RPC error: {error_msg}")
                        
                        # Other RPC errors
                        logger.error(f"RPC error in {method}: {error_msg}")
                        raise RPCError(f"RPC error: {error_msg}")
                    
                    # Update rate limiter on success
                    self._rate_limiter.update_rate(True)
                    
                    return result
        
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.warning(f"Timeout after {elapsed:.2f}s for {method} on {self.endpoint}")
            self._rate_limiter.update_rate(False)
            raise RetryableError(f"Timeout after {elapsed:.2f}s")
        
        except (aiohttp.ClientError, ConnectionError) as e:
            logger.warning(f"Client error in {method}: {str(e)}")
            self._rate_limiter.update_rate(False)
            raise RetryableError(f"Connection error: {str(e)}")
        
        except (RetryableError, RateLimitError):
            # Pass through retryable errors
            raise
        
        except Exception as e:
            logger.error(f"Error in {method}: {str(e)}")
            if not isinstance(e, RPCError):
                logger.exception(e)  # Log full stack trace for unexpected errors
            raise
        
        finally:
            # If we created a client and got an error, close it
            if client_created and (self._client is None or self._client.closed):
                await self.close()
    
    async def get_transaction(
        self,
        signature: str,
        encoding: str = "json",
        commitment: str = "confirmed",
        max_supported_transaction_version: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Get transaction details by signature"""
        try:
            # Call the getTransaction RPC method
            params = [
                signature,
                {
                    "encoding": encoding,
                    "commitment": commitment,
                    "maxSupportedTransactionVersion": max_supported_transaction_version
                }
            ]
            
            result = await self._make_rpc_call("getTransaction", params)
            
            # Return the result if available
            if "result" in result and result["result"] is not None:
                return result["result"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting transaction {signature}: {str(e)}")
            raise

    async def get_block(self, slot: int, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get block information for the given slot.
        
        Args:
            slot: Block slot number
            options: Additional parameters for getBlock
            
        Returns:
            Dict: Block information
            
        Raises:
            RPCError: If the RPC call fails
            SlotSkippedError: If the slot was skipped
            MethodNotSupportedError: If the endpoint doesn't support getBlock
        """
        try:
            # Prepare parameters
            params = [slot]
            
            # Initialize options if not provided
            if options is None:
                options = {}
                
            # Add encoding parameter if not provided
            if "encoding" not in options:
                options["encoding"] = "json"
                
            # Add transaction details parameter if not provided
            if "transactionDetails" not in options:
                options["transactionDetails"] = "full"
                
            # Always add maxSupportedTransactionVersion parameter to ensure compatibility
            if "maxSupportedTransactionVersion" not in options:
                options["maxSupportedTransactionVersion"] = 0
            
            # Add additional parameters
            params.append(options)
            
            # Make RPC call
            try:
                return await self._make_rpc_call("getBlock", params)
            except RPCError as e:
                if "Method not found" in str(e):
                    raise MethodNotSupportedError(f"Method getBlock not supported by endpoint {self.endpoint}")
                raise
                
        except Exception as e:
            # Check for specific error messages
            error_str = str(e).lower()
            
            # Handle slot skipped errors
            if "skipped slot" in error_str:
                logger.warning(f"Slot {slot} was skipped")
                raise SlotSkippedError(f"Slot {slot} was skipped")
                
            # Handle slot not found errors
            if "slot not found" in error_str or "block not available" in error_str:
                logger.warning(f"Slot {slot} not found or not available")
                raise SlotSkippedError(f"Slot {slot} not found or not available")
                
            # Re-raise other exceptions
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
            List: Information about cluster nodes
        """
        try:
            # Make the RPC call
            response = await self._make_rpc_call("getClusterNodes", [])
            
            # Check if the response is valid
            if isinstance(response, dict) and "result" in response:
                return response["result"]
            elif isinstance(response, list):
                # Some endpoints might return the result directly as a list
                return response
            else:
                logger.warning(f"Unexpected response format from getClusterNodes: {type(response)}")
                return []
        except Exception as e:
            logger.error(f"Error in getClusterNodes: {str(e)}")
            raise
            
    async def getClusterNodes(self, *args, **kwargs):
        """
        Alias for get_cluster_nodes to maintain compatibility with code using camelCase.
        
        Returns:
            List: Information about cluster nodes
        """
        return await self.get_cluster_nodes(*args, **kwargs)

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
        try:
            return await self._make_rpc_call("getBlockProduction", args or [])
        except Exception as e:
            error_msg = str(e).lower()
            if "not supported" in error_msg or "method not found" in error_msg:
                logger.warning(f"Method getBlockProduction not supported by endpoint {self.endpoint}")
                # Return a structured empty result that matches the expected format
                return {
                    "result": {
                        "total": 0,
                        "skippedSlots": 0,
                        "byIdentity": {}
                    }
                }
            else:
                # Log the error for debugging
                logger.error(f"Error calling getBlockProduction on {self.endpoint}: {str(e)}")
                # Re-raise other errors
                raise

    async def get_recent_performance_samples(self, *args, **kwargs):
        """
        Get recent performance samples.
        
        Returns:
            Dict: Recent performance samples or a fallback empty result if not supported
        """
        try:
            return await self._make_rpc_call("getRecentPerformanceSamples", args or [])
        except Exception as e:
            error_msg = str(e).lower()
            if "not supported" in error_msg or "method not found" in error_msg:
                logger.warning(f"getRecentPerformanceSamples not supported by endpoint {self.endpoint}")
                # Return a structured empty result that matches the expected format
                return {
                    "result": [],
                    "error": {
                        "message": f"Method not supported by endpoint {self.endpoint}",
                        "code": -32601,  # Standard JSON-RPC code for method not found
                        "data": {
                            "endpoint": self.endpoint,
                            "original_error": str(e)
                        }
                    }
                }
            else:
                # Log the error for debugging
                logger.error(f"Error calling getRecentPerformanceSamples on {self.endpoint}: {str(e)}")
                # Re-raise other errors
                raise

    async def get_version(self) -> Dict[str, Any]:
        """Get the version of the RPC API."""
        return await self._make_rpc_call("getVersion", [])

    async def get_slot(self, commitment: Optional[str] = None) -> int:
        """
        Get the current slot from the Solana cluster.
        
        Args:
            commitment: Optional commitment level
            
        Returns:
            int: The current slot
            
        Raises:
            RPCError: If the RPC call fails
        """
        try:
            params = []
            if commitment:
                params = [{"commitment": commitment}]
                
            result = await self._make_rpc_call("getSlot", params)
            if result and isinstance(result, dict) and "result" in result:
                return int(result["result"])
            else:
                raise RPCError("Invalid response format for getSlot")
        except Exception as e:
            logger.error(f"Error in get_slot: {str(e)}")
            raise

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

    async def get_validator_info(self, pubkey: str) -> Dict[str, Any]:
        """
        Get validator info for a specific validator.
        
        Args:
            pubkey: The validator's public key
            
        Returns:
            Dict: Validator information or empty dict if not found
        """
        try:
            result = await self._make_rpc_call("getValidatorInfo", [pubkey])
            if "result" not in result or result["result"] is None:
                logger.debug(f"No validator info found for {pubkey}")
                return {}
            return result["result"]
        except Exception as e:
            logger.debug(f"Error getting validator info for {pubkey}: {str(e)}")
            return {}

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

    async def get_health(self):
        """Check the health of the node"""
        start = time.time()
        try:
            # Use a shorter timeout for health checks
            timeout = min(3.0, self.timeout / 2)
            async with asyncio.timeout(timeout):
                async with self._client.post(
                    self.endpoint, 
                    json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"}
                ) as response:
                    result = await response.json()
                    if "result" in result and result["result"] != "ok":
                        raise NodeUnhealthyError(f"Node health check failed: {result}")
                    
            latency = time.time() - start
            self._record_latency(latency)
            
            return "ok"
        except asyncio.TimeoutError:
            logger.warning(f"Health check timed out for {self.endpoint} after {time.time() - start:.2f}s")
            raise NodeUnhealthyError(f"Health check timed out for {self.endpoint}")
        except Exception as e:
            logger.warning(f"Health check failed for {self.endpoint}: {str(e)}")
            raise

    async def get_recent_blockhash(self, commitment: Optional[str] = "processed"):
        """
        Get a recent blockhash from the cluster.
        
        Args:
            commitment: Commitment level for the blockhash ("processed" is recommended for most use cases)
            
        Returns:
            Dict: Contains blockhash and lastValidBlockHeight
        """
        params = []
        if commitment:
            params = [{"commitment": commitment}]
            
        result = await self._make_rpc_call("getRecentBlockhash", params)
        
        if "value" in result:
            return result["value"]
        return result

    async def get_cluster_nodes(self, *args, **kwargs):
        """
        Get information about the cluster nodes.
        
        Returns:
            List: Information about cluster nodes
        """
        try:
            # Make the RPC call
            response = await self._make_rpc_call("getClusterNodes", [])
            
            # Check if the response is valid
            if isinstance(response, dict) and "result" in response:
                return response["result"]
            elif isinstance(response, list):
                # Some endpoints might return the result directly as a list
                return response
            else:
                logger.warning(f"Unexpected response format from getClusterNodes: {type(response)}")
                return []
        except Exception as e:
            logger.error(f"Error in getClusterNodes: {str(e)}")
            raise

class SolanaConnectionPool:
    """Pool of Solana RPC clients with enhanced connection management."""
    
    def __init__(
        self, 
        endpoints: Optional[List[str]] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        ssl_verify: bool = True,
        connector_args: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a pool of Solana RPC clients.
        
        Args:
            endpoints: List of RPC endpoint URLs
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            ssl_verify: Whether to verify SSL certificates
            connector_args: Additional arguments for the TCP connector
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.ssl_verify = ssl_verify
        self.connector_args = connector_args or {}
        self._pool = []
        self._stats = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        self._current_index = -1
        self.endpoints = endpoints or []
        self.pool_size = 10  # Default maximum pool size
        self._rate_limited_until = {}
        self._max_consecutive_failures = 5
        
        # Initialize with provided endpoints if any
        if endpoints:
            asyncio.create_task(self.initialize(endpoints))
    
    class ClientContextManager:
        """Context manager for acquiring and releasing clients from the pool."""
        
        def __init__(self, pool):
            self.pool = pool
            self.client = None
            self.start_time = None
            
        async def __aenter__(self):
            """Acquire a client from the pool."""
            self.client = await self.pool.get_client()
            self.start_time = time.time()
            return self.client
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            """Release the client back to the pool."""
            if self.client:
                latency = time.time() - self.start_time if self.start_time else None
                success = exc_type is None
                await self.pool.release(self.client, success, latency)
                
    async def acquire(self):
        """
        Acquire a client from the pool.
        
        Returns:
            ClientContextManager: A context manager for a client from the pool
            
        Usage:
            async with pool.acquire() as client:
                result = await client.get_version()
        """
        return self.ClientContextManager(self)

    async def initialize(self, endpoints: List[str] = None) -> None:
        """
        Initialize the connection pool with the given endpoints.
        
        Args:
            endpoints: List of endpoint URLs to connect to
        
        Raises:
            ConnectionError: If no connections could be established
        """
        async with self._lock:
            # Close any existing connections
            if self._initialized:
                await self.close()
                
            # Validate endpoints
            if not endpoints:
                endpoints = DEFAULT_RPC_ENDPOINTS
                
            # Filter out invalid endpoints
            valid_endpoints = []
            for endpoint in endpoints:
                if isinstance(endpoint, str) and endpoint.startswith(('http://', 'https://')) and len(endpoint) > 10:
                    valid_endpoints.append(endpoint)
                else:
                    logger.warning(f"Skipping invalid endpoint: {endpoint}")
                    
            if not valid_endpoints:
                error_msg = "No valid endpoints provided"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            # Reset pool and stats
            self._pool = []
            self._stats = {}
            
            logger.info(f"Initializing connection pool with endpoints: {valid_endpoints}")
            
            # Try to initialize connections
            successful_connections = 0
            for endpoint in valid_endpoints:
                try:
                    client = SolanaClient(
                        endpoint=endpoint,
                        timeout=self.timeout,
                        max_retries=self.max_retries,
                        ssl_verify=self.ssl_verify,
                        connector_args=self.connector_args
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
        async with self._lock:
            logger.info(f"Closing connection pool with {len(self._pool)} clients")
            clients_to_close = []
            
            # First collect all clients to avoid modifying the list while iterating
            for client, _ in self._pool:
                if client:
                    clients_to_close.append(client)
            
            # Then close each client
            closed_count = 0
            for client in clients_to_close:
                try:
                    await client.close()
                    closed_count += 1
                    logger.debug(f"Successfully closed client for {client.endpoint} in pool")
                except Exception as e:
                    logger.warning(f"Error closing client in pool for {client.endpoint}: {str(e)}")
            
            # Clear the pool
            self._pool.clear()
            self._initialized = False
            logger.info(f"Connection pool closed and cleaned up ({closed_count}/{len(clients_to_close)} clients closed)")
    
    async def cleanup(self):
        """Alias for close() to maintain compatibility"""
        await self.close()

    async def __aenter__(self):
        await self.initialize(DEFAULT_RPC_ENDPOINTS)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_client(self) -> SolanaClient:
        """
        Get a client from the pool, prioritizing clients with lower failure counts.
        
        Returns:
            A SolanaClient instance
        
        Raises:
            NoClientsAvailableError: If no clients are available in the pool
        """
        async with self._lock:
            # Check if we need to refresh the pool
            if len(self._pool) == 0:
                logger.warning("Connection pool is empty, initializing with defaults")
                await self.initialize_with_defaults()
                
                # If still empty after initialization, raise an error
                if len(self._pool) == 0:
                    logger.error("Failed to initialize connection pool with defaults")
                    raise NoClientsAvailableError("No clients available in the connection pool")
            
            # Filter out endpoints that are currently rate limited or have excessive failures
            current_time = time.time()
            available_clients = []
            
            for i, (client, failure_count) in enumerate(self._pool):
                endpoint = client.endpoint
                
                # Skip rate-limited endpoints
                if endpoint in self._rate_limited_until and current_time < self._rate_limited_until[endpoint]:
                    continue
                
                # Skip endpoints with too many consecutive failures
                if failure_count >= self._max_consecutive_failures:
                    continue
                
                # Skip endpoints with poor performance metrics
                if endpoint in self._stats:
                    stats = self._stats[endpoint]
                    
                    # Skip if success rate is too low (less than 50%)
                    success_count = stats.get("success_count", 0)
                    failure_count = stats.get("failure_count", 0)
                    total_count = success_count + failure_count
                    
                    if total_count > 10 and success_count / total_count < 0.5:
                        continue
                
                available_clients.append((i, client, failure_count))
            
            # If no clients are available, try to use any client
            if not available_clients:
                logger.warning("No healthy clients available, using any available client")
                available_clients = [(i, client, failure_count) for i, (client, failure_count) in enumerate(self._pool)]
            
            # Sort by failure count (ascending)
            available_clients.sort(key=lambda x: x[2])
            
            # Choose from the top 3 clients with lowest failure counts
            top_clients = available_clients[:min(3, len(available_clients))]
            i, client, _ = random.choice(top_clients)
            
            logger.debug(f"Selected client for endpoint {client.endpoint} with {self._pool[i][1]} failures")
            return client
    
    async def get_specific_client(self, target_endpoint: str) -> Optional[SolanaClient]:
        """
        Get a client for a specific endpoint.
        
        Args:
            target_endpoint: The endpoint URL to get a client for
            
        Returns:
            SolanaClient or None if the endpoint is not in the pool or cannot be created
        """
        try:
            # Normalize the endpoint URL for comparison
            target_endpoint = target_endpoint.strip().rstrip('/')
            
            async with self._lock:
                # First check if we already have a client for this endpoint in the pool
                for client, _ in self._pool:
                    normalized_endpoint = client.endpoint.strip().rstrip('/')
                    if normalized_endpoint == target_endpoint:
                        logger.debug(f"Found existing client for endpoint {target_endpoint}")
                        return client
                
                # If not found by exact match, try to find by partial match (for API keys)
                for client, _ in self._pool:
                    # For Helius endpoints, the API key might be different but the base URL is the same
                    if "helius-rpc.com" in client.endpoint.lower() and "helius-rpc.com" in target_endpoint.lower():
                        logger.debug(f"Found Helius client (different API key) for {target_endpoint}")
                        return client
                
                # If we don't have a client for this endpoint, create one
                logger.info(f"Creating new client for specific endpoint {target_endpoint}")
                try:
                    client = SolanaClient(
                        target_endpoint,
                        timeout=self.timeout,
                        max_retries=self.max_retries,
                        ssl_verify=self.ssl_verify,
                        connector_args=self.connector_args
                    )
                    await client.connect()
                    
                    # Add to pool with 0 failures
                    self._pool.append((client, 0))
                    
                    return client
                except Exception as e:
                    logger.error(f"Failed to create client for {target_endpoint}: {str(e)}")
                    return None
                
        except Exception as e:
            logger.error(f"Error getting specific client for {target_endpoint}: {str(e)}")
            return None
    
    async def release(self, client: SolanaClient, success: bool, latency: float = None, rate_limited: bool = False) -> None:
        """
        Release a client back to the pool.
        
        Args:
            client: The client to release
            success: Whether the operation was successful
            latency: The latency of the operation (if successful)
            rate_limited: Whether the endpoint was rate limited
        """
        if client is None:
            logger.warning("Attempted to release a None client")
            return
            
        async with self._lock:
            # Handle rate limited endpoints
            if rate_limited:
                # Mark endpoint as rate limited for a cooling period
                cooling_period = random.uniform(30, 60)  # 30-60 seconds cooling period
                self._rate_limited_until[client.endpoint] = time.time() + cooling_period
                logger.warning(f"Marking endpoint {client.endpoint} as rate limited for {cooling_period:.1f}s")
                
            # Find the client in the pool
            for i, (pool_client, failure_count) in enumerate(self._pool):
                if pool_client.endpoint == client.endpoint:
                    # Update failure count based on success
                    if success:
                        new_failure_count = 0
                    else:
                        new_failure_count = failure_count + 1
                        if new_failure_count >= self._max_consecutive_failures:
                            logger.warning(f"Client for {client.endpoint} has {new_failure_count} consecutive failures")
                    
                    # Update the client in the pool
                    self._pool[i] = (pool_client, new_failure_count)
                    
                    # Update endpoint stats
                    if latency is not None:
                        await self.update_endpoint_stats(client.endpoint, success, latency, rate_limited)
                    else:
                        await self.update_endpoint_stats(client.endpoint, success, rate_limited=rate_limited)
                    
                    return
            
            # If client not found in pool (unusual), close it
            logger.warning(f"Client for endpoint {client.endpoint} not found in pool during release")
            try:
                await client.close()
                logger.debug(f"Closed client for {client.endpoint} as it was not found in pool")
            except Exception as e:
                logger.warning(f"Error closing client for {client.endpoint}: {str(e)}")
    
    async def check_endpoint_health(self, endpoint: str):
        """
        Check the health of an endpoint and update its performance metrics.
        
        Args:
            endpoint: The endpoint to check
            
        Returns:
            True if the endpoint is healthy, False otherwise
        """
        # Validate endpoint format
        if not isinstance(endpoint, str) or not endpoint.startswith(('http://', 'https://')) or len(endpoint) <= 10:
            logger.warning(f"Invalid endpoint format: {endpoint}")
            return False
            
        # Create a temporary client to test the endpoint
        client = None
        try:
            client = SolanaClient(
                endpoint=endpoint,
                timeout=5.0,  # Short timeout for health check
                max_retries=1,  # Only try once
                ssl_verify=self.ssl_verify,
                connector_args=self.connector_args
            )
            
            # Connect the client
            await client.connect()
            
            # Test basic health
            start_time = time.time()
            
            # Try to get version first (lightest call)
            try:
                await client.get_version()
                latency = time.time() - start_time
                await self.update_endpoint_stats(endpoint, True, latency)
                logger.debug(f"Endpoint {endpoint} is healthy (latency: {latency:.2f}s)")
                return True
            except RateLimitError:
                # If rate limited, mark as unhealthy but not a complete failure
                logger.warning(f"Endpoint {endpoint} is rate limited")
                await self.update_endpoint_stats(endpoint, False)
                
                # Add to rate limited endpoints tracking
                cooling_period = random.uniform(30, 60)  # 30-60 seconds cooling period
                self._rate_limited_until[endpoint] = time.time() + cooling_period
                logger.warning(f"Marking endpoint {endpoint} as rate limited for {cooling_period:.1f}s")
                return False
            except Exception as e:
                # Any other error means the endpoint is unhealthy
                logger.warning(f"Endpoint {endpoint} is unhealthy: {str(e)}")
                await self.update_endpoint_stats(endpoint, False)
                return False
        except Exception as e:
            # Connection error
            logger.warning(f"Failed to connect to endpoint {endpoint}: {str(e)}")
            await self.update_endpoint_stats(endpoint, False)
            return False
        finally:
            # Always close the client
            if client:
                try:
                    await client.close()
                    logger.debug(f"Successfully closed temporary client for {endpoint}")
                except Exception as e:
                    logger.warning(f"Error closing temporary client for {endpoint}: {str(e)}")
    
    async def get_endpoint_stats(self) -> Dict[str, Any]:
        """
        Get statistics about endpoint performance.
        
        Returns:
            Dict: Statistics about each endpoint
        """
        async with self._lock:
            # Count active and available clients
            active_clients = len([c for c in self._pool if c[1] == 0])
            available_clients = len([c for c in self._pool if c[1] > 0])
            
            # Calculate success rates and sort endpoints by performance
            performers = []
            for endpoint, stats in self._stats.items():
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
                    "in_pool": endpoint in [client.endpoint for client, _ in self._pool]
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
                "total_endpoints": len(self._stats),
                "top_performers": filtered_performers
            }

    async def update_endpoint_stats(self, endpoint: str, success: bool, latency: float = None, rate_limited: bool = False) -> None:
        """
        Update statistics for a specific RPC endpoint.
        
        Args:
            endpoint: The endpoint URL
            success: Whether the operation was successful
            latency: The latency of the operation (if successful)
            rate_limited: Whether the endpoint was rate limited
        """
        if endpoint in self._stats:
            if success:
                self._stats[endpoint]["success_count"] = self._stats[endpoint].get("success_count", 0) + 1
                # Update latency using exponential moving average if latency is provided
                if latency is not None:
                    alpha = 0.3  # Weight for new value
                    current_avg = self._stats[endpoint].get("avg_latency")
                    if current_avg is not None:
                        self._stats[endpoint]["avg_latency"] = alpha * latency + (1 - alpha) * current_avg
                    else:
                        self._stats[endpoint]["avg_latency"] = latency
                # Reset current failures
                self._stats[endpoint]["current_failures"] = 0
            else:
                self._stats[endpoint]["failure_count"] = self._stats[endpoint].get("failure_count", 0) + 1
                self._stats[endpoint]["current_failures"] = self._stats[endpoint].get("current_failures", 0) + 1
            
            # Track rate limiting
            if rate_limited:
                self._stats[endpoint]["rate_limited_count"] = self._stats[endpoint].get("rate_limited_count", 0) + 1
                self._stats[endpoint]["last_rate_limited"] = time.time()
        else:
            self._stats[endpoint] = {
                "success_count": 1 if success else 0,
                "failure_count": 0 if success else 1,
                "avg_latency": latency if success and latency is not None else 0,
                "current_failures": 0 if success else 1,
                "rate_limited_count": 1 if rate_limited else 0,
                "last_rate_limited": time.time() if rate_limited else None
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
        helius_endpoint = next((ep for ep in DEFAULT_RPC_ENDPOINTS if "helius-rpc.com" in ep), None)
        sorted_endpoints = [helius_endpoint] if helius_endpoint else []
        
        # Get remaining endpoints
        remaining_endpoints = [ep for ep in DEFAULT_RPC_ENDPOINTS if ep not in sorted_endpoints]
        
        # Sort remaining endpoints by performance metrics
        endpoint_scores = []
        for endpoint in remaining_endpoints:
            stats = self._stats.get(endpoint, {
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

    async def update_endpoints(self, new_endpoints: List[str]):
        """
        Update the pool with a new list of endpoints.
        
        This method will:
        1. Validate and filter the new endpoints
        2. Add any new endpoints to the pool
        3. Remove endpoints that are no longer in the list
        4. Sort endpoints by performance
        5. Re-initialize the pool with the sorted endpoints
        
        Args:
            new_endpoints: The new list of endpoints to use
        """
        if not new_endpoints:
            logger.warning("Empty endpoint list provided for update, ignoring")
            return
            
        logger.info(f"Updating connection pool with {len(new_endpoints)} endpoints")
        
        # Store current endpoints for comparison
        current_endpoints = [client.endpoint for client, _ in self._pool]
        
        # Filter out invalid endpoints
        valid_endpoints = []
        for endpoint in new_endpoints:
            if isinstance(endpoint, str) and endpoint.startswith(('http://', 'https://')) and len(endpoint) > 10:
                valid_endpoints.append(endpoint)
            else:
                logger.warning(f"Skipping invalid endpoint during update: {endpoint}")
        
        if not valid_endpoints:
            logger.warning("No valid endpoints found in update request, keeping current endpoints")
            return
            
        # Log changes
        added = [ep for ep in valid_endpoints if ep not in current_endpoints]
        removed = [ep for ep in current_endpoints if ep not in valid_endpoints]
        
        if added:
            logger.info(f"Adding {len(added)} new endpoints to the pool")
            for ep in added[:5]:  # Log first 5 for brevity
                logger.debug(f"  Adding: {ep}")
            if len(added) > 5:
                logger.debug(f"  ... and {len(added) - 5} more")
                
        if removed:
            logger.info(f"Removing {len(removed)} endpoints from the pool")
            for ep in removed[:5]:  # Log first 5 for brevity
                logger.debug(f"  Removing: {ep}")
            if len(removed) > 5:
                logger.debug(f"  ... and {len(removed) - 5} more")
        
        # Sort endpoints by performance
        sorted_endpoints = await self.sort_endpoints_by_performance()
        
        # Combine sorted existing endpoints with new endpoints
        # This ensures we keep the performance history for existing endpoints
        final_endpoints = []
        
        # First add sorted existing endpoints that are still valid
        for ep in sorted_endpoints:
            if ep in valid_endpoints:
                final_endpoints.append(ep)
                
        # Then add any new endpoints that weren't in the sorted list
        for ep in valid_endpoints:
            if ep not in final_endpoints:
                final_endpoints.append(ep)
        
        # Close all existing clients before re-initializing
        logger.info(f"Closing existing pool before updating with new endpoints")
        await self.close()

        # Re-initialize the pool with the final endpoint list
        logger.info(f"Re-initializing pool with {len(final_endpoints)} endpoints")
        await self.initialize(final_endpoints)
        
        logger.info(f"Connection pool updated with {len(self._pool)} endpoints")

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
            stats = self._stats.get(endpoint, {})
            logger.info(f"  {i+1}. {endpoint} - " +
                       f"Success Rate: {stats.get('success_rate', 0):.2f}, " +
                       f"Avg Latency: {stats.get('avg_latency', 0):.3f}s, " +
                       f"Failures: {self._stats.get(endpoint, {}).get('current_failures', 0)}")

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the connection pool.
        
        Returns:
            Dict with statistics about the connection pool
        """
        async with self._lock:
            # Count active and available clients
            active_clients = len([c for c, f in self._pool if f == 0])
            available_clients = len(self._pool)
            
            # Calculate success rates and sort endpoints by performance
            performers = []
            endpoint_stats = {}
            
            for endpoint, stats in self._stats.items():
                total_requests = stats.get("success_count", 0) + stats.get("failure_count", 0)
                if total_requests > 0:
                    success_rate = stats.get("success_count", 0) / total_requests * 100  # Convert to percentage
                else:
                    success_rate = 0
                
                endpoint_data = {
                    "endpoint": endpoint,
                    "success_rate": success_rate,
                    "avg_latency": stats.get("avg_latency", 0),
                    "success_count": stats.get("success_count", 0),
                    "failure_count": stats.get("failure_count", 0),
                    "current_failures": stats.get("current_failures", 0),
                    "in_pool": endpoint in [client.endpoint for client, _ in self._pool]
                }
                
                performers.append(endpoint_data)
                endpoint_stats[endpoint] = endpoint_data
            
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
                "total_endpoints": len(self._stats),
                "top_performers": filtered_performers,
                "endpoint_stats": endpoint_stats  # Add endpoint_stats to the return value
            }
    
    async def get_rpc_stats(self):
        """
        Get detailed statistics about RPC endpoint performance.
        
        Returns:
            Dict: Detailed statistics about each endpoint and summary metrics
        """
        # Get stats for each endpoint
        stats = {}
        total_success = 0
        total_failures = 0
        
        for url in self._stats:
            endpoint_stats = self._stats[url]
            success_count = endpoint_stats.get("success_count", 0)
            failure_count = endpoint_stats.get("failure_count", 0)
            
            # Calculate success rate
            total_requests = success_count + failure_count
            success_rate = success_count / max(total_requests, 1)
            
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
                "overall_success_rate": total_success / max(total_success + total_failures, 1)
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
                "overall_success_rate": round(total_success / max(total_success + total_failures, 1), 2)
            },
            "top_performers": filtered_performers
        }

    def __del__(self):
        """Destructor to ensure proper cleanup of resources during garbage collection."""
        if hasattr(self, '_pool') and self._pool:
            logger.debug(f"SolanaConnectionPool.__del__: Cleaning up {len(self._pool)} clients")
            
            # Try to get an event loop
            try:
                loop = asyncio.get_event_loop()
                
                # If we have a running loop, use it to close clients
                if loop.is_running():
                    # Create a task to close all clients
                    asyncio.create_task(self.close())
                    logger.debug("Created async task to close connection pool")
                else:
                    # If loop is not running, we can't use it to close clients
                    logger.debug("Event loop not running, closing clients synchronously")
                    for client, _ in self._pool:
                        if client:
                            # Try to close the client synchronously
                            if hasattr(client, '_client') and client._client and not client._client.closed:
                                client._client.close()
                            if hasattr(client, '_connector') and client._connector and not client._connector.closed:
                                client._connector.close()
                    
                    # Clear the pool
                    self._pool.clear()
            except Exception as e:
                logger.warning(f"Error in SolanaConnectionPool.__del__: {str(e)}")
                
                # Last resort: try to close clients directly
                try:
                    for client, _ in self._pool:
                        if client:
                            # Try to close the client synchronously
                            if hasattr(client, '_client') and client._client and not client._client.closed:
                                client._client.close()
                            if hasattr(client, '_connector') and client._connector and not client._connector.closed:
                                client._connector.close()
                except Exception as e2:
                    logger.warning(f"Failed to close clients in SolanaConnectionPool.__del__: {str(e2)}")

async def get_connection_pool() -> SolanaConnectionPool:
    """Get or create a shared connection pool."""
    global _connection_pool
    
    if _connection_pool is None:
        try:
            _connection_pool = SolanaConnectionPool(
                endpoints=DEFAULT_RPC_ENDPOINTS,
                timeout=30.0,
                max_retries=3,
                ssl_verify=True,
                connector_args=None
            )
            # The constructor will create a task to initialize the pool
            # No need to call initialize here as it will be called by the task
            logger.info("Created new connection pool")
        except Exception as e:
            logger.error(f"Error creating connection pool: {str(e)}")
            raise
    
    return _connection_pool

_connection_pool: Optional[SolanaConnectionPool] = None
_pool_lock = asyncio.Lock()

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

async def safe_rpc_call_async(method, client=None, params=None, max_retries=3, retry_delay=1.0, timeout=10.0, **kwargs):
    """
    Execute an RPC call with retry logic and error handling.
    
    Args:
        method: The RPC method to call
        client: The RPC client to use
        params: The parameters to pass to the method
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        timeout: Timeout for the RPC call in seconds
        **kwargs: Additional arguments to pass to the method
        
    Returns:
        The result of the RPC call
    """
    if params is None:
        params = []
        
    if not isinstance(params, list):
        params = [params]
        
    # Special handling for getClusterNodes
    is_get_cluster_nodes = method.lower() in ["getclusterNodes", "getcluster_nodes", "get_cluster_nodes"]
    if is_get_cluster_nodes:
        logging.info(f"Executing getClusterNodes RPC call with special handling to {client.endpoint}")
        # Use a shorter timeout for getClusterNodes to avoid long waits
        timeout = min(timeout, 4.0)
        
    # Track errors by endpoint
    errors_by_endpoint = {}
    
    # Retry loop
    for retry in range(max_retries):
        try:
            # Adjust timeout for subsequent retries (make them shorter)
            current_timeout = timeout * (0.8 ** retry)  # Reduce timeout by 20% each retry
            
            # Make the RPC call with timeout
            start_time = time.time()
            response = await asyncio.wait_for(
                client._make_rpc_call(method, params, **kwargs),
                timeout=current_timeout
            )
            elapsed = time.time() - start_time
            
            # For getClusterNodes, check if the response is valid
            if is_get_cluster_nodes:
                if isinstance(response, dict):
                    if 'result' in response:
                        nodes = response['result']
                        if isinstance(nodes, list):
                            nodes_count = len(nodes)
                            if nodes_count > 0:
                                logging.info(f"Successfully retrieved {nodes_count} nodes from {client.endpoint} in {elapsed:.2f}s")
                                return response
                            else:
                                logging.warning(f"getClusterNodes returned empty list from {client.endpoint}")
                                errors_by_endpoint[client.endpoint] = "Empty nodes list"
                                # Don't retry the same endpoint for empty lists
                                break
                        else:
                            logging.warning(f"getClusterNodes returned non-list result from {client.endpoint}: {type(nodes)}")
                            errors_by_endpoint[client.endpoint] = f"Non-list result: {type(nodes)}"
                            # Don't retry the same endpoint for invalid response formats
                            break
                    elif 'error' in response:
                        error_info = response['error']
                        error_msg = error_info.get('message', str(error_info))
                        error_code = error_info.get('code', 0)
                        
                        # Check for API key related errors
                        if error_code in [401, 403, -32000, -32001, -32002, -32003, -32004]:
                            logging.error(f"API key or authorization error from {client.endpoint}: {error_msg}")
                            # Check if it's an SSL error
                            if "SSL" in error_msg or "certificate" in error_msg.lower():
                                try:
                                    from .solana_ssl_config import add_ssl_bypass_endpoint
                                    add_ssl_bypass_endpoint(client.endpoint)
                                    logging.info(f"Added {client.endpoint} to SSL bypass list due to certificate error")
                                except Exception as ssl_config_error:
                                    logging.error(f"Error adding endpoint to SSL bypass: {str(ssl_config_error)}")
                            # Don't retry for API key errors
                            break
                        
                        # Don't retry if method not supported or other permanent errors
                        if error_code in [-32601, -32600]:  # Method not found or invalid request
                            logging.error(f"Method {method} not supported by {client.endpoint}, skipping retries")
                            break
                            
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logging.warning(f"Unexpected response format from {client.endpoint}: {response.keys()}")
                        errors_by_endpoint[client.endpoint] = f"Unexpected response format: {response.keys()}"
                        # Don't retry the same endpoint for invalid response formats
                        break
                elif isinstance(response, list):
                    # Some RPC endpoints return the result directly as a list
                    nodes_count = len(response)
                    if nodes_count > 0:
                        logging.info(f"Successfully retrieved {nodes_count} nodes from {client.endpoint} (direct list response) in {elapsed:.2f}s")
                        # Convert to the expected format
                        return {"result": response}
                    else:
                        logging.warning(f"getClusterNodes returned empty list (direct) from {client.endpoint}")
                        errors_by_endpoint[client.endpoint] = "Empty nodes list (direct)"
                        # Don't retry the same endpoint for empty lists
                        break
                else:
                    logging.warning(f"Unexpected response type from {client.endpoint}: {type(response)}")
                    errors_by_endpoint[client.endpoint] = f"Unexpected response type: {type(response)}"
                    # Don't retry the same endpoint for invalid response types
                    break
            
            # For other methods, just return the response
            return response
            
        except asyncio.TimeoutError:
            logging.warning(f"Timeout calling {method} on {client.endpoint} after {timeout:.2f}s (retry {retry+1}/{max_retries})")
            errors_by_endpoint[client.endpoint] = f"Timeout after {timeout:.2f}s"
            
            # Use exponential backoff for timeouts
            retry_delay = min(retry_delay * 1.5, 2.0)
            
        except aiohttp.ClientError as e:
            error_str = str(e)
            logging.error(f"Connection error calling {method} on {client.endpoint}: {error_str}")
            errors_by_endpoint[client.endpoint] = f"Connection error: {error_str}"
            
            # Check for SSL errors and add to bypass list
            if "SSL" in error_str or "certificate" in error_str.lower():
                try:
                    from .solana_ssl_config import add_ssl_bypass_endpoint
                    add_ssl_bypass_endpoint(client.endpoint)
                    logging.info(f"Added {client.endpoint} to SSL bypass list due to certificate error")
                    # Retry immediately with SSL verification bypassed
                    continue
                except Exception as ssl_config_error:
                    logging.error(f"Error adding endpoint to SSL bypass: {str(ssl_config_error)}")
            
            # Don't retry on other connection errors - likely endpoint is down
            break
            
        except Exception as e:
            error_str = str(e)
            logging.error(f"Error calling {method} on {client.endpoint}: {error_str}")
            errors_by_endpoint[client.endpoint] = error_str
            
            # Check for SSL errors and add to bypass list
            if "SSL" in error_str or "certificate" in error_str.lower():
                try:
                    from .solana_ssl_config import add_ssl_bypass_endpoint
                    add_ssl_bypass_endpoint(client.endpoint)
                    logging.info(f"Added {client.endpoint} to SSL bypass list due to certificate error")
                    # Retry immediately with SSL verification bypassed
                    continue
                except Exception as ssl_config_error:
                    logging.error(f"Error adding endpoint to SSL bypass: {str(ssl_config_error)}")
            
        # Wait before retrying
        if retry < max_retries - 1:
            # Use a shorter delay for getClusterNodes to speed up fallback
            if is_get_cluster_nodes:
                await asyncio.sleep(min(retry_delay, 0.5))
            else:
                await asyncio.sleep(retry_delay)
            
    # If we get here, all retries failed
    if is_get_cluster_nodes:
        logging.error(f"All {max_retries} retries failed for getClusterNodes on {client.endpoint}. Errors: {json.dumps(errors_by_endpoint)}")
    else:
        logging.error(f"All {max_retries} retries failed for {method}. Errors by endpoint: {json.dumps(errors_by_endpoint)}")
    
    # Return a structured error response
    return {
        "error": {
            "message": f"All {max_retries} retries failed for {method}",
            "details": errors_by_endpoint,
            "endpoint": client.endpoint if client else "unknown"
        },
        "_soleco_context": {
            "endpoint_errors": errors_by_endpoint,
            "method": method,
            "max_retries": max_retries,
            "timestamp": time.time()
        }
    }
