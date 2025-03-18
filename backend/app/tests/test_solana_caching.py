import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.database.sqlite import db_cache
from app.constants.cache import (
    NETWORK_STATUS_CACHE_TTL,
    PERFORMANCE_METRICS_CACHE_TTL,
    RPC_NODES_CACHE_TTL,
    TOKEN_INFO_CACHE_TTL
)

client = TestClient(app)

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

def test_network_status_caching():
    # Clear any existing cache
    db_cache.clear_cache("network-status")
    
    # First request should hit the API
    response1 = client.get("/api/solana/network/status")
    assert response1.status_code == 200
    
    # Get the timestamp from the first response
    timestamp1 = response1.json().get("timestamp")
    
    # Second request should use the cache
    response2 = client.get("/api/solana/network/status")
    assert response2.status_code == 200
    
    # Timestamps should be the same since we're using cached data
    timestamp2 = response2.json().get("timestamp")
    assert timestamp1 == timestamp2
    
    # Force refresh should bypass the cache
    response3 = client.get("/api/solana/network/status?refresh=true")
    assert response3.status_code == 200
    
    # Timestamps should be different since we forced a refresh
    timestamp3 = response3.json().get("timestamp")
    assert timestamp1 != timestamp3

def test_performance_metrics_caching():
    # Clear any existing cache
    db_cache.clear_cache("performance-metrics")
    
    # First request should hit the API
    response1 = client.get("/api/solana/performance/metrics")
    assert response1.status_code == 200
    
    # Get the timestamp from the first response
    timestamp1 = response1.json().get("timestamp")
    
    # Second request should use the cache
    response2 = client.get("/api/solana/performance/metrics")
    assert response2.status_code == 200
    
    # Timestamps should be the same since we're using cached data
    timestamp2 = response2.json().get("timestamp")
    assert timestamp1 == timestamp2
    
    # Force refresh should bypass the cache
    response3 = client.get("/api/solana/performance/metrics?refresh=true")
    assert response3.status_code == 200
    
    # Timestamps should be different since we forced a refresh
    timestamp3 = response3.json().get("timestamp")
    assert timestamp1 != timestamp3

def test_rpc_nodes_caching():
    # Clear any existing cache
    db_cache.clear_cache("rpc-nodes")
    
    # First request should hit the API
    response1 = client.get("/api/solana/rpc-nodes")
    assert response1.status_code == 200
    
    # Get the timestamp from the first response
    timestamp1 = response1.json().get("timestamp")
    
    # Second request should use the cache
    response2 = client.get("/api/solana/rpc-nodes")
    assert response2.status_code == 200
    
    # Timestamps should be the same since we're using cached data
    timestamp2 = response2.json().get("timestamp")
    assert timestamp1 == timestamp2
    
    # Force refresh should bypass the cache
    response3 = client.get("/api/solana/rpc-nodes?refresh=true")
    assert response3.status_code == 200
    
    # Timestamps should be different since we forced a refresh
    timestamp3 = response3.json().get("timestamp")
    assert timestamp1 != timestamp3

def test_token_info_caching():
    # Use a known token address for testing
    token_address = "So11111111111111111111111111111111111111112"  # SOL wrapped token
    
    # Clear any existing cache
    db_cache.clear_cache("token-info")
    
    # First request should hit the API
    response1 = client.get(f"/api/solana/token/{token_address}")
    assert response1.status_code == 200
    
    # Get the timestamp from the first response
    timestamp1 = response1.json().get("timestamp")
    
    # Second request should use the cache
    response2 = client.get(f"/api/solana/token/{token_address}")
    assert response2.status_code == 200
    
    # Timestamps should be the same since we're using cached data
    timestamp2 = response2.json().get("timestamp")
    assert timestamp1 == timestamp2
    
    # Force refresh should bypass the cache
    response3 = client.get(f"/api/solana/token/{token_address}?refresh=true")
    assert response3.status_code == 200
    
    # Timestamps should be different since we forced a refresh
    timestamp3 = response3.json().get("timestamp")
    assert timestamp1 != timestamp3
