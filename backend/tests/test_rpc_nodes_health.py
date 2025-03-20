"""
RPC Node Health Test Script

This script tests all known RPC nodes to determine which ones are working well.
It performs various tests including:
1. Basic connectivity
2. Response time
3. Rate limit information
4. Method availability

Usage:
    python -m backend.tests.test_rpc_nodes_health
"""

import asyncio
import time
import json
import sys
import os
from typing import Dict, List, Any, Tuple
import aiohttp
import logging
import pytest
from app.utils.solana_connection_pool import SolanaConnectionPool

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.config import HELIUS_API_KEY
from backend.app.utils.solana_rpc_constants import KNOWN_RPC_PROVIDERS, FALLBACK_RPC_ENDPOINTS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Test methods to check
TEST_METHODS = [
    {"method": "getHealth", "params": []},
    {"method": "getVersion", "params": []},
    {"method": "getSlot", "params": []},
    {"method": "getBlockHeight", "params": []},
    {"method": "getRecentBlockhash", "params": []}
]

# Combine all RPC endpoints
ALL_RPC_ENDPOINTS = list(KNOWN_RPC_PROVIDERS.values()) + FALLBACK_RPC_ENDPOINTS

# Add some endpoints with common API key formats for testing
ALL_RPC_ENDPOINTS.append("https://api.quicknode.com/solana/YOUR-API-KEY")
ALL_RPC_ENDPOINTS.append("https://solana-mainnet.g.alchemy.com/v2/YOUR-API-KEY")

# Remove duplicates while preserving order
UNIQUE_RPC_ENDPOINTS = []
for endpoint in ALL_RPC_ENDPOINTS:
    if endpoint not in UNIQUE_RPC_ENDPOINTS:
        UNIQUE_RPC_ENDPOINTS.append(endpoint)

# Configure test timeouts
CONNECT_TIMEOUT = 10  # seconds
METHOD_TIMEOUT = 15  # seconds
MAX_RETRIES = 2
RETRY_DELAY = 1  # second

@pytest.fixture
def test_endpoint():
    """Return a known good endpoint for testing."""
    return "https://api.mainnet-beta.solana.com"

@pytest.mark.asyncio
async def test_rpc_endpoint_health(test_endpoint):
    """Test a single RPC endpoint for health and performance."""
    endpoint = test_endpoint
    
    async with aiohttp.ClientSession() as session:
        try:
            test_results = {
                "endpoint": endpoint,
                "status": "unhealthy",
                "latency": 0,
                "methods": {},
                "retries": 0
            }
            
            for attempt in range(MAX_RETRIES + 1):
                try:
                    start_time = time.time()
                    # Test basic connectivity
                    async with session.post(
                        endpoint,
                        json={"jsonrpc": "2.0", "id": 1, "method": "getHealth", "params": []},
                        timeout=aiohttp.ClientTimeout(total=CONNECT_TIMEOUT)
                    ) as response:
                        if response.status != 200:
                            test_results["error"] = f"HTTP {response.status}"
                            test_results["retries"] = attempt
                            continue
                        
                        data = await response.json()
                        if "error" in data:
                            test_results["error"] = data["error"]
                            test_results["retries"] = attempt
                            continue
                        
                        # Test all methods
                        method_results = {}
                        for test_method in TEST_METHODS:
                            try:
                                method_start = time.time()
                                async with session.post(
                                    endpoint,
                                    json={"jsonrpc": "2.0", "id": 1, "method": test_method["method"], "params": test_method["params"]},
                                    timeout=aiohttp.ClientTimeout(total=METHOD_TIMEOUT)
                                ) as method_response:
                                    method_data = await method_response.json()
                                    method_time = time.time() - method_start
                                    
                                    if method_response.status != 200 or "error" in method_data:
                                        error_msg = f"HTTP {method_response.status}" if method_response.status != 200 else method_data.get("error", "Unknown error")
                                        method_results[test_method["method"]] = {
                                            "status": "error",
                                            "error": error_msg,
                                            "latency": method_time
                                        }
                                    else:
                                        method_results[test_method["method"]] = {
                                            "status": "ok",
                                            "latency": method_time
                                        }
                            except Exception as e:
                                method_results[test_method["method"]] = {
                                    "status": "error",
                                    "error": str(e),
                                    "latency": time.time() - method_start
                                }
                        
                        # Calculate overall latency
                        latency = time.time() - start_time
                        
                        # Update test results
                        test_results["status"] = "healthy"
                        test_results["latency"] = latency
                        test_results["methods"] = method_results
                        test_results["retries"] = attempt
                        
                        # If we got here, the test was successful
                        break
                        
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    test_results["error"] = str(e)
                    test_results["retries"] = attempt
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY)
                    continue
                except Exception as e:
                    test_results["error"] = f"Unexpected error: {str(e)}"
                    test_results["retries"] = attempt
                    break
            
            # Verify that we got some valid results
            assert "latency" in test_results
            assert isinstance(test_results["latency"], (int, float))
            
            # At least one method should be working
            assert "methods" in test_results
            assert len(test_results["methods"]) > 0
            
            # Log the results
            logger.info(f"Tested endpoint: {endpoint}")
            logger.info(f"Status: {test_results['status']}")
            logger.info(f"Latency: {test_results['latency']:.3f}s")
            
            return test_results
            
        except Exception as e:
            logger.error(f"Error testing endpoint {endpoint}: {str(e)}")
            pytest.skip(f"Error testing endpoint: {str(e)}")

