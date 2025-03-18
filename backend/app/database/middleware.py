"""
Database middleware for caching API responses.
"""
import json
import logging
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.database.sqlite import db_cache

# Configure logging
logger = logging.getLogger("app.database.middleware")

# Endpoints to cache
CACHEABLE_ENDPOINTS = [
    "/soleco/solana/network/status",
    "/soleco/solana/performance/metrics",
    "/soleco/network/rpc-nodes",
    "/soleco/mints/new/recent",
    "/soleco/pump_trending/pump/trending"
]

# TTL (Time to Live) for each endpoint in seconds
ENDPOINT_TTL = {
    "/soleco/solana/network/status": 300,  # 5 minutes
    "/soleco/solana/performance/metrics": 300,  # 5 minutes
    "/soleco/network/rpc-nodes": 1800,  # 30 minutes
    "/soleco/mints/new/recent": 600,  # 10 minutes
    "/soleco/pump_trending/pump/trending": 900  # 15 minutes
}

class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware for caching API responses.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and cache the response if applicable.
        
        Args:
            request: The incoming request
            call_next: The next middleware in the chain
            
        Returns:
            The response
        """
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Check if the endpoint is cacheable
        path = request.url.path
        if not any(path.endswith(endpoint) for endpoint in CACHEABLE_ENDPOINTS):
            return await call_next(request)
        
        # Get the endpoint from the path
        endpoint = next((e for e in CACHEABLE_ENDPOINTS if path.endswith(e)), None)
        if not endpoint:
            return await call_next(request)
        
        # Get the query parameters
        params = dict(request.query_params)
        
        # Try to get the cached response
        ttl = ENDPOINT_TTL.get(endpoint, 300)
        cached_data = db_cache.get_cached_data(endpoint, params, ttl)
        
        if cached_data:
            # Return the cached response
            logger.debug(f"Returning cached response for {endpoint}")
            
            # Store historical data if applicable
            self._store_historical_data(endpoint, cached_data, params)
            
            return Response(
                content=json.dumps(cached_data),
                media_type="application/json",
                headers={"X-Cache": "HIT"}
            )
        
        # Get the response from the next middleware
        response = await call_next(request)
        
        # Cache the response if it's successful
        if 200 <= response.status_code < 300 and response.headers.get("content-type", "").startswith("application/json"):
            try:
                # Check if the response has a body attribute (not a streaming response)
                if hasattr(response, 'body'):
                    # Get the response body
                    response_body = await response.body()
                    response_data = json.loads(response_body)
                    
                    # Cache the response
                    db_cache.cache_data(endpoint, response_data, params, ttl)
                    
                    # Store historical data if applicable
                    self._store_historical_data(endpoint, response_data, params)
                    
                    # Create a new response with the cached header
                    return Response(
                        content=response_body,
                        status_code=response.status_code,
                        headers={**dict(response.headers), "X-Cache": "MISS"},
                        media_type=response.media_type
                    )
                else:
                    logger.debug(f"Skipping cache for streaming response: {endpoint}")
            except Exception as e:
                logger.error(f"Error caching response for {endpoint}: {e}")
        
        return response
    
    def _store_historical_data(self, endpoint: str, data: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> None:
        """
        Store historical data for the given endpoint.
        
        Args:
            endpoint: API endpoint
            data: Response data
            params: Query parameters
        """
        try:
            if not data or not isinstance(data, dict):
                logger.debug(f"Skipping historical data storage for {endpoint}: Invalid data format")
                return
                
            if endpoint == "/soleco/solana/network/status":
                status = data.get("status", "unknown")
                db_cache.store_network_status(status, json.dumps(data))
            
            elif endpoint == "/soleco/mints/new/recent":
                blocks = int(params.get("blocks", 2))
                new_mints_count = len(data.get("new_mints", []))
                pump_tokens_count = len(data.get("pump_tokens", []))
                db_cache.store_mint_analytics(blocks, new_mints_count, pump_tokens_count, json.dumps(data))
            
            elif endpoint == "/soleco/pump_trending/pump/trending":
                timeframe = params.get("timeframe", "24h")
                sort_metric = params.get("sort_metric", "volume")
                tokens_count = len(data.get("tokens", []))
                db_cache.store_pump_tokens(timeframe, sort_metric, tokens_count, json.dumps(data))
            
            elif endpoint == "/soleco/network/rpc-nodes":
                total_nodes = data.get("total_nodes", 0)
                db_cache.store_rpc_nodes(total_nodes, json.dumps(data))
            
            elif endpoint == "/soleco/solana/performance/metrics":
                tps_stats = data.get("tps_statistics", {})
                max_tps = tps_stats.get("max", 0)
                avg_tps = tps_stats.get("avg", 0)
                db_cache.store_performance_metrics(max_tps, avg_tps, json.dumps(data))
        
        except Exception as e:
            logger.error(f"Error storing historical data for {endpoint}: {e}")
