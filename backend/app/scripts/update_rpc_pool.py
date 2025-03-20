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

import os
import sys
import time
import json
import asyncio
import aiohttp
import logging
import argparse
from typing import List, Dict, Any, Optional, Tuple
from ssl import SSLError
from datetime import datetime
import re
import httpx

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.config import HELIUS_API_KEY
from app.utils.solana_rpc import get_connection_pool, SolanaConnectionPool, SolanaClient
from app.utils.solana_error import (
    SlotSkippedError, 
    MethodNotSupportedError, 
    RPCError, 
    NodeUnhealthyError,
    BlockNotAvailableError
)
from app.utils.solana_rpc_constants import DEFAULT_RPC_ENDPOINTS, KNOWN_RPC_PROVIDERS
from tests.test_discovered_rpc_nodes import (
    fetch_rpc_nodes,
    WELL_KNOWN_ENDPOINTS,
    PREVIOUSLY_WORKING_ENDPOINTS
)

# Configure logging
logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False):
    """
    Set up logging configuration.
    
    Args:
        verbose: Whether to enable verbose logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# Test methods to check
TEST_METHODS = [
    {"method": "getHealth", "params": []},
    {"method": "getVersion", "params": []},
    {"method": "getSlot", "params": []},
    {"method": "getBlockHeight", "params": []},
    {"method": "getLatestBlockhash", "params": [{"commitment": "processed"}]},
    {"method": "getRecentBlockhash", "params": [{"commitment": "processed"}]}
]

# API endpoint for discovering RPC nodes
API_BASE_URL = "http://localhost:8001"
PRIMARY_RPC_NODES_ENDPOINT = f"{API_BASE_URL}/api/soleco/solana/network/rpc-nodes-v2"
FALLBACK_RPC_NODES_ENDPOINT = f"{API_BASE_URL}/api/soleco/solana/network/rpc-nodes"

async def discover_rpc_nodes(quick_mode: bool = False) -> List[str]:
    """
    Discover RPC nodes from all sources including the API endpoint.
    
    Args:
        quick_mode: If True, only use community endpoints for faster discovery
        
    Returns:
        List of discovered RPC endpoint URLs
    """
    # Start with community endpoints (these are more reliable)
    logger.info("Discovering community endpoints")
    community_endpoints = await discover_community_endpoints()
    logger.info(f"Discovered {len(community_endpoints)} community endpoints")
    
    # Fetch RPC nodes from the API using simplified parameters
    logger.info("Fetching RPC nodes from API")
    
    # Customize parameters to focus on raw URLs and skip conversions
    params = {
        "include_raw_urls": True,
        "include_well_known": True,
        "skip_dns_lookup": True,  # Skip DNS lookup to speed up the process
        "prioritize_clean_urls": False,  # We'll handle all URLs directly
        "include_all": True,  # Include all nodes
        "max_conversions": 0  # Skip conversions entirely
    }
    
    api_endpoints = []
    
    # Use direct httpx call instead of fetch_rpc_nodes to customize parameters
    async with httpx.AsyncClient() as client:
        # Try primary endpoint first
        try:
            logger.info(f"Calling primary API endpoint: {PRIMARY_RPC_NODES_ENDPOINT}")
            response = await client.get(PRIMARY_RPC_NODES_ENDPOINT, params=params, timeout=60.0)
            
            if response.status_code == 200:
                api_response = response.json()
                logger.info(f"Successfully retrieved data from primary endpoint")
                
                # Extract only raw URLs
                if "raw_rpc_urls" in api_response and api_response["raw_rpc_urls"]:
                    raw_urls = api_response["raw_rpc_urls"]
                    logger.info(f"Found {len(raw_urls)} raw RPC URLs")
                    api_endpoints.extend(raw_urls)
                
                # Add well-known URLs if available
                if "well_known_rpc_urls" in api_response and api_response["well_known_rpc_urls"]:
                    well_known = api_response["well_known_rpc_urls"]
                    logger.info(f"Found {len(well_known)} well-known RPC URLs")
                    api_endpoints.extend(well_known)
                
                # Add official Solana URLs if available
                if "solana_official_urls" in api_response and api_response["solana_official_urls"]:
                    official = api_response["solana_official_urls"]
                    logger.info(f"Found {len(official)} Solana official URLs")
                    api_endpoints.extend(official)
            else:
                logger.warning(f"Primary endpoint returned status code {response.status_code}, trying fallback")
                
                # Try fallback endpoint
                try:
                    logger.info(f"Calling fallback API endpoint: {FALLBACK_RPC_NODES_ENDPOINT}")
                    fallback_response = await client.get(FALLBACK_RPC_NODES_ENDPOINT, params=params, timeout=60.0)
                    
                    if fallback_response.status_code == 200:
                        fallback_api_response = fallback_response.json()
                        logger.info(f"Successfully retrieved data from fallback endpoint")
                        
                        # Extract only raw URLs
                        if "raw_rpc_urls" in fallback_api_response and fallback_api_response["raw_rpc_urls"]:
                            raw_urls = fallback_api_response["raw_rpc_urls"]
                            logger.info(f"Found {len(raw_urls)} raw RPC URLs from fallback")
                            api_endpoints.extend(raw_urls)
                        
                        # Add well-known URLs if available
                        if "well_known_rpc_urls" in fallback_api_response and fallback_api_response["well_known_rpc_urls"]:
                            well_known = fallback_api_response["well_known_rpc_urls"]
                            logger.info(f"Found {len(well_known)} well-known RPC URLs from fallback")
                            api_endpoints.extend(well_known)
                    else:
                        logger.error(f"Fallback endpoint returned status code {fallback_response.status_code}")
                except Exception as fallback_error:
                    logger.error(f"Error fetching RPC nodes from fallback API: {str(fallback_error)}")
                
        except Exception as e:
            logger.error(f"Error fetching RPC nodes from primary API: {str(e)}")
            
            # Try fallback endpoint
            try:
                logger.info(f"Calling fallback API endpoint: {FALLBACK_RPC_NODES_ENDPOINT}")
                fallback_response = await client.get(FALLBACK_RPC_NODES_ENDPOINT, params=params, timeout=60.0)
                
                if fallback_response.status_code == 200:
                    fallback_api_response = fallback_response.json()
                    logger.info(f"Successfully retrieved data from fallback endpoint")
                    
                    # Extract only raw URLs
                    if "raw_rpc_urls" in fallback_api_response and fallback_api_response["raw_rpc_urls"]:
                        raw_urls = fallback_api_response["raw_rpc_urls"]
                        logger.info(f"Found {len(raw_urls)} raw RPC URLs from fallback")
                        api_endpoints.extend(raw_urls)
                    
                    # Add well-known URLs if available
                    if "well_known_rpc_urls" in fallback_api_response and fallback_api_response["well_known_rpc_urls"]:
                        well_known = fallback_api_response["well_known_rpc_urls"]
                        logger.info(f"Found {len(well_known)} well-known RPC URLs from fallback")
                        api_endpoints.extend(well_known)
                else:
                    logger.error(f"Fallback endpoint returned status code {fallback_response.status_code}")
            except Exception as fallback_error:
                logger.error(f"Error fetching RPC nodes from fallback API: {str(fallback_error)}")
    
    logger.info(f"Discovered {len(api_endpoints)} endpoints from API")
    
    # Add well-known endpoints for comparison
    api_endpoints.extend(WELL_KNOWN_ENDPOINTS)
    
    # Add previously discovered working endpoints
    api_endpoints.extend(PREVIOUSLY_WORKING_ENDPOINTS)
    
    # If in quick mode, only use community and API endpoints
    if quick_mode:
        logger.info("Quick mode enabled, skipping validator endpoint discovery")
        all_endpoints = get_unique_endpoints(community_endpoints + api_endpoints)
        logger.info(f"Total unique endpoints (quick mode): {len(all_endpoints)}")
        return all_endpoints
    
    # Discover validator endpoints
    logger.info("Discovering validator endpoints")
    validator_endpoints = await discover_validator_endpoints()
    logger.info(f"Discovered {len(validator_endpoints)} validator endpoints")
    
    # Combine all endpoints
    all_endpoints = get_unique_endpoints(community_endpoints + api_endpoints + validator_endpoints)
    logger.info(f"Total unique endpoints: {len(all_endpoints)}")
    
    return all_endpoints

def get_unique_endpoints(endpoints: List[Any]) -> List[str]:
    """
    Get a list of unique endpoints while handling unhashable types.
    
    Args:
        endpoints: List of endpoints which may contain unhashable types
        
    Returns:
        List of unique endpoints as strings
    """
    unique_endpoints = []
    seen = set()
    
    for endpoint in endpoints:
        # Convert endpoint to a hashable type (string) if it's a list or dict
        endpoint_key = str(endpoint) if isinstance(endpoint, (list, dict)) else endpoint
        if endpoint_key not in seen:
            unique_endpoints.append(endpoint)
            seen.add(endpoint_key)
    
    return unique_endpoints

async def discover_api_endpoints() -> List[str]:
    """
    Discover RPC endpoints from the API endpoint.
    
    Returns:
        List of discovered RPC endpoint URLs
    """
    endpoints = []
    
    try:
        async with aiohttp.ClientSession() as session:
            # Set parameters for the API call
            params = {
                "include_details": "true"  # We need the full details to get the RPC endpoints
            }
            
            # Try primary endpoint first
            logger.info(f"Fetching RPC nodes from {PRIMARY_RPC_NODES_ENDPOINT}")
            async with session.get(PRIMARY_RPC_NODES_ENDPOINT, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"API response received: {str(data)[:200]}...")
                    
                    # Extract RPC endpoints from the response
                    if data.get("status") == "success" and "rpc_nodes" in data:
                        for node in data["rpc_nodes"]:
                            if "rpc_endpoint" in node and node["rpc_endpoint"]:
                                endpoints.append(node["rpc_endpoint"])
                    
                    logger.info(f"Discovered {len(endpoints)} RPC endpoints from API")
                else:
                    logger.warning(f"API returned status {response.status}, trying fallback endpoint")
                    
                    # Try fallback endpoint
                    logger.info(f"Fetching RPC nodes from fallback {FALLBACK_RPC_NODES_ENDPOINT}")
                    async with session.get(FALLBACK_RPC_NODES_ENDPOINT, params=params, timeout=30) as fallback_response:
                        if fallback_response.status == 200:
                            fallback_data = await fallback_response.json()
                            logger.debug(f"Fallback API response received: {str(fallback_data)[:200]}...")
                            
                            # Extract RPC endpoints from the response
                            if fallback_data.get("status") == "success" and "rpc_nodes" in fallback_data:
                                for node in fallback_data["rpc_nodes"]:
                                    if "rpc_endpoint" in node and node["rpc_endpoint"]:
                                        endpoints.append(node["rpc_endpoint"])
                            
                            logger.info(f"Discovered {len(endpoints)} RPC endpoints from fallback API")
                        else:
                            logger.error(f"Fallback API returned status {fallback_response.status}")
    except Exception as e:
        logger.error(f"Error discovering API endpoints: {str(e)}")
    
    return endpoints

async def discover_community_endpoints() -> List[str]:
    """
    Discover community RPC endpoints from known providers.
    
    Returns:
        List of discovered RPC endpoint URLs
    """
    endpoints = []
    
    # Add default endpoints
    for endpoint in DEFAULT_RPC_ENDPOINTS:
        # Skip problematic endpoints
        if "projectserum" in endpoint.lower() or "rpcpool.com" in endpoint.lower():
            logger.info(f"Skipping known problematic endpoint: {endpoint}")
            continue
            
        if endpoint not in endpoints:
            endpoints.append(endpoint)
            
    # Add known providers
    for provider, provider_endpoints in KNOWN_RPC_PROVIDERS.items():
        # Skip problematic providers
        if "projectserum" in provider.lower() or "rpcpool.com" in provider.lower():
            logger.info(f"Skipping known problematic provider: {provider}")
            continue
            
        # Handle list of endpoints
        if isinstance(provider_endpoints, list):
            for endpoint in provider_endpoints:
                if endpoint not in endpoints and "projectserum" not in endpoint.lower() and "rpcpool.com" not in endpoint.lower():
                    endpoints.append(endpoint)
        # Handle single endpoint string
        elif isinstance(provider_endpoints, str) and provider_endpoints not in endpoints:
            if "projectserum" not in provider_endpoints.lower() and "rpcpool.com" not in provider_endpoints.lower():
                endpoints.append(provider_endpoints)
            
    # Ensure API keys are only used with their specific endpoints
    filtered_endpoints = []
    for endpoint in endpoints:
        # Keep Helius endpoint with API key
        if "helius" in endpoint.lower() and "api-key" in endpoint.lower():
            filtered_endpoints.append(endpoint)
        # For other endpoints, ensure they don't have API keys from other services
        elif "api-key" not in endpoint.lower() and HELIUS_API_KEY not in endpoint:
            filtered_endpoints.append(endpoint)
            
    logger.info(f"Discovered {len(filtered_endpoints)} community endpoints")
    return filtered_endpoints

async def discover_validator_endpoints(
    cluster_api_url: str = "https://api.mainnet-beta.solana.com",
    timeout: float = 10.0,
    ssl_verify: bool = True
) -> List[str]:
    """
    Discover validator RPC endpoints from cluster nodes.
    
    Args:
        cluster_api_url: URL of the cluster API to query for validators
        timeout: Timeout in seconds for RPC calls
        ssl_verify: Whether to verify SSL certificates
        
    Returns:
        List of discovered RPC endpoints
    """
    logger.info(f"Discovering validator endpoints from {cluster_api_url}")
    
    # Initialize client with the cluster API URL
    client = SolanaClient(endpoint=cluster_api_url, timeout=timeout, ssl_verify=ssl_verify)
    
    try:
        # Get cluster nodes
        nodes = await client.get_cluster_nodes()
        logger.info(f"Found {len(nodes)} cluster nodes")
        
        # Extract RPC endpoints from nodes
        endpoints = []
        
        for node in nodes:
            # Skip nodes without rpc information
            if not node.get("rpc"):
                continue
                
            # Extract hostname/IP and port
            rpc_host = node.get("rpc")
            gossip_host = node.get("gossip")
            
            # Skip empty or invalid hosts
            if not rpc_host or len(rpc_host) < 3:
                continue
                
            # Try to extract port from gossip if available (usually rpc port = gossip port + 1)
            rpc_port = None
            if gossip_host and ":" in gossip_host:
                try:
                    gossip_port = int(gossip_host.split(":")[-1])
                    rpc_port = gossip_port + 1
                except (ValueError, IndexError):
                    pass
            
            # If we couldn't get port from gossip, try to extract from rpc field
            if not rpc_port and ":" in rpc_host:
                try:
                    rpc_port = int(rpc_host.split(":")[-1])
                    # Remove port from host if it's included
                    rpc_host = rpc_host.rsplit(":", 1)[0]
                except (ValueError, IndexError):
                    pass
            
            # Use default port if we couldn't extract one
            if not rpc_port:
                rpc_port = 8899  # Default Solana RPC port
            
            # Check if the host is an IP address or domain
            is_ip = re.match(r'^\d+\.\d+\.\d+\.\d+$', rpc_host) is not None
            
            # Construct endpoint URL
            if is_ip:
                # For IP addresses, use http by default
                endpoint = f"http://{rpc_host}:{rpc_port}"
            else:
                # For domains, prefer https
                endpoint = f"https://{rpc_host}:{rpc_port}"
                
                # For standard domains, don't include default port
                if rpc_port == 443:
                    endpoint = f"https://{rpc_host}"
                
                # Check for common TLDs to identify likely public endpoints
                common_tlds = ['.com', '.net', '.io', '.org']
                has_common_tld = any(rpc_host.endswith(tld) for tld in common_tlds)
                
                # Prioritize endpoints with common TLDs
                if has_common_tld:
                    # Add both https and http versions for testing
                    endpoints.append(endpoint)
                    # Also try without the port for common domains
                    if rpc_port != 443:
                        endpoints.append(f"https://{rpc_host}")
            
            # Add the endpoint to our list
            if endpoint not in endpoints:
                endpoints.append(endpoint)
        
        # Filter out invalid endpoints
        valid_endpoints = []
        for endpoint in endpoints:
            if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
                logger.warning(f"Skipping invalid endpoint format: {endpoint}")
                continue
                
            # Skip endpoints with non-standard ports except 8899 (Solana default)
            if ":" in endpoint.split("/")[-1]:
                port = endpoint.split(":")[-1]
                if port not in ["80", "443", "8899"]:
                    logger.debug(f"Skipping endpoint with non-standard port: {endpoint}")
                    continue
            
            valid_endpoints.append(endpoint)
        
        logger.info(f"Discovered {len(valid_endpoints)} potential validator endpoints")
        return valid_endpoints
    
    except Exception as e:
        logger.error(f"Error discovering validator endpoints: {str(e)}")
        return []
    
    finally:
        # Ensure client is closed
        try:
            await client.close()
        except Exception as e:
            logger.debug(f"Error closing client: {str(e)}")

async def test_endpoint(endpoint: str, timeout: float = 10.0) -> Dict[str, Any]:
    """
    Test a specific RPC endpoint.
    
    Args:
        endpoint: The RPC endpoint to test
        timeout: The timeout for the request in seconds
        
    Returns:
        Dict[str, Any]: Test results including status, latency, and other metrics.
    """
    start_time = time.time()
    result = {
        "endpoint": endpoint,
        "status": "error",
        "tests_passed": 0,
        "tests_total": 0,
        "persistent_failures": 0,
        "latency": 0.0,
        "last_failure_reason": None
    }
    
    # Skip invalid endpoints
    if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
        result["last_failure_reason"] = "Invalid endpoint format"
        return result
    
    # Check if this endpoint has an API key
    has_api_key = "api-key" in endpoint.lower()
    
    # For endpoints with API keys, ensure they're only used with their specific service
    if has_api_key:
        # Only allow Helius API key with Helius endpoints
        if "api-key" in endpoint.lower() and "helius" not in endpoint.lower():
            result["last_failure_reason"] = "API key can only be used with its specific service"
            return result
        
        # For non-Helius endpoints, ensure they don't have any API key in the URL
        if HELIUS_API_KEY in endpoint and "helius" not in endpoint.lower():
            result["last_failure_reason"] = "Helius API key cannot be used with non-Helius endpoints"
            return result
    
    # Determine if this is likely a validator endpoint (IP address or non-standard port)
    is_validator_endpoint = (
        re.match(r'https?://\d+\.\d+\.\d+\.\d+', endpoint) is not None or
        ":8899" in endpoint
    )
    
    # For validator endpoints, use a shorter timeout
    if is_validator_endpoint:
        timeout = min(timeout, 5.0)
    
    # Check if this endpoint should bypass SSL verification
    ssl_verify = True
    try:
        from app.utils.solana_ssl_config import should_bypass_ssl_verification
        bypass_ssl = should_bypass_ssl_verification(endpoint)
        if bypass_ssl:
            ssl_verify = False
            logger.info(f"Bypassing SSL verification for endpoint: {endpoint}")
    except ImportError:
        logger.warning("Could not import solana_ssl_config, using default SSL settings")
    
    client = None
    
    try:
        # Create client with appropriate SSL settings
        client = SolanaClient(
            endpoint=endpoint,
            timeout=timeout,
            ssl_verify=ssl_verify
        )
        
        # Test getHealth - most basic test that almost all nodes support
        try:
            # Use _make_rpc_call which handles connection internally
            health_result = await client._make_rpc_call("getHealth", [])
            if health_result.get("result") == "ok":
                result["tests_passed"] += 1
                logger.info(f"Endpoint {endpoint} health check passed")
            else:
                logger.warning(f"Endpoint {endpoint} health check failed: {health_result}")
                result["last_failure_reason"] = f"Health check failed: {health_result}"
                result["persistent_failures"] += 1
        except Exception as e:
            logger.warning(f"Health check failed for {endpoint}: {str(e)}")
            result["last_failure_reason"] = f"Health check failed: {str(e)}"
            result["persistent_failures"] += 1
        result["tests_total"] += 1
        
        # Test getVersion
        try:
            # Use _make_rpc_call which handles connection internally
            version_result = await client._make_rpc_call("getVersion", [])
            if version_result and "result" in version_result and "solana-core" in version_result["result"]:
                result["tests_passed"] += 1
                logger.info(f"Endpoint {endpoint} successfully returned version info")
            else:
                logger.warning(f"Endpoint {endpoint} failed to return valid version info")
                result["last_failure_reason"] = "Failed to return valid version info"
                result["persistent_failures"] += 1
        except Exception as e:
            logger.warning(f"Version check failed for {endpoint}: {str(e)}")
            result["last_failure_reason"] = f"Version check failed: {str(e)}"
            result["persistent_failures"] += 1
        result["tests_total"] += 1
        
        # Test getLatestBlockhash or getRecentBlockhash
        blockhash_test_passed = False
        try:
            # Use _make_rpc_call which handles connection internally
            blockhash_result = await client._make_rpc_call("getLatestBlockhash", [{"commitment": "processed"}])
            if blockhash_result and "result" in blockhash_result:
                blockhash_info = blockhash_result["result"]
                if blockhash_info and "blockhash" in blockhash_info and "lastValidBlockHeight" in blockhash_info:
                    result["tests_passed"] += 1
                    blockhash_test_passed = True
                    logger.info(f"Endpoint {endpoint} successfully returned latest blockhash with lastValidBlockHeight")
                elif blockhash_info and "blockhash" in blockhash_info:
                    # Still pass if we have a blockhash but no lastValidBlockHeight
                    result["tests_passed"] += 1
                    blockhash_test_passed = True
                    logger.info(f"Endpoint {endpoint} successfully returned latest blockhash (without lastValidBlockHeight)")
            result["tests_total"] += 1
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Endpoint {endpoint} failed getLatestBlockhash: {error_msg}")
            
            # If getLatestBlockhash failed, try the deprecated getRecentBlockhash as fallback
            if not blockhash_test_passed:
                try:
                    # Use _make_rpc_call which handles connection internally
                    blockhash_result = await client._make_rpc_call("getRecentBlockhash", [{"commitment": "processed"}])
                    if blockhash_result and "result" in blockhash_result:
                        blockhash_info = blockhash_result["result"]
                        if blockhash_info and "blockhash" in blockhash_info and "lastValidBlockHeight" in blockhash_info:
                            result["tests_passed"] += 1
                            blockhash_test_passed = True
                            logger.info(f"Endpoint {endpoint} successfully returned recent blockhash with lastValidBlockHeight (deprecated method)")
                        elif blockhash_info and "blockhash" in blockhash_info:
                            # Still pass if we have a blockhash but no lastValidBlockHeight (older nodes)
                            result["tests_passed"] += 1
                            blockhash_test_passed = True
                            logger.info(f"Endpoint {endpoint} successfully returned recent blockhash (deprecated method, without lastValidBlockHeight)")
                    result["tests_total"] += 1
                except Exception as e2:
                    error_msg = str(e2)
                    logger.warning(f"Endpoint {endpoint} failed getRecentBlockhash: {error_msg}")
                    result["last_failure_reason"] = f"Blockhash methods: getLatestBlockhash: {error_msg}, getRecentBlockhash: {error_msg}"
                    result["persistent_failures"] += 1
                    result["tests_total"] += 1
            else:
                result["last_failure_reason"] = f"getLatestBlockhash: {error_msg}"
                result["persistent_failures"] += 1
                result["tests_total"] += 1
        
        # Calculate latency
        result["latency"] = time.time() - start_time
        
        # Mark as success if it passed at least 2 tests
        if result["tests_passed"] >= 2:
            result["status"] = "success"
            
        # If we have SSL errors, add the endpoint to the bypass list
        if result["persistent_failures"] > 0 and "SSL" in result.get("last_failure_reason", ""):
            try:
                from app.utils.solana_ssl_config import add_ssl_bypass_endpoint
                add_ssl_bypass_endpoint(endpoint)
            except ImportError:
                logger.warning("Could not import solana_ssl_config to add SSL bypass")
                
        return result
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error testing endpoint {endpoint}: {error_msg}")
        result["last_failure_reason"] = error_msg
        result["latency"] = time.time() - start_time
        return result
    finally:
        # Ensure client is closed
        if client:
            try:
                await client.close()
            except Exception as e:
                logger.error(f"Error closing client for {endpoint}: {str(e)}")

async def test_rpc_endpoints(endpoints: List[str], max_test: int = 50, parallel: int = 10) -> List[Dict[str, Any]]:
    """
    Test multiple RPC endpoints in parallel.
    
    Args:
        endpoints: List of RPC endpoint URLs to test
        max_test: Maximum number of endpoints to test
        parallel: Maximum number of parallel tests
        
    Returns:
        List of test results
    """
    # Ensure all endpoints have proper protocol
    formatted_endpoints = []
    for endpoint in endpoints:
        # Skip empty endpoints
        if not endpoint:
            continue
            
        # Handle unhashable types
        if isinstance(endpoint, (list, dict)):
            endpoint = str(endpoint)
            
        # Add protocol if missing
        if not isinstance(endpoint, str):
            logger.warning(f"Skipping non-string endpoint: {endpoint}")
            continue
            
        if not endpoint.startswith(("http://", "https://")):
            # Try both protocols
            formatted_endpoints.append(f"https://{endpoint}")
            formatted_endpoints.append(f"http://{endpoint}")
        else:
            formatted_endpoints.append(endpoint)
    
    # Remove duplicates using our helper function
    formatted_endpoints = get_unique_endpoints(formatted_endpoints)
    
    # Limit the number of endpoints to test
    if max_test and len(formatted_endpoints) > max_test:
        logger.info(f"Limiting to {max_test} endpoints for testing")
        formatted_endpoints = formatted_endpoints[:max_test]
    
    # Test endpoints using our own implementation
    logger.info(f"Testing {len(formatted_endpoints)} endpoints with a maximum of {parallel} parallel tests")
    tasks = [test_endpoint(endpoint) for endpoint in formatted_endpoints]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Extract successful endpoints
    successful_endpoints = []
    for result in results:
        if isinstance(result, dict) and result.get("status") == "success":
            successful_endpoints.append(result)
    
    # Log results
    logger.info(f"Successfully tested {len(successful_endpoints)} out of {len(formatted_endpoints)} endpoints")
    logger.info(f"Success rate: {(len(successful_endpoints) / len(formatted_endpoints)) * 100:.2f}%")
    
    return successful_endpoints

async def update_connection_pool(endpoints: List[str], max_test: int, max_endpoints: int) -> bool:
    """
    Update the Solana connection pool with the best performing endpoints.
    
    Args:
        endpoints: List of RPC endpoint URLs to test
        max_test: Maximum number of endpoints to test
        max_endpoints: Maximum number of endpoints to keep in the pool
        
    Returns:
        True if the pool was updated, False otherwise
    """
    if not endpoints:
        logger.warning("No endpoints provided for connection pool update")
        return False
        
    try:
        logger.info(f"Discovered {len(endpoints)} endpoints, testing up to {max_test}")
        test_results = await test_rpc_endpoints(endpoints, max_test)
        
        if not test_results:
            logger.warning("No valid endpoints found during testing")
            return False
            
        # Sort by score (highest first)
        test_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Get the best endpoints
        best_endpoints = [r.get('endpoint') for r in test_results[:max_endpoints]]
        
        if not best_endpoints:
            logger.warning("No valid endpoints after filtering")
            return False
            
        # Get the connection pool
        pool = await get_connection_pool()
        
        # Update the pool
        logger.info(f"Updating connection pool with {len(best_endpoints)} endpoints")
        await pool.update_endpoints(best_endpoints)
        logger.info("Connection pool updated successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating connection pool: {str(e)}")
        logger.exception(e)
        return False

async def update_rpc_pool(max_test: int = 50, max_endpoints: int = 10, quick_mode: bool = False) -> bool:
    """
    Update the RPC pool with the best performing endpoints.
    
    Args:
        max_test: Maximum number of endpoints to test
        max_endpoints: Maximum number of endpoints to keep in the pool
        quick_mode: If True, only test well-known endpoints
        
    Returns:
        True if the pool was updated, False otherwise
    """
    try:
        # Use a timeout for the entire update process
        return await asyncio.wait_for(
            _update_rpc_pool_impl(max_test, max_endpoints, quick_mode),
            timeout=120.0  # 2 minute timeout for the entire update process
        )
    except asyncio.TimeoutError:
        logger.warning("RPC pool update timed out after 120 seconds")
        return False
    except Exception as e:
        logger.error(f"Error updating RPC pool: {str(e)}")
        logger.exception(e)
        return False

async def _update_rpc_pool_impl(max_test: int = 50, max_endpoints: int = 10, quick_mode: bool = False) -> bool:
    """
    Implementation of the RPC pool update process.
    
    Args:
        max_test: Maximum number of endpoints to test
        max_endpoints: Maximum number of endpoints to keep in the pool
        quick_mode: If True, only test well-known endpoints
        
    Returns:
        True if the pool was updated, False otherwise
    """
    # Discover RPC nodes
    endpoints = await discover_rpc_nodes(quick_mode=quick_mode)
    
    # Test RPC endpoints
    test_results = await test_rpc_endpoints(endpoints, max_test)
    
    # Update connection pool
    selected_endpoints = await update_connection_pool(
        test_results, 
        max_test=max_test,
        max_endpoints=max_endpoints
    )
    
    # Log completion
    logger.info(f"RPC pool update completed")
    logger.info(f"Updated pool with {len(selected_endpoints)} endpoints")
    
    return selected_endpoints

async def main():
    """
    Main function to update the RPC connection pool.
    """
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Update the Solana RPC connection pool")
    parser.add_argument("--max-test", type=int, default=50, help="Maximum number of endpoints to test")
    parser.add_argument("--max-endpoints", type=int, default=10, help="Maximum number of endpoints to keep in the pool")
    parser.add_argument("--parallel", type=int, default=10, help="Maximum number of parallel tests")
    parser.add_argument("--quick", action="store_true", help="Only test well-known endpoints")
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Log startup
    logger.info("Starting RPC pool update...")
    
    try:
        # Update RPC pool
        success = await update_rpc_pool(
            max_test=args.max_test,
            max_endpoints=args.max_endpoints,
            quick_mode=args.quick
        )
        
        # Log completion
        if success:
            logger.info("RPC pool update completed successfully")
        else:
            logger.warning("RPC pool update completed with issues")
            
    except Exception as e:
        logger.error(f"Error updating RPC pool: {str(e)}")
        logger.exception(e)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