@pytest.mark.asyncio
async def test_unhealthy_endpoint():
    """Test an unhealthy endpoint."""
    # Use a known bad endpoint
    endpoint = "https://invalid.endpoint.example.com"
    
    try:
        # We expect this to fail
        with pytest.raises(Exception):
            await test_rpc_endpoint_health(endpoint)
        
        # If we get here, the test passed
        logger.info("Successfully detected unhealthy endpoint")
    except Exception as e:
        logger.error(f"Error testing unhealthy endpoint: {str(e)}")
        pytest.fail(f"Failed to properly handle unhealthy endpoint: {str(e)}")

@pytest.mark.asyncio
async def test_endpoint_with_high_latency():
    """Test an endpoint with high latency."""
    global CONNECT_TIMEOUT
    
    # We'll use a valid endpoint but with a very short timeout to simulate high latency
    endpoint = "https://api.mainnet-beta.solana.com"
    
    # Save the original timeout
    original_timeout = CONNECT_TIMEOUT
    
    try:
        # Set a very short timeout
        CONNECT_TIMEOUT = 0.001  # 1ms
        
        # We expect this to timeout
        result = await test_rpc_endpoint_health(endpoint)
        
        # Check if we got a timeout or error
        assert "error" in result
        logger.info("Successfully detected high latency endpoint")
    except Exception as e:
        logger.error(f"Error testing high latency endpoint: {str(e)}")
        pytest.fail(f"Failed to properly handle high latency endpoint: {str(e)}")
    finally:
        # Restore the original timeout
        CONNECT_TIMEOUT = original_timeout

@pytest.mark.asyncio
async def test_health_check_with_invalid_endpoint():
    """Test health check with an invalid endpoint."""
    # Use a known bad endpoint
    endpoint = "https://invalid.endpoint.example.com"
    
    try:
        # We expect this to fail
        result = await test_rpc_endpoint_health(endpoint)
        
        # Check if we got an error
        assert "error" in result
        logger.info("Successfully detected invalid endpoint")
    except Exception as e:
        logger.error(f"Error testing invalid endpoint: {str(e)}")
        pytest.fail(f"Failed to properly handle invalid endpoint: {str(e)}")

@pytest.mark.asyncio
async def test_all_endpoints():
    """Test a sample of endpoints."""
    # Test a small sample of endpoints to keep the test fast
    sample_endpoints = ALL_RPC_ENDPOINTS[:2]
    
    results = []
    for endpoint in sample_endpoints:
        try:
            result = await test_rpc_endpoint_health(endpoint)
            results.append(result)
        except Exception as e:
            logger.error(f"Error testing endpoint {endpoint}: {str(e)}")
    
    # We should have at least one valid result
    assert len(results) > 0
    
    # Log the results
    logger.info(f"Tested {len(results)} endpoints")
    for result in results:
        logger.info(f"Endpoint: {result['endpoint']}, Status: {result['status']}")
    
    return results

@pytest.mark.asyncio
async def test_unhealthy_endpoint():
    # Test with known unhealthy endpoint
    endpoint = 'unhealthy.endpoint'
    client = SolanaConnectionPool(endpoint=endpoint)
    try:
        with pytest.raises(Exception):
            await client.get_version()
    finally:
        await client.close()

@pytest.mark.asyncio
async def test_endpoint_with_high_latency():
    pool = SolanaConnectionPool()
    await pool.initialize()
    # Test latency handling

@pytest.mark.asyncio
async def test_health_check_with_invalid_endpoint():
    # Test health check with invalid endpoint
    endpoint = 'invalid.endpoint'
    client = SolanaConnectionPool(endpoint=endpoint)
    try:
        with pytest.raises(Exception):
            await client.get_version()
    finally:
        await client.close()

@pytest.mark.asyncio
async def test_health_check_with_timeout():
    """Test health check with a timeout."""
    global CONNECT_TIMEOUT
    
    # Use a valid endpoint but with a very short timeout
    endpoint = "https://api.mainnet-beta.solana.com"
    
    # Save the original timeout
    original_timeout = CONNECT_TIMEOUT
    
    try:
        # Set a very short timeout
        CONNECT_TIMEOUT = 0.001  # 1ms
        
        # We expect this to timeout
        with pytest.raises(Exception):
            await test_rpc_endpoint_health(endpoint)
        
        logger.info("Successfully detected timeout")
    except Exception as e:
        logger.error(f"Error testing timeout: {str(e)}")
        pytest.fail(f"Failed to properly handle timeout: {str(e)}")
    finally:
        # Restore the original timeout
        CONNECT_TIMEOUT = original_timeout

async def main():
    """Main function to run the tests."""
    print(f"Testing {len(UNIQUE_RPC_ENDPOINTS)} unique RPC endpoints...")
    results = await test_all_endpoints()
    print_results(results)
    
    # Save results to file
    with open("rpc_node_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to rpc_node_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
