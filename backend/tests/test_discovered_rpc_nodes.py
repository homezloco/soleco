"""
Test discovered Solana RPC endpoints for connectivity and functionality.

This script:
1. Calls the Soleco API to discover RPC nodes
2. Tests each node for connectivity using both HTTP and HTTPS
3. Generates a report of working nodes
"""
import asyncio
import logging
import time
import json
import sys
import os
from typing import List, Dict, Any, Optional, Tuple
import httpx
import pytest

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

from backend.app.utils.solana_connection_pool import SolanaConnectionPool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API endpoint to get RPC nodes
API_BASE_URL = os.environ.get("TEST_SERVER_URL", "http://localhost:8001")
API_ENDPOINT = f"{API_BASE_URL}/api/soleco/solana/network/rpc-nodes"

# Well-known public RPC endpoints for comparison
WELL_KNOWN_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-api.projectserum.com",
    "https://rpc.ankr.com/solana",
    "https://solana.public-rpc.com"
]

# Previously discovered working endpoints
PREVIOUSLY_WORKING_ENDPOINTS = [
    "http://149-255-37-154.static.hvvc.us:8899",
    "http://149-255-37-170.static.hvvc.us:8899",
    "http://38.58.176.230:8899",
    "http://74.50.65.226:8899",
    "http://147.28.171.53:8899",
    "http://67.213.115.207:8899",
    "http://208.85.17.92:8899",
    "http://74.50.65.194:8899",
    "http://145.40.126.95:8899",
    "http://185.189.44.139:8899",
    "http://173.231.22.242:8899",
    "http://66.45.229.34:8899",
    "http://147.75.198.219:8899",
    "http://107.182.163.194:8899",
    "http://145.40.88.77:8899",
    "http://173.231.14.98:8899",
    "http://88.216.198.210:8899",
    "http://207.148.14.220:8899",
    "http://103.219.170.217:8899"
]

# Check if we're running in a CI environment
def is_ci_environment():
    return os.environ.get("CI", "false").lower() == "true"

