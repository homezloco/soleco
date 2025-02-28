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

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

from app.utils.solana_rpc import SolanaClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# The endpoint to test
TEST_ENDPOINT = "https://api.mainnet-beta.solana.com"

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
    try:
        # Create a client for this endpoint
        client = SolanaClient(endpoint=TEST_ENDPOINT, timeout=timeout)
        
        logger.info(f"Testing endpoint {TEST_ENDPOINT} with timeout {timeout}s")
        
        # Test getHealth - simplest method
        health_result = await client._make_rpc_call("getHealth", [])
        logger.info(f"Health result: {health_result}")
        
        # Test getVersion
        version_result = await client.get_version()
        logger.info(f"Version result: {version_result}")
        
        response_time = time.time() - start_time
        logger.info(f"Test completed in {response_time:.3f}s")
        
        return {
            "endpoint": TEST_ENDPOINT,
            "timeout": timeout,
            "status": "success",
            "response_time": round(response_time, 3),
            "health": health_result,
            "version": version_result
        }
    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"Error with timeout {timeout}s after {error_time:.3f}s: {str(e)}")
        return {
            "endpoint": TEST_ENDPOINT,
            "timeout": timeout,
            "status": "error",
            "error": str(e),
            "error_time": round(error_time, 3)
        }
    finally:
        if client:
            await client.close()

async def main():
    """Test the endpoint with different timeout settings."""
    logger.info(f"Starting individual endpoint test for {TEST_ENDPOINT}")
    
    # Test with different timeouts
    timeouts = [5.0, 10.0, 20.0, 30.0]
    
    for timeout in timeouts:
        result = await test_with_timeout(timeout)
        logger.info(f"Result with {timeout}s timeout: {'Success' if result['status'] == 'success' else 'Failed'}")
        logger.info("-" * 50)
        
        # Wait between tests to avoid rate limiting
        await asyncio.sleep(2)
    
    logger.info("Tests completed")

if __name__ == "__main__":
    asyncio.run(main())
