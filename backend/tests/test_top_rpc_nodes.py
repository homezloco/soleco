"""
Test the top performing Solana RPC endpoints discovered in our previous tests.

This script focuses on the fastest and most reliable RPC nodes we found.
"""
import asyncio
import logging
import time
import json
import sys
import os
from typing import List, Dict, Any
import pytest

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app.utils.solana_connection import SolanaConnectionPool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_ci_environment():
    """Check if we're running in a CI environment"""
    return os.environ.get('CI') == 'true'

# Top performing RPC endpoints from our previous tests
TOP_RPC_ENDPOINTS = [
    "http://38.58.176.230:8899",
    "http://74.50.65.226:8899",
    "http://147.28.171.53:8899",
    "http://67.213.115.207:8899",
    "http://208.85.17.92:8899",
    "http://74.50.65.194:8899",
    "http://145.40.126.95:8899",
    "http://185.189.44.139:8899",
    "http://173.231.22.242:8899",
    "http://66.45.229.34:8899"
]

# Official Solana RPC endpoints for comparison
OFFICIAL_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-api.projectserum.com"
]

@pytest.fixture
def endpoints():
    return [
        "https://api.mainnet-beta.solana.com",
        "https://solana-api.projectserum.com"
    ]

async def test_rpc_endpoint(endpoint: str, timeout: float = 20.0) -> Dict[str, Any]:
    """
    Test a specific RPC endpoint with basic checks.
    
    Args:
        endpoint: The RPC endpoint to test
        timeout: The timeout for the request in seconds
        
    Returns:
        Dict[str, Any]: Test results including status, version, slot, and other metrics.
    """
    start_time = time.time()
    client = None
    try:
        # Create a client for this endpoint
        client = SolanaConnectionPool()
        
        # Test basic RPC methods
        logger.info(f"Testing endpoint: {endpoint}")
        
        # Test getVersion - this is the most basic method
        version_result = await client.get_version()
        version = "unknown"
        if isinstance(version_result, dict) and "result" in version_result:
            version_data = version_result.get("result", {})
            if isinstance(version_data, dict):
                version = version_data.get("solana-core", "unknown")
        
        # Test getSlot - this is also widely supported
        slot_result = await client.get_slot()
        slot = 0
        if isinstance(slot_result, dict) and "result" in slot_result:
            slot_data = slot_result.get("result")
            if isinstance(slot_data, (int, str)):
                slot = slot_data
        
        # Calculate response time
        response_time = time.time() - start_time
        
        return {
            "endpoint": endpoint,
            "status": "success",
            "version": version,
            "slot": slot,
            "response_time": round(response_time, 3)
        }
    except Exception as e:
        error_msg = str(e)
        return {
            "endpoint": endpoint,
            "status": "error",
            "error": error_msg,
            "response_time": round(time.time() - start_time, 3)
        }
    finally:
        # Close the client
        if client:
            await client.close()

async def test_multiple_endpoints(endpoints: List[str], timeout: float = 20.0) -> Dict[str, Any]:
    """
    Test multiple RPC endpoints concurrently.
    
    Args:
        endpoints: List of RPC endpoints to test
        timeout: The timeout for each request in seconds
        
    Returns:
        Dict[str, Any]: Test results including successful and failed endpoints.
    """
    if not endpoints:
        logger.warning("No endpoints to test!")
        return {"successful": [], "failed": [], "success_rate": 0}
    
    logger.info(f"Testing {len(endpoints)} endpoints...")
    
    # Test endpoints
    tasks = [test_rpc_endpoint(endpoint, timeout) for endpoint in endpoints]
    results = await asyncio.gather(*tasks)
    
    # Sort results by status and response time
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] != "success"]
    
    successful.sort(key=lambda x: x["response_time"])
    
    # Print results
    logger.info(f"\n{'=' * 50}")
    logger.info(f"SUCCESSFUL ENDPOINTS ({len(successful)}/{len(results)})")
    logger.info(f"{'=' * 50}")
    for i, result in enumerate(successful):
        logger.info(f"{i+1}. {result['endpoint']}")
        logger.info(f"   Version: {result['version']}")
        logger.info(f"   Current Slot: {result['slot']}")
        logger.info(f"   Response Time: {result['response_time']}s")
        logger.info(f"   {'-' * 40}")
    
    if failed:
        logger.info(f"\n{'=' * 50}")
        logger.info(f"FAILED ENDPOINTS ({len(failed)}/{len(results)})")
        logger.info(f"{'=' * 50}")
        for i, result in enumerate(failed):
            logger.info(f"{i+1}. {result['endpoint']}")
            logger.info(f"   Status: {result['status']}")
            logger.info(f"   Error: {result.get('error', 'Unknown error')}")
            logger.info(f"   Response Time: {result['response_time']}s")
            logger.info(f"   {'-' * 40}")
    
    return {
        "successful": successful,
        "failed": failed,
        "success_rate": len(successful) / len(results) * 100 if results else 0
    }

