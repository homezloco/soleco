"""
Solana connection pool module for managing RPC connections with fallback support
"""

import logging
import asyncio
import os
from typing import Dict, Any, Optional, List
from solana.rpc.async_api import AsyncClient
import time
import functools
import aiohttp
import sys

# Configure logging
logger = logging.getLogger(__name__)

# Get Helius API key from environment
HELIUS_API_KEY = os.environ.get("HELIUS_API_KEY", "")

# Simple cache implementation
class SimpleCache:
    """Simple time-based cache for RPC responses"""
    
    def __init__(self, ttl_seconds=60):
        """Initialize the cache with a time-to-live in seconds"""
        self.cache = {}
        self.ttl_seconds = ttl_seconds
        
    def get(self, key):
        """Get a value from the cache if it exists and is not expired"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return value
            else:
                # Remove expired item
                del self.cache[key]
        return None
        
    def set(self, key, value):
        """Set a value in the cache with the current timestamp"""
        self.cache[key] = (value, time.time())
        
    def clear(self):
        """Clear the entire cache"""
        self.cache = {}
        
    def remove_expired(self):
        """Remove all expired items from the cache"""
        now = time.time()
        keys_to_remove = []
        for key, (_, timestamp) in self.cache.items():
            if now - timestamp >= self.ttl_seconds:
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self.cache[key]

# Create global cache instances with different TTLs
# Performance metrics cache - 30 seconds TTL
performance_cache = SimpleCache(ttl_seconds=30)
# Block production cache - 60 seconds TTL
block_production_cache = SimpleCache(ttl_seconds=60)
# Network status cache - 15 seconds TTL
network_status_cache = SimpleCache(ttl_seconds=15)
# RPC nodes cache - 2 minutes TTL
rpc_nodes_cache = SimpleCache(ttl_seconds=120)
# Mint analytics cache - 60 seconds TTL
mint_analytics_cache = SimpleCache(ttl_seconds=60)

class SolanaConnectionPool:
    """Pool of Solana RPC connections with fallback support"""
    
    # Class-level default endpoints
    DEFAULT_RPC_ENDPOINTS = [
        {"url": "https://api.mainnet-beta.solana.com", "name": "Solana Mainnet"},
        {"url": "https://rpc.ankr.com/solana", "name": "Ankr"}
    ]
    
    def __init__(self, endpoint=None):
        """Initialize the connection pool"""
        # If specific endpoint provided, use only that
        if endpoint is not None:
            if isinstance(endpoint, str):
                self.rpc_endpoints = [{'url': endpoint, 'name': 'Custom Endpoint'}]
            else:
                self.rpc_endpoints = endpoint
        else:
            self.rpc_endpoints = self.DEFAULT_RPC_ENDPOINTS
            
            # Always prioritize Helius if API key is available
            if HELIUS_API_KEY:
                helius_endpoint = {"url": f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}", "name": "Helius"}
                self.rpc_endpoints = [helius_endpoint] + self.rpc_endpoints
            
            # Add top performing endpoints as fallbacks
            top_performing_endpoints = [
                {"url": "http://173.231.14.98:8899", "name": "Fast RPC 1"},
                {"url": "http://107.182.163.194:8899", "name": "Fast RPC 2"},
                {"url": "http://66.45.229.34:8899", "name": "Fast RPC 3"},
                {"url": "http://38.58.176.230:8899", "name": "Fast RPC 4"},
                {"url": "http://147.75.198.219:8899", "name": "Fast RPC 5"}
            ]
            self.rpc_endpoints.extend(top_performing_endpoints)
        
        # Initialize client dictionary and tracking variables
        self.clients: Dict[str, AsyncClient] = {}
        self.endpoint_stats: Dict[str, Dict[str, Any]] = {}
        self.current_endpoint = 0
        self._initialized = False
        
    async def initialize(self, endpoints=None):
        """Initialize connections to all endpoints"""
        if endpoints is None:
            endpoints = self.rpc_endpoints

        if self._initialized:
            return

        # Validate endpoints
        if not isinstance(endpoints, (list, tuple)):
            raise ValueError('Endpoints must be a list or tuple')

        valid_endpoints = []
        for endpoint in endpoints:
            if isinstance(endpoint, str):
                if not endpoint.startswith(('http://', 'https://')):
                    raise ValueError(f'Invalid endpoint protocol: {endpoint}')
                if len(endpoint) < 10:  # Minimum length check
                    raise ValueError(f'Endpoint too short: {endpoint}')
                if not any(c.isalpha() for c in endpoint):
                    raise ValueError(f'Endpoint must contain at least one letter: {endpoint}')
                valid_endpoints.append({'url': endpoint, 'name': 'Custom Endpoint'})
            elif isinstance(endpoint, dict) and 'url' in endpoint:
                url = endpoint['url']
                if not url.startswith(('http://', 'https://')):
                    raise ValueError(f'Invalid endpoint protocol: {url}')
                if len(url) < 10:
                    raise ValueError(f'Endpoint too short: {url}')
                if not any(c.isalpha() for c in url):
                    raise ValueError(f'Endpoint must contain at least one letter: {url}')
                valid_endpoints.append(endpoint)
            else:
                raise ValueError(f'Invalid endpoint format: {endpoint}')

        if not valid_endpoints:
            raise ValueError('No valid endpoints provided')

        for endpoint in valid_endpoints:
            url = endpoint["url"]
            name = endpoint["name"]

            # Skip if endpoint has failed too many times
            if url in self.endpoint_stats and self.endpoint_stats[url]["failure_count"] > 3:
                logger.warning(f"Skipping {name} due to repeated failures")
                continue

            # Initialize stats
            self.endpoint_stats[url] = {
                "success_count": 0,
                "failure_count": 0,
                "avg_latency": 0,
                "last_latency": 0,
                "last_success": None
            }

            for attempt in range(3):  # Retry up to 3 times
                try:
                    client = AsyncClient(url, timeout=10.0)  # Increased timeout
                    # Test connection with timeout
                    start_time = time.time()
                    await asyncio.wait_for(client.get_version(), timeout=10.0)  # Increased timeout
                    latency = time.time() - start_time

                    self.clients[url] = client
                    self.endpoint_stats[url]["avg_latency"] = latency
                    self.endpoint_stats[url]["last_latency"] = latency
                    self.endpoint_stats[url]["success_count"] = 1
                    self.endpoint_stats[url]["last_success"] = time.time()

                    logger.info(f"Successfully connected to {name} (latency: {latency:.3f}s)")
                    break
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed to connect to {name}: {str(e)}")
                    self.endpoint_stats[url]["failure_count"] += 1
                    if attempt == 2:  # Last attempt failed
                        logger.error(f"Failed to connect to {name} after 3 attempts")
                    await asyncio.sleep(1)  # Wait before retry

        if not self.clients:
            raise ConnectionError("Failed to connect to any RPC endpoint")

        self._sort_endpoints_by_performance()
        self._initialized = True
        
    async def initialize_with_defaults(self):
        """Initialize the pool with default endpoints"""
        await self.initialize(self.DEFAULT_RPC_ENDPOINTS)
        
    def _sort_endpoints_by_performance(self):
        """Sort endpoints by performance (success rate and latency)"""
        # Create a list of (url, stats) tuples
        endpoint_items = [(url, stats) for url, stats in self.endpoint_stats.items() 
                         if url in self.clients]  # Only consider working endpoints
        
        # Sort by success rate (desc) and then by latency (asc)
        def sort_key(item):
            url, stats = item
            success_rate = stats["success_count"] / max(stats["success_count"] + stats["failure_count"], 1)
            return (-success_rate, stats["avg_latency"])
            
        sorted_endpoints = sorted(endpoint_items, key=sort_key)
        
        # Reorder rpc_endpoints based on performance
        url_to_endpoint = {endpoint["url"]: endpoint for endpoint in self.rpc_endpoints}
        self.rpc_endpoints = [url_to_endpoint[url] for url, _ in sorted_endpoints if url in url_to_endpoint]
        
        # Add back any endpoints that weren't in the sorted list (those that failed to connect)
        connected_urls = {url for url, _ in sorted_endpoints}
        for endpoint in list(self.rpc_endpoints):
            if endpoint["url"] not in connected_urls:
                self.rpc_endpoints.append(endpoint)
                
    def get_endpoint_stats(self):
        """Get statistics about endpoint performance"""
        stats = []
        for endpoint in self.rpc_endpoints:
            url = endpoint["url"]
            if url in self.endpoint_stats:
                endpoint_stat = self.endpoint_stats[url].copy()
                endpoint_stat["url"] = url
                endpoint_stat["name"] = endpoint["name"]
                
                # Calculate success rate
                total_requests = endpoint_stat["success_count"] + endpoint_stat["failure_count"]
                success_rate = endpoint_stat["success_count"] / max(total_requests, 1)
                endpoint_stat["success_rate"] = round(success_rate * 100, 2)
                
                stats.append(endpoint_stat)
                
        return {
            "endpoints": stats,
            "total_endpoints": len(stats),
            "active_endpoints": sum(1 for stat in stats if stat["success_count"] > 0),
            "average_latency": sum(stat["avg_latency"] for stat in stats) / max(len(stats), 1)
        }
        
    async def get_client(self) -> AsyncClient:
        """Get a working client, trying fallbacks if needed"""
        if not self._initialized:
            await self.initialize()
            
        # Try endpoints in order of priority (which is based on performance)
        for i in range(len(self.rpc_endpoints)):
            endpoint = self.rpc_endpoints[i]
            url = endpoint["url"]
            
            # Skip endpoints with too many failures (more than 3 consecutive failures)
            if url in self.endpoint_stats and self.endpoint_stats[url]["failure_count"] > 3:
                # But don't skip if it's been more than 5 minutes since the last failure
                import time
                if self.endpoint_stats[url].get("last_success") is None or \
                   time.time() - self.endpoint_stats[url].get("last_success", 0) > 300:
                    # Reset failure count to give it another chance
                    self.endpoint_stats[url]["failure_count"] = 0
                else:
                    logger.debug(f"Skipping endpoint {endpoint['name']} due to too many failures")
                    continue
            
            # Use existing client if available
            if url in self.clients:
                self.current_endpoint = i
                return self.clients[url]
                
            # Try to create a new client if not available
            try:
                logger.debug(f"Creating new client for {endpoint['name']}")
                client = AsyncClient(url)
                
                # Test connection and measure latency
                import time
                start_time = time.time()
                await client.get_version()
                latency = time.time() - start_time
                
                # Store client and update stats
                self.clients[url] = client
                
                # Update stats
                if url not in self.endpoint_stats:
                    self.endpoint_stats[url] = {
                        "success_count": 0,
                        "failure_count": 0,
                        "avg_latency": 0,
                        "last_latency": 0,
                        "last_success": None
                    }
                
                stats = self.endpoint_stats[url]
                stats["success_count"] += 1
                stats["last_success"] = time.time()
                stats["last_latency"] = latency
                
                # Update average latency with exponential moving average
                if stats["avg_latency"] == 0:
                    stats["avg_latency"] = latency
                else:
                    stats["avg_latency"] = 0.7 * stats["avg_latency"] + 0.3 * latency
                
                self.current_endpoint = i
                return client
            except Exception as e:
                logger.warning(f"Failed to connect to {endpoint['name']}: {str(e)}")
                
                # Update failure stats
                if url in self.endpoint_stats:
                    self.endpoint_stats[url]["failure_count"] += 1
                
        # If we get here, all endpoints failed
        raise ConnectionError("Failed to connect to any RPC endpoint")
        
    async def close(self):
        """Close all connections"""
        for client in self.clients.values():
            try:
                await client.close()
            except Exception as e:
                logger.error(f"Error closing client: {str(e)}")
                
        self.clients = {}
        self._initialized = False
        
    def update_endpoint_performance(self, client, success, latency=None):
        """Update performance metrics for an endpoint"""
        # Find the endpoint URL for this client
        endpoint_url = None
        for url, c in self.clients.items():
            if c == client:
                endpoint_url = url
                break
                
        if not endpoint_url or endpoint_url not in self.endpoint_stats:
            return
            
        stats = self.endpoint_stats[endpoint_url]
        
        if success:
            stats["success_count"] += 1
            import time
            stats["last_success"] = time.time()
            
            if latency is not None:
                stats["last_latency"] = latency
                # Update average latency with exponential moving average
                if stats["avg_latency"] == 0:
                    stats["avg_latency"] = latency
                else:
                    stats["avg_latency"] = 0.7 * stats["avg_latency"] + 0.3 * latency
        else:
            stats["failure_count"] += 1
            
        # Re-sort endpoints periodically based on performance
        if (stats["success_count"] + stats["failure_count"]) % 10 == 0:
            self._sort_endpoints_by_performance()
            
    class ClientContextManager:
        """Context manager for client acquisition"""
        def __init__(self, pool):
            self.pool = pool
            self.client = None
            self.start_time = None
            
        async def __aenter__(self):
            import time
            self.client = await self.pool.get_client()
            self.start_time = time.time()
            return self.client
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            import time
            latency = time.time() - self.start_time if self.start_time else None
            success = exc_type is None
            self.pool.update_endpoint_performance(self.client, success, latency)
            
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
        
    async def get_specific_client(self, target_endpoint: str) -> Optional[AsyncClient]:
        """
        Get a client for a specific endpoint.
        
        Args:
            target_endpoint: The endpoint URL to get a client for
            
        Returns:
            AsyncClient or None if the endpoint is not in the pool
        """
        try:
            # Normalize the endpoint URL for comparison
            target_endpoint = target_endpoint.strip().rstrip('/')
            
            # First check if we already have a client for this endpoint
            for endpoint, client in self.clients.items():
                normalized_endpoint = endpoint.strip().rstrip('/')
                if normalized_endpoint == target_endpoint:
                    logger.debug(f"Found existing client for endpoint {target_endpoint}")
                    return client
                
            # If not found by exact match, try to find by partial match (for API keys)
            for endpoint, client in self.clients.items():
                # For Helius endpoints, the API key might be different but the base URL is the same
                if "helius-rpc.com" in endpoint.lower() and "helius-rpc.com" in target_endpoint.lower():
                    logger.debug(f"Found Helius client (different API key) for {target_endpoint}")
                    return client
            
            # If we don't have a client for this endpoint, create one
            logger.info(f"Creating new client for specific endpoint {target_endpoint}")
            client = AsyncClient(target_endpoint)
            self.clients[target_endpoint] = client
            return client
            
        except Exception as e:
            logger.error(f"Error getting specific client for {target_endpoint}: {str(e)}")
            return None
        
    def _sanitize_url(self, url):
        """
        Sanitize URL by removing API keys and other sensitive information.
        
        Args:
            url (str): The URL to sanitize
            
        Returns:
            str: Sanitized URL
        """
        import re
        
        # Sanitize API keys in query parameters
        if '?' in url and ('api-key=' in url.lower() or 'apikey=' in url.lower()):
            base_url, params = url.split('?', 1)
            sanitized_params = []
            
            for param in params.split('&'):
                if 'api-key=' in param.lower() or 'apikey=' in param.lower():
                    key, value = param.split('=', 1)
                    sanitized_params.append(f"{key}=REDACTED")
                else:
                    sanitized_params.append(param)
            
            return f"{base_url}?{'&'.join(sanitized_params)}"
        
        return url
        
    async def get_slot(self, timeout: Optional[float] = None) -> int:
        """
        Get the current slot from the RPC endpoint.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            int: Current slot number
        """
        client = await self.get_client()
        try:
            slot_resp = await client.get_slot()
            return slot_resp.value
        finally:
            await self.release_client(client)

    async def get_version(self) -> dict:
        """
        Get the Solana version from the RPC endpoint.

        Returns:
            dict: Version information from the RPC endpoint
        """
        client = await self.get_client()
        try:
            version = await client.get_version()
            version_str = str(version)
            # Extract version number from string like 'GetVersionResp(RpcVersionInfo(2.1.11))'
            version_num = version_str.split('(')[-1].rstrip(')')
            return {
                'result': {
                    'solana-core': version_num,
                    'feature-set': version.feature_set if hasattr(version, 'feature_set') else None,
                    'protocol-version': version.protocol_version if hasattr(version, 'protocol_version') else None
                }
            }
        finally:
            await self.release_client(client)

    async def get_block_height(self) -> int:
        """
        Get the current block height from the RPC endpoint.

        Returns:
            int: Current block height
        """
        client = await self.get_client()
        try:
            response = await client.get_block_height()
            return response.value
        finally:
            await self.release_client(client)

    async def release_client(self, client):
        pass

    async def get_rpc_stats(self):
        """
        Get detailed statistics about RPC endpoint performance.
        
        Returns:
            Dict: Detailed statistics about each endpoint and summary metrics
        """
        if not self._initialized:
            return {
                "status": "not_initialized",
                "endpoints": [],
                "summary": {
                    "total_endpoints": len(self.rpc_endpoints),
                    "active_endpoints": 0,
                    "average_latency": 0,
                    "total_success": 0,
                    "total_failures": 0
                }
            }
            
        # Get detailed stats for each endpoint
        endpoints_stats = []
        total_success = 0
        total_failures = 0
        active_endpoints = 0
        latencies = []
        
        for endpoint in self.rpc_endpoints:
            url = endpoint["url"]
            name = endpoint["name"]
            
            # Skip Helius endpoints for security (API key protection)
            if "helius" in url.lower():
                continue
                
            # Skip endpoints without stats
            if url not in self.endpoint_stats:
                continue
                
            stats = self.endpoint_stats[url]
            success_count = stats.get("success_count", 0)
            failure_count = stats.get("failure_count", 0)
            total_requests = success_count + failure_count
            
            # Calculate success rate
            success_rate = success_count / max(total_requests, 1) * 100
            
            # Update totals
            total_success += success_count
            total_failures += failure_count
            if success_count > 0:
                active_endpoints += 1
                latencies.append(stats.get("avg_latency", 0))
                
            # Format last success time
            last_success = stats.get("last_success")
            if last_success:
                import datetime
                last_success_str = datetime.datetime.fromtimestamp(last_success).strftime('%Y-%m-%d %H:%M:%S')
            else:
                last_success_str = "Never"
                
            # Add endpoint stats with sanitized URL
            endpoints_stats.append({
                "url": self._sanitize_url(url),
                "name": name,
                "success_count": success_count,
                "failure_count": failure_count,
                "total_requests": total_requests,
                "success_rate": round(success_rate, 2),
                "avg_latency": round(stats.get("avg_latency", 0), 3),
                "last_latency": round(stats.get("last_latency", 0), 3),
                "last_success": last_success_str,
                "is_active": url in self.clients
            })
            
        # Sort endpoints by success rate (desc) and then by latency (asc)
        endpoints_stats.sort(key=lambda x: (-x["success_rate"], x["avg_latency"]))
        
        # Calculate summary metrics
        avg_latency = sum(latencies) / max(len(latencies), 1)
        
        return {
            "status": "initialized",
            "endpoints": endpoints_stats,
            "summary": {
                "total_endpoints": len(self.rpc_endpoints),
                "active_endpoints": active_endpoints,
                "average_latency": round(avg_latency, 3),
                "total_success": total_success,
                "total_failures": total_failures,
                "overall_success_rate": round(total_success / max(total_success + total_failures, 1) * 100, 2)
            }
        }

    def get_filtered_rpc_stats(self):
        """
        Get detailed statistics about RPC endpoint performance, excluding Helius endpoints.
        
        Returns:
            Dict: Detailed statistics about each endpoint and summary metrics, with Helius endpoints filtered out
        """
        # Get the full stats first
        stats = self.get_rpc_stats()
        
        # Filter out Helius endpoints from stats
        filtered_stats = {}
        for url, stat in stats.get("stats", {}).items():
            if "helius" not in url.lower():
                filtered_stats[url] = stat
                
        # Get detailed stats for endpoints
        endpoints_stats = []
        total_success = 0
        total_failures = 0
        active_endpoints = 0
        latencies = []
        
        for endpoint in self.rpc_endpoints:
            url = endpoint["url"]
            name = endpoint["name"]
            
            # Skip Helius endpoints
            if "helius" in url.lower():
                continue
                
            # Skip endpoints without stats
            if url not in self.endpoint_stats:
                continue
                
            stats = self.endpoint_stats[url]
            success_count = stats.get("success_count", 0)
            failure_count = stats.get("failure_count", 0)
            total_requests = success_count + failure_count
            
            # Calculate success rate
            success_rate = success_count / max(total_requests, 1) * 100
            
            # Update totals
            total_success += success_count
            total_failures += failure_count
            if success_count > 0:
                active_endpoints += 1
                latencies.append(stats.get("avg_latency", 0))
                
            # Format last success time
            last_success = stats.get("last_success")
            if last_success:
                import datetime
                last_success_str = datetime.datetime.fromtimestamp(last_success).strftime('%Y-%m-%d %H:%M:%S')
            else:
                last_success_str = "Never"
                
            # Add endpoint stats with sanitized URL
            endpoints_stats.append({
                "url": self._sanitize_url(url),
                "name": name,
                "success_count": success_count,
                "failure_count": failure_count,
                "total_requests": total_requests,
                "success_rate": round(success_rate, 2),
                "avg_latency": round(stats.get("avg_latency", 0), 3),
                "last_latency": round(stats.get("last_latency", 0), 3),
                "last_success": last_success_str,
                "is_active": url in self.clients
            })
            
        # Sort endpoints by success rate (desc) and then by latency (asc)
        endpoints_stats.sort(key=lambda x: (-x["success_rate"], x["avg_latency"]))
        
        # Calculate summary metrics
        avg_latency = sum(latencies) / max(len(latencies), 1)
        
        # Get top performers (excluding Helius)
        top_performers = []
        for endpoint in endpoints_stats:
            if endpoint["success_count"] > 0:
                top_performers.append({
                    "endpoint": endpoint["url"],
                    "avg_latency": endpoint["avg_latency"],
                    "success_rate": endpoint["success_rate"],
                    "success_count": endpoint["success_count"],
                    "failure_count": endpoint["failure_count"]
                })
                
        # Sort and limit to top 5
        top_performers.sort(key=lambda x: (-x["success_rate"], x["avg_latency"]))
        top_performers = top_performers[:5]
        
        return {
            "status": "initialized",
            "endpoints": endpoints_stats,
            "stats": filtered_stats,
            "top_performers": top_performers,
            "summary": {
                "total_endpoints": len(endpoints_stats),
                "active_endpoints": active_endpoints,
                "average_latency": round(avg_latency, 3),
                "total_success": total_success,
                "total_failures": total_failures,
                "overall_success_rate": round(total_success / max(total_success + total_failures, 1) * 100, 2)
            }
        }

_connection_pool = None

async def get_connection_pool() -> SolanaConnectionPool:
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = SolanaConnectionPool()
        await _connection_pool.initialize_with_defaults()
    return _connection_pool
