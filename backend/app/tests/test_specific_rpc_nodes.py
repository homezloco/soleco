"""
Test for specific Solana RPC endpoints with both HTTP and HTTPS
"""
import asyncio
import logging
import time
from ..utils.solana_rpc import SolanaClient, RPCError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of RPC endpoints to test with both HTTP and HTTPS
RPC_ENDPOINTS_TO_TEST = [
    # Original endpoints that failed but showed some response
    "149-255-37-170.static.hvvc.us:8899",
    "149-255-37-154.static.hvvc.us:8899",
    "vmi2400433.contaboserver.net:8899",
    
    # Other endpoints that failed
    "unassigned.psychz.net:8899",
    "70.34.245.172.vultrusercontent.com:8899",
    "149.248.62.208.vultrusercontent.com:8899",
    "207.148.14.220.vultrusercontent.com:8899",
    "anza-staked-node-hk-1:8899",
    "177-54-146-61.rev.hostzone.com.br:8899",
    "80-77-161-201.as51369.ru:8899",
    "208.85.17.92.vultrusercontent.com:8899",
    "static-ip-173-224-127-6.inaddr.ip-pool.com:8899",
    "anza-dev-staked-tokyo:8899",
    "66-135-11-69.constant.com:8899"
]

# Well-known public RPC endpoints for comparison
WELL_KNOWN_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-api.projectserum.com",
    "https://rpc.ankr.com/solana",
    "https://solana.public-rpc.com"
]

async def test_rpc_endpoint(endpoint: str, protocol: str = "https", timeout: float = 5.0):
    """Test a specific RPC endpoint with the specified protocol."""
    full_endpoint = f"{protocol}://{endpoint}" if "://" not in endpoint else endpoint
    start_time = time.time()
    try:
        # Create a client for this endpoint
        client = SolanaClient(endpoint=full_endpoint, timeout=timeout)
        
        # Test basic RPC methods
        logger.info(f"Testing endpoint: {full_endpoint}")
        
        # Test getVersion
        version_result = await client.get_version()
        version = "unknown"
        if isinstance(version_result, dict) and "result" in version_result:
            version_data = version_result.get("result", {})
            if isinstance(version_data, dict):
                version = version_data.get("solana-core", "unknown")
        
        # Test getSlot
        slot_result = await client.get_slot()
        slot = 0
        if isinstance(slot_result, dict) and "result" in slot_result:
            slot_data = slot_result.get("result")
            if isinstance(slot_data, (int, str)):
                slot = slot_data
        
        # Calculate response time
        response_time = time.time() - start_time
        
        return {
            "endpoint": full_endpoint,
            "status": "success",
            "version": version,
            "slot": slot,
            "response_time": round(response_time, 3)
        }
    except Exception as e:
        return {
            "endpoint": full_endpoint,
            "status": "error",
            "error": str(e),
            "response_time": round(time.time() - start_time, 3)
        }
    finally:
        # Close the client
        if 'client' in locals():
            await client.close()

async def test_endpoint_with_both_protocols(endpoint: str, timeout: float = 5.0):
    """Test an endpoint with both HTTP and HTTPS protocols."""
    # Test with HTTPS first
    https_result = await test_rpc_endpoint(endpoint, "https", timeout)
    
    # If HTTPS failed, try HTTP
    if https_result["status"] != "success":
        http_result = await test_rpc_endpoint(endpoint, "http", timeout)
        return http_result if http_result["status"] == "success" else https_result
    
    return https_result

async def test_multiple_endpoints(endpoints: list, well_known_endpoints: list, timeout: float = 5.0):
    """Test multiple RPC endpoints concurrently."""
    # Test regular endpoints with both protocols
    regular_tasks = [test_endpoint_with_both_protocols(endpoint, timeout) for endpoint in endpoints]
    regular_results = await asyncio.gather(*regular_tasks)
    
    # Test well-known endpoints (these already have the protocol in the URL)
    well_known_tasks = [test_rpc_endpoint(endpoint, timeout=timeout) for endpoint in well_known_endpoints]
    well_known_results = await asyncio.gather(*well_known_tasks)
    
    # Combine results
    all_results = regular_results + well_known_results
    
    # Sort results by status and response time
    successful = [r for r in all_results if r["status"] == "success"]
    failed = [r for r in all_results if r["status"] != "success"]
    
    successful.sort(key=lambda x: x["response_time"])
    
    # Print results
    logger.info(f"\n{'=' * 50}")
    logger.info(f"SUCCESSFUL ENDPOINTS ({len(successful)}/{len(all_results)})")
    logger.info(f"{'=' * 50}")
    for i, result in enumerate(successful):
        logger.info(f"{i+1}. {result['endpoint']}")
        logger.info(f"   Version: {result['version']}")
        logger.info(f"   Current Slot: {result['slot']}")
        logger.info(f"   Response Time: {result['response_time']}s")
        logger.info(f"   {'-' * 40}")
    
    logger.info(f"\n{'=' * 50}")
    logger.info(f"FAILED ENDPOINTS ({len(failed)}/{len(all_results)})")
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
        "success_rate": len(successful) / len(all_results) * 100
    }

if __name__ == "__main__":
    # Run the test
    logger.info("Testing RPC endpoints with both HTTP and HTTPS...")
    result = asyncio.run(test_multiple_endpoints(RPC_ENDPOINTS_TO_TEST, WELL_KNOWN_ENDPOINTS))
    logger.info(f"Test completed with success rate: {result['success_rate']:.2f}%")
