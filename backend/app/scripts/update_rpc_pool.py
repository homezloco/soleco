"""
RPC Pool Updater Script

This script discovers and tests Solana RPC nodes, then updates the connection pool
with the best performing nodes. It combines:

1. RPC node discovery from the /api/soleco/solana/network/rpc-nodes endpoint
2. Health testing similar to test_rpc_nodes_health.py
3. Automatic updating of the connection pool with the best performing nodes

Usage:
    python -m app.scripts.update_rpc_pool
"""

import asyncio
import time
import json
import sys
import os
import random
from typing import Dict, List, Any, Tuple
import aiohttp
import logging
import argparse

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.config import HELIUS_API_KEY
from app.utils.solana_rpc import (
    get_connection_pool, 
    SolanaConnectionPool,
    DEFAULT_RPC_ENDPOINTS,
    KNOWN_RPC_PROVIDERS
)

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

# API endpoint for discovering RPC nodes
API_BASE_URL = "http://localhost:8001/api"
RPC_NODES_ENDPOINT = f"{API_BASE_URL}/soleco/solana/network/rpc-nodes"
RPC_NODES_LIST_ENDPOINT = f"{API_BASE_URL}/soleco/solana/network/rpc-nodes-list"

async def discover_rpc_nodes() -> List[str]:
    """Discover available RPC nodes from the API."""
    logger.info("Discovering RPC nodes from API...")
    
    async with aiohttp.ClientSession() as session:
        rpc_urls = []
        
        # Get RPC nodes from the API
        try:
            async with session.get(
                RPC_NODES_ENDPOINT,
                params={
                    "include_details": "false",
                    "health_check": "false",
                    "skip_dns_lookup": "true",  # Skip DNS lookup since it's not needed
                    "include_raw_urls": "true",
                    "prioritize_clean_urls": "false",  # Don't prioritize clean URLs
                    "include_well_known": "true"
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Add raw RPC URLs (these are the IP:port format)
                    if "raw_rpc_urls" in data and data["raw_rpc_urls"]:
                        rpc_urls.extend(data["raw_rpc_urls"])
                    
                    # Add well-known URLs
                    if "well_known_rpc_urls" in data:
                        rpc_urls.extend(data["well_known_rpc_urls"])
                    
                    # Add Solana official URLs
                    if "solana_official_urls" in data:
                        rpc_urls.extend(data["solana_official_urls"])
                    
                    # Extract RPC endpoints from node details
                    if "rpc_nodes" in data:
                        for node in data["rpc_nodes"]:
                            if "rpc_endpoint" in node and node["rpc_endpoint"]:
                                rpc_urls.append(node["rpc_endpoint"])
                else:
                    logger.error(f"Failed to get RPC nodes from API: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error getting RPC nodes from API: {str(e)}")
        
        # Also add our known fallback endpoints
        fallback_endpoints = [
            "http://173.231.14.98:8899",
            "http://107.182.163.194:8899",
            "http://66.45.229.34:8899",
            "http://38.58.176.230:8899",
            "http://147.75.198.219:8899"
        ]
        rpc_urls.extend(fallback_endpoints)
        
        # Add additional endpoints from our MEMORY
        additional_endpoints = [
            "http://145.40.126.95:8899",
            "http://74.50.65.194:8899",
            "http://207.148.14.220:8899",
            "http://149-255-37-170.static.hvvc.us:8899",
            "http://74.50.65.226:8899",
            "http://149-255-37-154.static.hvvc.us:8899"
        ]
        rpc_urls.extend(additional_endpoints)
        
        # Remove duplicates while preserving order
        unique_urls = []
        for url in rpc_urls:
            if url and url not in unique_urls:
                unique_urls.append(url)
        
        logger.info(f"Discovered {len(unique_urls)} unique RPC nodes")
        return unique_urls

async def test_rpc_endpoint(session: aiohttp.ClientSession, endpoint: str) -> Dict[str, Any]:
    """Test a single RPC endpoint for health and performance."""
    # Ensure endpoint has http:// prefix
    if not endpoint.startswith('http://') and not endpoint.startswith('https://'):
        endpoint = f'http://{endpoint}'
    
    results = {
        "endpoint": endpoint,
        "status": "unknown",
        "response_times": {},
        "errors": [],
        "rate_limits": {},
        "methods_supported": {},
        "overall_score": 0,
        "api_key_required": False
    }
    
    # Test each method
    for test in TEST_METHODS:
        method = test["method"]
        params = test["params"]
        
        try:
            start_time = time.time()
            async with session.post(
                endpoint,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                timeout=5
            ) as response:
                elapsed = time.time() - start_time
                results["response_times"][method] = elapsed
                
                # Check rate limits in headers
                if "x-ratelimit-remaining" in response.headers:
                    results["rate_limits"]["remaining"] = response.headers["x-ratelimit-remaining"]
                if "x-ratelimit-limit" in response.headers:
                    results["rate_limits"]["limit"] = response.headers["x-ratelimit-limit"]
                
                # Check response
                if response.status == 200:
                    json_response = await response.json()
                    if "result" in json_response:
                        results["methods_supported"][method] = True
                    else:
                        results["methods_supported"][method] = False
                        results["errors"].append(f"{method}: No result in response")
                elif response.status == 401 or response.status == 403:
                    # Likely requires API key
                    results["api_key_required"] = True
                    results["methods_supported"][method] = False
                    results["errors"].append(f"{method}: HTTP {response.status} - Likely requires API key")
                else:
                    results["methods_supported"][method] = False
                    results["errors"].append(f"{method}: HTTP {response.status}")
        
        except asyncio.TimeoutError:
            results["methods_supported"][method] = False
            results["errors"].append(f"{method}: Timeout")
        except Exception as e:
            results["methods_supported"][method] = False
            results["errors"].append(f"{method}: {str(e)}")
    
    # Calculate overall status
    if all(results["methods_supported"].values()):
        results["status"] = "excellent"
    elif results["methods_supported"].get("getHealth", False) and results["methods_supported"].get("getVersion", False):
        results["status"] = "good"
    elif any(results["methods_supported"].values()):
        results["status"] = "partial"
    else:
        results["status"] = "down"
    
    # Calculate score (lower is better)
    avg_response_time = sum(results["response_times"].values()) / len(results["response_times"]) if results["response_times"] else 999
    method_score = sum(1 for m in results["methods_supported"].values() if m) / len(TEST_METHODS)
    results["overall_score"] = avg_response_time * (2 - method_score)  # Lower score is better
    
    return results

async def test_rpc_endpoints(endpoints: List[str], max_endpoints: int = 50) -> List[Dict[str, Any]]:
    """Test a list of RPC endpoints and return results."""
    # Limit the number of endpoints to test to avoid overloading
    if len(endpoints) > max_endpoints:
        logger.info(f"Limiting testing to {max_endpoints} randomly selected endpoints")
        random.shuffle(endpoints)
        endpoints = endpoints[:max_endpoints]
    
    logger.info(f"Testing {len(endpoints)} RPC endpoints...")
    
    async with aiohttp.ClientSession() as session:
        tasks = [test_rpc_endpoint(session, endpoint) for endpoint in endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions
    valid_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Error testing endpoint: {str(result)}")
        else:
            valid_results.append(result)
    
    return valid_results

def print_summary(test_results: List[Dict[str, Any]]) -> None:
    """Print a summary of the test results."""
    # Count the number of endpoints in each status
    status_counts = {
        "excellent": 0,
        "good": 0,
        "partial": 0,
        "down": 0
    }
    
    for result in test_results:
        status = result["status"]
        if status in status_counts:
            status_counts[status] += 1
    
    logger.info(f"\nTEST RESULTS SUMMARY:")
    logger.info(f"  Excellent: {status_counts['excellent']} endpoints")
    logger.info(f"  Good:      {status_counts['good']} endpoints")
    logger.info(f"  Partial:   {status_counts['partial']} endpoints")
    logger.info(f"  Down:      {status_counts['down']} endpoints")
    
    # Print top performers
    logger.info("\nTOP PERFORMING ENDPOINTS:")
    for i, result in enumerate(test_results[:5]):
        endpoint = result["endpoint"]
        avg_time = sum(result["response_times"].values()) / len(result["response_times"]) if result["response_times"] else 0
        logger.info(f"  {i+1}. {endpoint}")
        logger.info(f"     Score: {result['overall_score']:.3f}")
        logger.info(f"     Avg Response Time: {avg_time:.3f}s")
        logger.info(f"     Status: {result['status']}")

async def update_connection_pool(test_results: List[Dict[str, Any]], existing_endpoints: List[str] = None) -> None:
    """
    Update the connection pool with newly discovered working nodes.
    
    Args:
        test_results: List of discovered nodes with their test results
        existing_endpoints: Optional list of existing endpoints to include
    """
    # Get the current connection pool
    pool = await get_connection_pool()
    
    # Get existing endpoints if not provided
    if existing_endpoints is None:
        existing_endpoints = pool.endpoints.copy()
    
    # Extract working endpoints from discovered nodes
    # Only include endpoints with 'good' or 'partial' status
    working_endpoints = []
    for node in test_results:
        if node.get("status") in ["good", "partial"] and node.get("endpoint"):
            working_endpoints.append(node)
    
    logger.info(f"Found {len(working_endpoints)} working endpoints from test results")
    
    # Sort working endpoints by score (lower is better)
    sorted_working_endpoints = sorted(working_endpoints, key=lambda x: x.get("overall_score", float('inf')))
    
    # Extract just the endpoint URLs
    sorted_endpoint_urls = [node["endpoint"] for node in sorted_working_endpoints]
    
    # Log the best endpoints
    best_endpoints = sorted_endpoint_urls[:10]
    if best_endpoints:
        logger.info(f"Best performing discovered endpoints: {best_endpoints}")
        for i, endpoint in enumerate(best_endpoints[:5]):
            node = next((n for n in sorted_working_endpoints if n["endpoint"] == endpoint), None)
            if node:
                logger.info(f"  {i+1}. {endpoint} - Score: {node.get('overall_score', 'N/A')}, " +
                           f"Response Time: {node.get('response_time', 0):.3f}s")
    else:
        logger.warning("No working endpoints found in test results")
    
    # Create a new list with Helius endpoint first (if present)
    helius_endpoint = next((ep for ep in existing_endpoints if "helius-rpc.com" in ep), None)
    new_endpoints = [helius_endpoint] if helius_endpoint else []
    
    # Add newly discovered working endpoints next
    for endpoint in sorted_endpoint_urls:
        if endpoint not in new_endpoints:
            new_endpoints.append(endpoint)
    
    # Add remaining existing endpoints
    for endpoint in existing_endpoints:
        if endpoint not in new_endpoints:
            new_endpoints.append(endpoint)
    
    # Update the connection pool
    await pool.update_endpoints(new_endpoints)
    
    # Update the DEFAULT_RPC_ENDPOINTS in solana_rpc.py
    update_default_rpc_endpoints(new_endpoints)
    
    logger.info(f"Connection pool updated with {len(sorted_endpoint_urls)} new endpoints")
    logger.info(f"New endpoints prioritized: {best_endpoints}")
    logger.info(f"Total pool size: {len(new_endpoints)}")

def update_default_rpc_endpoints(endpoints: List[str]) -> None:
    """Update the DEFAULT_RPC_ENDPOINTS list in solana_rpc.py."""
    try:
        # Path to the solana_rpc.py file
        solana_rpc_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                      "utils", "solana_rpc.py")
        
        # Read the current file
        with open(solana_rpc_path, "r") as f:
            lines = f.readlines()
        
        # Find the DEFAULT_RPC_ENDPOINTS definition
        start_index = -1
        end_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("DEFAULT_RPC_ENDPOINTS = ["):
                start_index = i
            if start_index != -1 and line.strip() == "]":
                end_index = i
                break
        
        if start_index == -1 or end_index == -1:
            logger.error("Could not find DEFAULT_RPC_ENDPOINTS definition in solana_rpc.py")
            return
        
        # Create new lines for the endpoints
        new_lines = ["DEFAULT_RPC_ENDPOINTS = [\n"]
        for endpoint in endpoints:
            # Format the endpoint properly
            if "helius" in endpoint.lower() and "api-key" in endpoint.lower():
                new_lines.append(f'    f"https://mainnet.helius-rpc.com/?api-key={{HELIUS_API_KEY}}",\n')
            else:
                new_lines.append(f'    "{endpoint}",\n')
        new_lines.append("]\n")
        
        # Replace the old lines with the new ones
        new_content = lines[:start_index] + new_lines + lines[end_index+1:]
        
        # Write the updated file
        with open(solana_rpc_path, "w") as f:
            f.writelines(new_content)
        
        logger.info(f"Updated DEFAULT_RPC_ENDPOINTS in solana_rpc.py with {len(endpoints)} endpoints")
    except Exception as e:
        logger.error(f"Error updating DEFAULT_RPC_ENDPOINTS: {str(e)}")

async def main(args):
    """Main function to run the script."""
    # Discover RPC nodes
    endpoints = await discover_rpc_nodes()
    
    # Remove duplicates
    unique_endpoints = list(set(endpoints))
    logger.info(f"Discovered {len(unique_endpoints)} unique RPC nodes")
    
    # Test the endpoints
    test_results = await test_rpc_endpoints(unique_endpoints, args.max_test)
    
    # Print summary
    print_summary(test_results)
    
    # Print top performers
    logger.info("\nTOP PERFORMING ENDPOINTS:")
    for i, result in enumerate(test_results[:5]):
        endpoint = result["endpoint"]
        avg_time = sum(result["response_times"].values()) / len(result["response_times"]) if result["response_times"] else 0
        logger.info(f"  {i+1}. {endpoint}")
        logger.info(f"     Score: {result['overall_score']:.3f}")
        logger.info(f"     Avg Response Time: {avg_time:.3f}s")
        logger.info(f"     Status: {result['status']}")
    
    # Update the connection pool if requested
    if args.update_pool:
        await update_connection_pool(test_results)
    
    # Save results to file if requested
    if args.save_results:
        output_file = args.output_file or "rpc_node_test_results.json"
        with open(output_file, "w") as f:
            json.dump(test_results, f, indent=2)
        logger.info(f"\nDetailed results saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover and test Solana RPC nodes, then update the connection pool")
    parser.add_argument("--update-pool", action="store_true", help="Update the connection pool with the best performing nodes")
    parser.add_argument("--max-test", type=int, default=50, help="Maximum number of endpoints to test")
    parser.add_argument("--save-results", action="store_true", help="Save test results to a file")
    parser.add_argument("--output-file", type=str, help="Output file for test results (default: rpc_node_test_results.json)")
    
    args = parser.parse_args()
    
    # Run the main function
    asyncio.run(main(args))
