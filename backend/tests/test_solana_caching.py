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
from unittest.mock import Mock, AsyncMock

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
async def test_network_status_caching(async_client):
    # Clear any existing cache
    await db_cache.clear_cache("network-status")
    
    # First request should hit the API
    response1 = await async_client.get("/network/status")
    assert response1.status_code == 200
    assert response1.json().get("timestamp") is not None
    
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
async def test_performance_metrics_caching(async_client):
    # Clear any existing cache
    await db_cache.clear_cache("performance-metrics")
    
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
async def test_rpc_nodes_caching(async_client):
    # Clear any existing cache
    await db_cache.clear_cache("rpc-nodes")
    
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
async def test_token_info_caching(async_client):
    cache = DatabaseCache()
    handler = SolanaQueryHandler(cache=cache)

    # Create proper async mock client
    mock_client = AsyncMock(spec=AsyncClient)
    mock_client.get_token_account_balance = AsyncMock(return_value={'result': {'value': {'mocked': 'data'}}})

    # Mock connection pool methods
    handler.connection_pool = Mock()
    handler.connection_pool.get_client = AsyncMock(return_value=mock_client)
    handler.connection_pool.release = AsyncMock()

    # Use a known token address for testing
    token_address = "So11111111111111111111111111111111111111112"  # SOL wrapped token

    # Clear any existing cache
    await handler.clear_token_cache()

    # Test with increased timeout
    result = await asyncio.wait_for(handler.get_token_info(token_address), timeout=60.0)
    assert result == {'mocked': 'data'}

    # Verify caching
    cached_result = await handler.get_cached_token_info(token_address)
    assert cached_result == result
