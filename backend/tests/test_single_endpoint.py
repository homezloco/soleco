"""
Test individual Solana RPC endpoints with different timeout settings.

This script helps diagnose connectivity issues with specific endpoints.
"""
import asyncio
import logging
import time
import sys
import os
from typing import Dict, Any
import pytest

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app.utils.solana_rpc import SolanaClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# The endpoint to test
TEST_ENDPOINT = "https://api.mainnet-beta.solana.com"

# Check if we're running in a CI environment
def is_ci_environment():
    """Check if we're running in a CI environment"""
    return os.environ.get('CI') == 'true'

async def test_with_timeout(timeout: float) -> Dict[str, Any]:
    """
    Test a specific RPC endpoint with a given timeout.
    
    Args:
        timeout: The timeout for the request in seconds
        
    Returns:
        Dict[str, Any]: Test results
    """
    start_time = time.time()
    client = None
    result = {
        "endpoint": TEST_ENDPOINT,
        "timeout": timeout,
        "success": False,
        "response_time": None,
        "error": None,
        "health": None,
        "version": None
    }
    
    try:
        # Create a client for this endpoint
        client = SolanaClient(endpoint=TEST_ENDPOINT, timeout=timeout)
        
        logger.info(f"Testing endpoint {TEST_ENDPOINT} with timeout {timeout}s")
        
        # Test basic methods with timeout
        try:
            health_result = await asyncio.wait_for(client._make_rpc_call("getHealth", []), timeout)
            result["health"] = health_result
        except Exception as e:
            logger.warning(f"Health check failed: {str(e)}")
            result["health"] = {"error": str(e)}
        
        try:
            version_result = await asyncio.wait_for(client.get_version(), timeout)
            result["version"] = version_result
        except Exception as e:
            logger.warning(f"Version check failed: {str(e)}")
            result["version"] = {"error": str(e)}
        
        response_time = time.time() - start_time
        result["response_time"] = response_time
        
        # If we got here with at least one successful call, mark as success
        if result["health"] and not isinstance(result["health"], dict) or \
           result["version"] and not isinstance(result["version"], dict):
            result["success"] = True
        
        logger.info(f"Test completed in {response_time:.3f}s")
        return result
        
    except asyncio.TimeoutError:
        response_time = time.time() - start_time
        logger.error(f"Timeout error after {response_time:.3f}s")
        result["error"] = "Timeout"
        result["response_time"] = response_time
        return result
        
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"Error: {str(e)}")
        result["error"] = str(e)
        result["response_time"] = response_time
        return result
        
    finally:
        # Ensure client is closed properly
        if client:
            try:
                await client.close()
            except Exception as e:
                logger.warning(f"Error closing client: {str(e)}")

async def run_tests():
    """Test the endpoint with different timeout settings."""
    logger.info(f"Starting individual endpoint test for {TEST_ENDPOINT}")
    
    # Test with different timeouts
    timeouts = [5.0, 10.0, 20.0, 30.0]
    
    for timeout in timeouts:
        result = await test_with_timeout(timeout)
        logger.info(f"Result with {timeout}s timeout: {'Success' if result['success'] else 'Failed'}")
        logger.info("-" * 50)
        
        # Wait between tests to avoid rate limiting
        await asyncio.sleep(2)
    
    logger.info("Tests completed")

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment to avoid long-running tests")
async def test_single_endpoint():
    """Pytest test function for testing a single endpoint."""
    # Just test with a single timeout for pytest
    result = await test_with_timeout(10.0)
    assert result["success"] == True, f"Endpoint test failed: {result['error']}"

if __name__ == "__main__":
    asyncio.run(run_tests())
