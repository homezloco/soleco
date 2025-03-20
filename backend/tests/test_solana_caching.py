import pytest
import asyncio
from httpx import AsyncClient
from fastapi import FastAPI
from app.routers.solana_network import router as solana_network_router
from app.routers.solana_rpc_nodes import router as solana_rpc_nodes_router
from app.routers.solana import router as solana_router
from app.utils.solana_query import SolanaQueryHandler
from app.utils.cache.database_cache import DatabaseCache
from app.utils.solana_connection_pool import SolanaConnectionPool, get_connection_pool
from app.constants.cache import (
    NETWORK_STATUS_CACHE_TTL,
    PERFORMANCE_METRICS_CACHE_TTL,
    RPC_NODES_CACHE_TTL,
    TOKEN_INFO_CACHE_TTL
)
from unittest.mock import Mock, AsyncMock, patch
import os

# Check if we're running in a CI environment
def is_ci_environment():
    return os.environ.get("CI", "false").lower() == "true"

# Initialize db_cache
db_cache = DatabaseCache()

@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(solana_network_router)
    app.include_router(solana_rpc_nodes_router)
    app.include_router(solana_router)
    return app

@pytest.fixture
def async_client(app):
    return AsyncClient(app=app, base_url="http://test")

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment as it requires a running server")
async def test_network_status_caching(async_client):
    # Clear any existing cache
    await db_cache.clear_cache("network-status")
    
    # Mock the API call
    with patch('app.routers.solana_network.get_network_status') as mock_get_network_status:
        mock_get_network_status.return_value = {'timestamp': 'mocked_timestamp'}
        
        # First request should hit the API
        response1 = await async_client.get("/network/status")
        assert response1.status_code == 200
        assert response1.json().get("timestamp") == 'mocked_timestamp'
        
        # Get the timestamp from the first response
        timestamp1 = response1.json().get("timestamp")
        
        # Second request should use the cache
        response2 = await async_client.get("/network/status")
        assert response2.status_code == 200
        
        # Timestamps should be same since we're using cached data
        timestamp2 = response2.json().get("timestamp")
        assert timestamp1 == timestamp2, f"Timestamps don't match: {timestamp1} != {timestamp2}"
        
        # Force refresh should bypass the cache
        response3 = await async_client.get("/network/status?refresh=true")
        assert response3.status_code == 200
        
        # Timestamps should be different since we forced a refresh
        timestamp3 = response3.json().get("timestamp")
        assert timestamp1 != timestamp3

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment as it requires a running server")
async def test_performance_metrics_caching(async_client):
    # Clear any existing cache
    await db_cache.clear_cache("performance-metrics")
    
    # Mock the API call
    with patch('app.routers.solana.get_performance_metrics') as mock_get_performance_metrics:
        mock_get_performance_metrics.return_value = {'timestamp': 'mocked_timestamp'}
        
        # First request should hit the API
        response1 = await async_client.get("/performance/metrics")
        assert response1.status_code == 200
        
        # Get the timestamp from the first response
        timestamp1 = response1.json().get("timestamp")
        
        # Second request should use the cache
        response2 = await async_client.get("/performance/metrics")
        assert response2.status_code == 200
        
        # Timestamps should be same since we're using cached data
        timestamp2 = response2.json().get("timestamp")
        assert timestamp1 == timestamp2
        
        # Force refresh should bypass the cache
        response3 = await async_client.get("/performance/metrics?refresh=true")
        assert response3.status_code == 200
        
        # Timestamps should be different since we forced a refresh
        timestamp3 = response3.json().get("timestamp")
        assert timestamp1 != timestamp3

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment as it requires a running server")
async def test_rpc_nodes_caching(async_client):
    # Clear any existing cache
    await db_cache.clear_cache("rpc-nodes")
    
    # Mock the API call
    with patch('app.routers.solana_rpc_nodes.get_rpc_nodes') as mock_get_rpc_nodes:
        mock_get_rpc_nodes.return_value = {'timestamp': 'mocked_timestamp'}
        
        # First request should hit the API
        response1 = await async_client.get("/rpc-nodes")
        assert response1.status_code == 200
        timestamp1 = response1.json().get("timestamp")

        # Second request should use the cache
        response2 = await async_client.get("/rpc-nodes")
        assert response2.status_code == 200
        timestamp2 = response2.json().get("timestamp")
        assert timestamp1 == timestamp2

        # Force refresh should bypass the cache
        response3 = await async_client.get("/rpc-nodes?refresh=true")
        assert response3.status_code == 200
        timestamp3 = response3.json().get("timestamp")
        assert timestamp1 != timestamp3

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment as it requires a running server")
async def test_token_info_caching(async_client):
    cache = DatabaseCache()
    handler = SolanaQueryHandler(cache=cache)
    
    # Clear any existing cache
    await cache.clear_cache("token-info")
    
    # Mock token address
    token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
    
    # Mock the API call
    with patch('app.routers.solana.get_token_info') as mock_get_token_info:
        mock_get_token_info.return_value = {'timestamp': 'mocked_timestamp', 'token': token_address}
        
        # First request should hit the API
        response1 = await async_client.get(f"/token/{token_address}")
        assert response1.status_code == 200
        assert response1.json().get("token") == token_address
        
        # Second request should use the cache
        response2 = await async_client.get(f"/token/{token_address}")
        assert response2.status_code == 200
        
        # Force refresh should bypass the cache
        response3 = await async_client.get(f"/token/{token_address}?refresh=true")
        assert response3.status_code == 200