async def fetch_rpc_nodes() -> Dict[str, Any]:
    """
    Fetch RPC nodes from the Soleco API.
    
    Returns:
        Dict[str, Any]: The API response containing RPC nodes.
    """
    logger.info(f"Fetching RPC nodes from {API_ENDPOINT}")
    
    params = {
        "include_raw_urls": True,
        "include_well_known": True,
        "skip_dns_lookup": False,
        "prioritize_clean_urls": True,
        "max_conversions": 100
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(API_ENDPOINT, params=params, timeout=60.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching RPC nodes: {e}")
            return {"raw_rpc_urls": [], "converted_rpc_urls": [], "well_known_rpc_urls": [], "solana_official_urls": []}

async def test_rpc_endpoint(endpoint: str, protocol: str = "https", timeout: float = 5.0) -> Dict[str, Any]:
    """
    Test a specific RPC endpoint with the specified protocol.
    
    Args:
        endpoint: The RPC endpoint to test
        protocol: The protocol to use (http or https)
        timeout: The timeout for the request in seconds
        
    Returns:
        Dict[str, Any]: Test results including status, version, and slot.
    """
    # Ensure the endpoint doesn't already have a protocol
    if "://" in endpoint:
        full_endpoint = endpoint
    else:
        full_endpoint = f"{protocol}://{endpoint}"
    
    start_time = time.time()
    logger.debug(f"Testing endpoint: {full_endpoint}")
    try:
        # Initialize the connection pool with the specific endpoint
        async with SolanaConnectionPool(endpoint=full_endpoint) as pool:
            logger.debug("Successfully initialized connection pool")
            
            # Test getVersion
            logger.debug("Testing get_version")
            version_result = await pool.get_version()
            logger.debug(f"get_version response: {version_result}")
            version = "unknown"
            if isinstance(version_result, dict) and "result" in version_result:
                version_data = version_result.get("result", {})
                if isinstance(version_data, dict):
                    version = version_data.get("solana-core", "unknown")
            
            # Test getSlot
            logger.debug("Testing get_slot")
            slot_result = await pool.get_slot()
            logger.debug(f"get_slot response: {slot_result}")
            slot = 0
            if isinstance(slot_result, dict) and "result" in slot_result:
                slot_data = slot_result.get("result")
                if isinstance(slot_data, (int, str)):
                    slot = slot_data
            
            # Calculate response time
            response_time = time.time() - start_time
            
            logger.debug(f"Test successful for {full_endpoint}")
            return {
                "endpoint": full_endpoint,
                "status": "success",
                "version": version,
                "slot": slot,
                "response_time": round(response_time, 3)
            }
    except Exception as e:
        logger.error(f"Error testing endpoint {full_endpoint}: {str(e)}", exc_info=True)
        return {
            "endpoint": full_endpoint,
            "status": "error",
            "error": str(e),
            "response_time": round(time.time() - start_time, 3)
        }

async def test_endpoint_with_both_protocols(endpoint: str, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Test an endpoint with both HTTP and HTTPS protocols.
    
    Args:
        endpoint: The RPC endpoint to test
        timeout: The timeout for the request in seconds
        
    Returns:
        Dict[str, Any]: Test results from the successful protocol, or the HTTPS results if both fail.
    """
    # Skip protocol testing if the endpoint already includes a protocol
    if "://" in endpoint:
        return await test_rpc_endpoint(endpoint, timeout=timeout)
    
    # Test with HTTPS first
    https_result = await test_rpc_endpoint(endpoint, "https", timeout)
    
    # If HTTPS failed, try HTTP
    if https_result["status"] != "success":
        http_result = await test_rpc_endpoint(endpoint, "http", timeout)
        return http_result if http_result["status"] == "success" else https_result
    
    return https_result

async def test_multiple_endpoints(endpoints: List[str], timeout: float = 5.0) -> Dict[str, Any]:
    """
    Test multiple RPC endpoints with both HTTP and HTTPS protocols.
    
    Args:
        endpoints: List of RPC endpoints to test
        timeout: The timeout for each request in seconds
        
    Returns:
        Dict[str, Any]: Test results including successful and failed endpoints.
    """
    if not endpoints:
        logger.warning("No endpoints to test")
        return {"successful": [], "failed": [], "success_rate": 0}
    
    # Remove duplicates while preserving order
    unique_endpoints = []
    seen = set()
    for endpoint in endpoints:
        # Convert endpoint to a hashable type (string) if it's a list
        endpoint_key = str(endpoint) if isinstance(endpoint, (list, dict)) else endpoint
        if endpoint_key not in seen:
            unique_endpoints.append(endpoint)
            seen.add(endpoint_key)
    
    logger.info(f"Testing {len(unique_endpoints)} unique endpoints...")
    
    # Test endpoints with both protocols
    tasks = [test_endpoint_with_both_protocols(endpoint, timeout) for endpoint in unique_endpoints]
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
    
    logger.info(f"\n{'=' * 50}")
    logger.info(f"FAILED ENDPOINTS (showing first 10 of {len(failed)})")
    logger.info(f"{'=' * 50}")
    for i, result in enumerate(failed[:10]):  # Show only first 10 failed endpoints
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

async def save_results_to_file(results: Dict[str, Any], filename: str = "rpc_test_results.json") -> None:
    """
    Save test results to a JSON file.
    
    Args:
        results: The test results to save
        filename: The name of the file to save to
    """
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {filename}")

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment as it requires a running server")
async def test_rpc_endpoint():
    # Test a discovered RPC endpoint
    endpoint = 'https://api.mainnet-beta.solana.com'
    pool = SolanaConnectionPool(endpoint)
    version = await pool.get_version()
    assert version is not None
    assert isinstance(version, dict)
    assert 'solana-core' in version['result']

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment as it requires a running server")
async def test_endpoint_with_both_protocols():
    # Test endpoints with both http and https protocols
    endpoints = [
        'http://api.mainnet-beta.solana.com',
        'https://api.mainnet-beta.solana.com'
    ]
    
    for endpoint in endpoints:
        pool = SolanaConnectionPool(endpoint)
        version = await pool.get_version()
        assert version is not None
        assert isinstance(version, dict)
        assert 'solana-core' in version['result']

@pytest.mark.asyncio
@pytest.mark.skipif(is_ci_environment(), reason="Skip in CI environment as it requires a running server")
async def test_multiple_endpoints():
    # Test multiple discovered endpoints
    endpoints = [
        'https://api.mainnet-beta.solana.com',
        'https://api.devnet.solana.com',
        'https://api.testnet.solana.com'
    ]
    
    for endpoint in endpoints:
        pool = SolanaConnectionPool(endpoint)
        version = await pool.get_version()
        assert version is not None
        assert isinstance(version, dict)
        assert 'solana-core' in version['result']

async def main():
    """Main function to run the tests."""
    logger.info("Starting RPC node discovery and testing...")
    
    # Fetch RPC nodes from the API
    api_response = await fetch_rpc_nodes()
    
    # Collect all endpoints to test
    all_endpoints = []
    
    # Add raw RPC URLs
    if "raw_rpc_urls" in api_response and api_response["raw_rpc_urls"]:
        logger.info(f"Found {len(api_response['raw_rpc_urls'])} raw RPC URLs")
        all_endpoints.extend(api_response["raw_rpc_urls"])
    
    # Add converted RPC URLs
    if "converted_rpc_urls" in api_response and api_response["converted_rpc_urls"]:
        logger.info(f"Found {len(api_response['converted_rpc_urls'])} converted RPC URLs")
        all_endpoints.extend(api_response["converted_rpc_urls"])
    
    # Add well-known RPC URLs
    if "well_known_rpc_urls" in api_response and api_response["well_known_rpc_urls"]:
        logger.info(f"Found {len(api_response['well_known_rpc_urls'])} well-known RPC URLs")
        all_endpoints.extend(api_response["well_known_rpc_urls"])
    
    # Add Solana official URLs
    if "solana_official_urls" in api_response and api_response["solana_official_urls"]:
        logger.info(f"Found {len(api_response['solana_official_urls'])} Solana official URLs")
        all_endpoints.extend(api_response["solana_official_urls"])
    
    # Add our own well-known endpoints for comparison
    all_endpoints.extend(WELL_KNOWN_ENDPOINTS)
    
    # Add previously discovered working endpoints
    all_endpoints.extend(PREVIOUSLY_WORKING_ENDPOINTS)
    
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

if __name__ == "__main__":
    asyncio.run(main())
