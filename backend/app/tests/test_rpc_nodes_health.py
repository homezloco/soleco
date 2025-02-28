"""
RPC Node Health Test Script

This script tests all known RPC nodes to determine which ones are working well.
It performs various tests including:
1. Basic connectivity
2. Response time
3. Rate limit information
4. Method availability

Usage:
    python -m app.tests.test_rpc_nodes_health
"""

import asyncio
import time
import json
import sys
import os
from typing import Dict, List, Any, Tuple
import aiohttp
import logging

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.config import HELIUS_API_KEY
from app.utils.solana_rpc import KNOWN_RPC_PROVIDERS, FALLBACK_RPC_ENDPOINTS

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

async def test_rpc_endpoint(session: aiohttp.ClientSession, endpoint: str) -> Dict[str, Any]:
    """Test a single RPC endpoint for health and performance."""
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

async def test_all_endpoints() -> List[Dict[str, Any]]:
    """Test all RPC endpoints and return results."""
    async with aiohttp.ClientSession() as session:
        tasks = [test_rpc_endpoint(session, endpoint) for endpoint in UNIQUE_RPC_ENDPOINTS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions
    valid_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Error testing endpoint: {str(result)}")
        else:
            valid_results.append(result)
    
    # Sort by overall score (lower is better)
    valid_results.sort(key=lambda x: x["overall_score"])
    return valid_results

def print_results(results: List[Dict[str, Any]]) -> None:
    """Print test results in a readable format."""
    print("\n" + "=" * 80)
    print(f"RPC NODE HEALTH TEST RESULTS - {len(results)} endpoints tested")
    print("=" * 80)
    
    # Group by status
    status_groups = {
        "excellent": [],
        "good": [],
        "partial": [],
        "down": []
    }
    
    for result in results:
        status = result["status"]
        if status in status_groups:
            status_groups[status].append(result)
    
    # Print summary
    print(f"\nSUMMARY:")
    print(f"  Excellent: {len(status_groups['excellent'])} endpoints")
    print(f"  Good:      {len(status_groups['good'])} endpoints")
    print(f"  Partial:   {len(status_groups['partial'])} endpoints")
    print(f"  Down:      {len(status_groups['down'])} endpoints")
    
    # Print detailed results by group
    for status, group in status_groups.items():
        if not group:
            continue
            
        print(f"\n{status.upper()} ENDPOINTS:")
        for result in group:
            endpoint = result["endpoint"]
            avg_time = sum(result["response_times"].values()) / len(result["response_times"]) if result["response_times"] else 0
            methods = sum(1 for m in result["methods_supported"].values() if m)
            print(f"  {endpoint}")
            print(f"    Score: {result['overall_score']:.3f}")
            print(f"    Avg Response Time: {avg_time:.3f}s")
            print(f"    Methods Working: {methods}/{len(TEST_METHODS)}")
            if result["errors"]:
                print(f"    Errors: {len(result['errors'])}")
                # Print first error in detail
                print(f"    First Error: {result['errors'][0]}")
            if result["api_key_required"]:
                print(f"    API Key Required: Yes")
            else:
                print(f"    API Key Required: No")
    
    # Print recommendations
    print("\nRECOMMENDED ENDPOINTS:")
    for i, result in enumerate(results[:3]):
        if result["status"] in ["excellent", "good"]:
            print(f"  {i+1}. {result['endpoint']} (Score: {result['overall_score']:.3f})")
    
    print("\nNOT RECOMMENDED ENDPOINTS:")
    for result in results:
        if result["status"] == "down":
            print(f"  ❌ {result['endpoint']}")

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