async def save_results_to_file(results: Dict[str, Any], filename: str = "top_rpc_nodes_results.json") -> None:
    """
    Save test results to a JSON file.
    
    Args:
        results: The test results to save
        filename: The name of the file to save to
    """
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {filename}")

async def main():
    """Main function to run the tests."""
    logger.info("Starting top RPC nodes testing...")
    
    # Combine top endpoints with official endpoints
    all_endpoints = TOP_RPC_ENDPOINTS + OFFICIAL_ENDPOINTS
    
    # Test all endpoints
    results = await test_multiple_endpoints(all_endpoints)
    
    # Save results to file
    await save_results_to_file(results)
    
    # Print summary
    logger.info(f"\nTEST SUMMARY:")
    logger.info(f"Total endpoints tested: {len(results['successful']) + len(results['failed'])}")
    logger.info(f"Successful endpoints: {len(results['successful'])}")
    logger.info(f"Failed endpoints: {len(results['failed'])}")
    logger.info(f"Success rate: {results['success_rate']:.2f}%")
    
    # Return the fastest working endpoints
    if results['successful']:
        logger.info(f"\nTOP 5 FASTEST WORKING ENDPOINTS:")
        for i, result in enumerate(results['successful'][:5]):
            logger.info(f"{i+1}. {result['endpoint']} ({result['response_time']}s)")

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment")
async def test_rpc_endpoint():
    # Test a top RPC endpoint
    endpoint = 'api.mainnet-beta.solana.com'
    client = SolanaConnectionPool()
    try:
        # Test basic RPC methods
        version = await client.get_version()
        slot = await client.get_slot()
        assert isinstance(version, dict)
        assert isinstance(slot, int)
    finally:
        await client.close()

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment")
async def test_multiple_endpoints():
    # Test multiple top RPC endpoints
    endpoints = [
        'api.mainnet-beta.solana.com',
        'solana-api.projectserum.com',
        'rpc.ankr.com/solana'
    ]

    results = []
    for endpoint in endpoints:
        client = SolanaConnectionPool()
        try:
            version = await client.get_version()
            results.append({
                'endpoint': endpoint,
                'version': version,
                'status': 'success'
            })
        except Exception as e:
            results.append({
                'endpoint': endpoint,
                'error': str(e),
                'status': 'failed'
            })
        finally:
            await client.close()

    # Verify at least one endpoint succeeded
    assert any(r['status'] == 'success' for r in results)

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment")
async def test_invalid_endpoint():
    # Test with invalid endpoint
    endpoint = 'invalid.endpoint'
    with pytest.raises(ValueError):
        pool = SolanaConnectionPool(endpoint)
        await pool.initialize()

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment")
async def test_timeout():
    # Test timeout scenario
    endpoint = 'https://api.mainnet-beta.solana.com'
    pool = SolanaConnectionPool(endpoint)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(pool.get_version(), timeout=0.001)

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment")
async def test_multiple_rpc_methods():
    # Test multiple RPC methods on a single endpoint
    endpoint = 'api.mainnet-beta.solana.com'
    client = SolanaConnectionPool()
    try:
        # Test getVersion
        version = await client.get_version()
        assert isinstance(version, dict)
        
        # Test getSlot
        slot = await client.get_slot()
        assert isinstance(slot, int)
        
        # Test getBlockHeight
        block_height = await client.get_block_height()
        assert isinstance(block_height, int)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
