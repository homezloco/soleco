"""
Solana RPC Nodes Router - Handles endpoints related to Solana RPC nodes
"""
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import ipaddress
import logging
import re
import time
import socket
import dns.resolver
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Query, HTTPException, Request
from app.utils.handlers.rpc_node_extractor import RPCNodeExtractor
from ..utils.solana_rpc import get_connection_pool
from ..utils.solana_query import SolanaQueryHandler
from ..utils.handlers.rpc_node_extractor import RPCNodeExtractor
from ..utils.solana_connection_pool import rpc_nodes_cache
from ..config import HELIUS_API_KEY

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(
    tags=["Soleco"],
    responses={404: {"description": "Not found"}},
)

# Initialize handlers
solana_query_handler = None
rpc_node_extractor = None

async def initialize_handlers():
    """Initialize handlers if they haven't been initialized yet."""
    global solana_query_handler, rpc_node_extractor
    
    if solana_query_handler is None:
        # Get connection pool
        pool = await get_connection_pool()
        solana_query_handler = SolanaQueryHandler(pool)
    
    if rpc_node_extractor is None:
        rpc_node_extractor = RPCNodeExtractor(solana_query_handler)

# Thread pool for DNS lookups
dns_executor = ThreadPoolExecutor(max_workers=20)

# Cache for DNS lookups to avoid redundant lookups
dns_cache = {}
DNS_CACHE_TTL = 3600  # 1 hour TTL for cache entries

# Thread pool for DNS lookups
dns_executor = ThreadPoolExecutor(max_workers=20)

# Cache for DNS lookups to avoid redundant lookups
dns_cache = {}
DNS_CACHE_TTL = 3600  # 1 hour TTL for cache entries

# DNS resolver configuration
dns_resolver = dns.resolver.Resolver()
dns_resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1', '1.0.0.1']
dns_resolver.timeout = 0.5  # Reduce timeout to 0.5 seconds
dns_resolver.lifetime = 1.0  # Reduce lifetime to 1 second

# Add logging level for DNS lookups - set to DEBUG to reduce console noise
DNS_LOOKUP_LOG_LEVEL = logging.DEBUG  # Change to logging.WARNING if you want to see all warnings

# Maximum concurrent DNS lookups
MAX_CONCURRENT_DNS_LOOKUPS = 10

# Maximum number of IP addresses to attempt to convert
MAX_IP_CONVERSIONS = 30

# Well-known RPC providers mapping - expanded with more providers
KNOWN_RPC_PROVIDERS = {
    # Public RPC providers - expanded list
    "mainnet.helius-rpc.com": f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}",
    "rpc.ankr.com/solana": "https://rpc.ankr.com/solana",
    "solana.public-rpc.com": "https://solana.public-rpc.com",
}

# Official Solana network endpoints
SOLANA_OFFICIAL_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://api.devnet.solana.com",
    "https://api.testnet.solana.com"
]

# Expanded patterns for identifying RPC providers
RPC_PROVIDER_PATTERNS = [
    (r'.*\.mainnet-beta\.solana\.com$', SOLANA_OFFICIAL_ENDPOINTS[0]),  # mainnet
    (r'.*\.devnet\.solana\.com$', SOLANA_OFFICIAL_ENDPOINTS[1]),  # devnet
    (r'.*\.testnet\.solana\.com$', SOLANA_OFFICIAL_ENDPOINTS[2]),  # testnet
    (r'.*\.helius-rpc\.com$', f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"),
    (r'.*\.ankr\.com$', "https://rpc.ankr.com/solana"),
    (r'.*\.public-rpc\.com$', "https://solana.public-rpc.com"),
]

# Expanded list of server hostname patterns to filter out
SERVER_HOSTNAME_PATTERNS = [
    r'^[\d\.-]+$',                  # IP-like hostname
    r'^ec2-',                       # AWS EC2 instance
    r'^vmi',                        # VPS instance
    r'^host',                       # Generic host
    r'^ns\d+',                      # Nameserver
    r'compute\.amazonaws\.com$',    # AWS compute
    r'vultrusercontent\.com$',      # Vultr
    r'^static\.',                   # Static IP
    r'\.static\.',                  # Static IP
    r'\.rev\.',                     # Reverse DNS
    r'\.ip-',                       # IP-based hostname
    r'\.vultr',                     # Vultr
    r'edgevanaservers\.com$',       # Edgevana
    r'contaboserver\.net$',         # Contabo
    r'\.amazonaws\.com$',           # AWS
]

async def lookup_hostname(ip_address: str) -> Optional[str]:
    """
    Perform a reverse DNS lookup to get the hostname for an IP address.
    
    Args:
        ip_address: The IP address to lookup
        
    Returns:
        The hostname if found, None otherwise
    """
    try:
        # Check cache first
        current_time = time.time()
        if ip_address in dns_cache:
            hostname, timestamp = dns_cache[ip_address]
            # If cache entry is still valid
            if current_time - timestamp < DNS_CACHE_TTL:
                return hostname
        
        # Try DNS resolver with PTR records
        addr = dns.reversename.from_address(ip_address)
        answers = dns_resolver.resolve(addr, 'PTR')
        if answers:
            hostname = str(answers[0]).rstrip('.')
            dns_cache[ip_address] = (hostname, current_time)
            return hostname
        
        # No hostname found
        dns_cache[ip_address] = (None, current_time)
        return None
        
    except Exception as e:
        # Log at the configured level instead of always WARNING
        logger.log(DNS_LOOKUP_LOG_LEVEL, f"Error in DNS lookup for {ip_address}: {str(e)}")
        # Cache the negative result to avoid repeated lookups
        current_time = time.time()
        dns_cache[ip_address] = (None, current_time)
        return None

async def format_rpc_url(endpoint: str) -> str:
    """
    Format an RPC endpoint as a proper URL with domain name where possible.
    
    Args:
        endpoint: The RPC endpoint (IP or hostname)
        
    Returns:
        Formatted RPC URL
    """
    # If it's already a URL, return it
    if endpoint.startswith(('http://', 'https://')):
        return endpoint
    
    # Extract the host and port
    parts = endpoint.split(':')
    host = parts[0]
    port = parts[1] if len(parts) > 1 else '8899'  # Default Solana RPC port
    
    # Check if it's a known RPC provider by hostname
    if host in KNOWN_RPC_PROVIDERS:
        return KNOWN_RPC_PROVIDERS[host]
    
    # Check if it matches any provider patterns directly
    for pattern, url in RPC_PROVIDER_PATTERNS:
        if re.match(pattern, host):
            return url
    
    # Check if it's an IP address
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False
    
    # If it's an IP, try to get the hostname only if we haven't cached a negative result
    hostname = None
    if is_ip:
        # Check if we've already tried this IP and failed
        current_time = time.time()
        if host in dns_cache:
            cached_hostname, timestamp = dns_cache[host]
            # If cache entry is still valid
            if current_time - timestamp < DNS_CACHE_TTL:
                hostname = cached_hostname
            # If we've tried recently and failed, don't try again
            elif cached_hostname is None and current_time - timestamp < 60:  # 1 minute negative caching
                hostname = None
            else:
                # Cache expired, try lookup
                try:
                    hostname = await lookup_hostname(host)
                except Exception:
                    hostname = None
        else:
            # Not in cache, try lookup
            try:
                hostname = await lookup_hostname(host)
            except Exception:
                hostname = None
    
    # Use the hostname if available, otherwise use the original host
    final_host = hostname if hostname else host
    
    # Check if the resolved hostname is a known RPC provider
    if final_host in KNOWN_RPC_PROVIDERS:
        return KNOWN_RPC_PROVIDERS[final_host]
    
    # Check if it matches any provider patterns
    for pattern, url in RPC_PROVIDER_PATTERNS:
        if re.match(pattern, final_host):
            return url
    
    # Otherwise, format as HTTPS URL
    return f"https://{final_host}:{port}"

async def format_rpc_urls_async(endpoints: List[str]) -> List[str]:
    """
    Format a list of RPC endpoints as proper URLs with domain names where possible.
    
    Args:
        endpoints: List of RPC endpoints (IPs or hostnames)
        
    Returns:
        List of formatted RPC URLs
    """
    # Process in batches to avoid too many concurrent DNS lookups
    formatted_urls = []
    batch_size = MAX_CONCURRENT_DNS_LOOKUPS
    
    # First, process all non-IP addresses (no DNS lookup needed)
    non_ip_endpoints = []
    ip_endpoints = []
    
    for endpoint in endpoints:
        # Skip empty endpoints
        if not endpoint:
            continue
            
        # If it's already a URL, add it directly
        if endpoint.startswith(('http://', 'https://')):
            formatted_urls.append(endpoint)
            continue
            
        # Extract the host
        parts = endpoint.split(':')
        host = parts[0]
        
        # Check if it's a known RPC provider by hostname
        if host in KNOWN_RPC_PROVIDERS:
            formatted_urls.append(KNOWN_RPC_PROVIDERS[host])
            continue
            
        # Check if it matches any provider patterns directly
        matched = False
        for pattern, url in RPC_PROVIDER_PATTERNS:
            if re.match(pattern, host):
                formatted_urls.append(url)
                matched = True
                break
                
        if matched:
            continue
            
        # Check if it's an IP address
        try:
            ipaddress.ip_address(host)
            ip_endpoints.append(endpoint)
        except ValueError:
            non_ip_endpoints.append(endpoint)
    
    # Process non-IP endpoints (no DNS lookup needed)
    for endpoint in non_ip_endpoints:
        formatted_urls.append(await format_rpc_url(endpoint))
    
    # Process IP endpoints in batches
    for i in range(0, len(ip_endpoints), batch_size):
        batch = ip_endpoints[i:i+batch_size]
        tasks = [format_rpc_url(endpoint) for endpoint in batch]
        batch_results = await asyncio.gather(*tasks)
        formatted_urls.extend(batch_results)
    
    return formatted_urls

async def convert_ips_to_hostnames(rpc_urls: List[str], max_conversions: int = 30) -> Tuple[List[str], Dict[str, int]]:
    """
    Convert IP addresses in RPC URLs to hostnames.
    
    Args:
        rpc_urls: List of RPC URLs to convert
        max_conversions: Maximum number of IP addresses to attempt to convert
        
    Returns:
        Tuple containing:
        - List of successfully converted URLs
        - Dictionary with conversion statistics
    """
    # Track conversion statistics
    conversion_stats = {
        "attempted": 0,
        "successful": 0,
        "failed": 0,
        "skipped": 0
    }
    
    # Track successfully converted URLs
    converted_urls = []
    
    # Filter out URLs that are likely IP addresses
    ip_urls = []
    for url in rpc_urls:
        # Extract host from URL
        parts = url.split(':')
        host = parts[0]
        port = parts[1] if len(parts) > 1 else '8899'
        
        # Check if it's an IP address
        try:
            ipaddress.ip_address(host)
            ip_urls.append((host, port))
        except ValueError:
            # Not an IP address, skip
            pass
    
    # Limit the number of conversions
    ip_urls = ip_urls[:max_conversions]
    conversion_stats["attempted"] = len(ip_urls)
    conversion_stats["skipped"] = len(rpc_urls) - len(ip_urls)
    
    # Process IP addresses in batches
    for i in range(0, len(ip_urls), MAX_CONCURRENT_DNS_LOOKUPS):
        batch = ip_urls[i:i+MAX_CONCURRENT_DNS_LOOKUPS]
        
        # Process each IP address in the batch
        for host, port in batch:
            try:
                hostname = await lookup_hostname(host)
                if hostname:
                    conversion_stats["successful"] += 1
                    converted_urls.append(f"https://{hostname}:{port}")
                    logger.info(f"Successfully converted {host} to {hostname}")
                else:
                    conversion_stats["failed"] += 1
            except Exception as e:
                logger.error(f"Error converting {host}: {str(e)}")
                conversion_stats["failed"] += 1
    
    return converted_urls, conversion_stats

def get_well_known_rpc_urls() -> List[str]:
    """
    Get a list of well-known RPC endpoint URLs.
    
    Returns:
        List[str]: A list of well-known RPC endpoint URLs.
    """
    # Start with Soleco-specific endpoints from KNOWN_RPC_PROVIDERS
    urls = list(KNOWN_RPC_PROVIDERS.values())
    
    # Add official Solana endpoints
    for endpoint in SOLANA_OFFICIAL_ENDPOINTS:
        if endpoint not in urls:
            urls.append(endpoint)
    
    # Remove any duplicates and return
    return list(dict.fromkeys(urls))

@router.get("/rpc-nodes", summary="Get Available Solana RPC Nodes")
async def get_rpc_nodes(
    include_details: bool = Query(False, description="Include detailed information for each RPC node"),
    health_check: bool = Query(False, description="Perform health checks on a sample of RPC nodes"),
    skip_dns_lookup: bool = Query(False, description="Skip DNS lookups for faster response time"),
    include_raw_urls: bool = Query(False, description="Include raw, unconverted RPC URLs in the response"),
    prioritize_clean_urls: bool = Query(True, description="Prioritize user-friendly URLs in the response"),
    include_well_known: bool = Query(True, description="Include well-known RPC endpoints in the response"),
    max_conversions: int = Query(30, description="Maximum number of IP addresses to attempt to convert to hostnames"),
    request: Request = None
) -> Dict[str, Any]:
    """
    Get a list of available Solana RPC nodes.
    
    Optionally include detailed information about each node and perform health checks.
    
    Returns:
        Dict[str, Any]: A dictionary containing the list of RPC nodes and additional metadata.
    """
    start_time = time.time()
    
    # Create a cache key based on the parameters
    cache_key = f"rpc_nodes_{include_details}_{health_check}_{skip_dns_lookup}_{include_raw_urls}_{prioritize_clean_urls}_{include_well_known}_{max_conversions}"
    
    # Check cache first
    cached_result = rpc_nodes_cache.get(cache_key)
    if cached_result:
        logger.info("Returning cached RPC nodes data")
        return cached_result
    
    # Initialize handlers if needed
    await initialize_handlers()
    
    # Get RPC nodes
    result = await rpc_node_extractor.get_all_rpc_nodes()
    
    # Extract RPC URLs
    rpc_urls = []
    if "rpc_nodes" in result:
        for node in result["rpc_nodes"]:
            if "rpc_endpoint" in node and node["rpc_endpoint"]:
                rpc_urls.append(node["rpc_endpoint"])
    
    # Convert IP addresses to hostnames if needed
    converted_urls = []
    conversion_stats = {
        "attempted": 0,
        "successful": 0,
        "failed": 0,
        "skipped": 0
    }
    
    if not skip_dns_lookup:
        converted_urls, conversion_stats = await convert_ips_to_hostnames(rpc_urls, max_conversions)
    
    # Add well-known RPC endpoints if requested
    well_known_urls = []
    solana_official_urls = []
    
    if include_well_known:
        # Get well-known RPC endpoints from Soleco
        well_known_urls = [url for url in list(KNOWN_RPC_PROVIDERS.values()) if url]
        
        # Get official Solana endpoints
        solana_official_urls = SOLANA_OFFICIAL_ENDPOINTS
    
    # Prepare the response
    response = {
        "total_nodes": len(result.get("rpc_nodes", [])),
        "version_distribution": result.get("version_distribution", {}),
        "well_known_rpc_urls": well_known_urls,
        "solana_official_urls": solana_official_urls,
        "conversion_stats": conversion_stats
    }
    
    # Include raw RPC URLs if requested
    if include_raw_urls:
        response["raw_rpc_urls"] = rpc_urls
    
    # Include converted URLs if available
    if converted_urls:
        response["converted_rpc_urls"] = converted_urls
    
    # Include detailed information if requested
    if include_details:
        response["rpc_nodes"] = result.get("rpc_nodes", [])
    
    # Add timestamp and execution time
    response["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    response["execution_time_ms"] = int((time.time() - start_time) * 1000)
    
    # Cache the result
    rpc_nodes_cache.set(cache_key, response)
    
    return response

def is_user_friendly_domain(domain: str) -> bool:
    """
    Check if a domain appears to be a user-friendly RPC provider domain.
    
    Args:
        domain: The domain name to check
        
    Returns:
        True if it appears to be a user-friendly domain, False otherwise
    """
    if not domain:
        return False
    
    # Check if it's a known provider
    if domain in KNOWN_RPC_PROVIDERS:
        return True
    
    # Check if it matches any provider patterns
    for pattern, _ in RPC_PROVIDER_PATTERNS:
        if re.match(pattern, domain):
            return True
    
    # Check if it's a server hostname
    for pattern in SERVER_HOSTNAME_PATTERNS:
        if re.search(pattern, domain):
            return False
    
    # Look for keywords that suggest it's a real domain
    good_keywords = ['solana', 'rpc', 'api', 'node', 'mainnet', 'service', 'blockchain']
    for keyword in good_keywords:
        if keyword in domain.lower():
            return True
    
    # Default to false for ambiguous cases
    return False

def match_provider_from_domain(domain: str) -> Optional[str]:
    """
    Try to match a domain to a known RPC provider.
    
    Args:
        domain: The domain name to match
        
    Returns:
        The URL of the matched provider, or None if no match
    """
    if not domain:
        return None
    
    # Direct match
    if domain in KNOWN_RPC_PROVIDERS:
        return KNOWN_RPC_PROVIDERS[domain]
    
    # Pattern match
    for pattern, provider_url in RPC_PROVIDER_PATTERNS:
        if re.match(pattern, domain):
            return provider_url
    
    return None

@router.get("/solana/rpc/stats")
async def get_rpc_stats():
    """
    Get statistics about RPC endpoint performance.
    
    Returns:
        Dict[str, Any]: Statistics about each endpoint
    """
    await initialize_handlers()
    
    # Get connection pool
    pool = await get_connection_pool()
    
    # Get endpoint stats
    stats = await pool.get_endpoint_stats()
    
    # Format the response
    formatted_stats = {
        "stats": stats,
        "summary": {
            "total_endpoints": len(stats),
            "endpoints_in_pool": sum(1 for _, data in stats.items() if data.get("in_pool", False)),
            "total_requests": sum(data.get("success_count", 0) + data.get("failure_count", 0) for _, data in stats.items()),
            "total_successes": sum(data.get("success_count", 0) for _, data in stats.items()),
            "total_failures": sum(data.get("failure_count", 0) for _, data in stats.items()),
            "overall_success_rate": 0
        }
    }
    
    # Calculate overall success rate
    total_requests = formatted_stats["summary"]["total_requests"]
    if total_requests > 0:
        formatted_stats["summary"]["overall_success_rate"] = (
            formatted_stats["summary"]["total_successes"] / total_requests * 100
        )
    
    # Add top performing endpoints
    endpoints_with_data = {
        endpoint: data for endpoint, data in stats.items() 
        if data.get("success_count", 0) > 0 and data.get("avg_latency", 0) > 0
    }
    
    if endpoints_with_data:
        sorted_by_latency = sorted(
            endpoints_with_data.items(),
            key=lambda x: x[1].get("avg_latency", float("inf"))
        )
        
        formatted_stats["top_performers"] = [
            {
                "endpoint": endpoint,
                "avg_latency": data.get("avg_latency", 0),
                "success_rate": data.get("success_rate", 0),
                "success_count": data.get("success_count", 0),
                "failure_count": data.get("failure_count", 0)
            }
            for endpoint, data in sorted_by_latency[:5]  # Top 5 performers
        ]
    else:
        formatted_stats["top_performers"] = []
    
    return formatted_stats

@router.get("/solana/rpc/filtered-stats", response_model=Dict[str, Any], tags=["solana"])
async def get_filtered_rpc_stats():
    """
    Get detailed statistics about RPC endpoint performance, excluding Helius endpoints.
    
    This endpoint provides the same information as the /rpc/stats endpoint but filters out
    any private endpoints with API keys for security reasons.
    
    Returns:
        Dict: Detailed statistics about each endpoint and summary metrics, with Helius endpoints filtered out
    """
    from app.utils.solana_rpc import get_connection_pool
    import logging
    
    # Get or create the connection pool
    pool = await get_connection_pool()
    
    # Initialize the pool if not already initialized
    if not pool._initialized:
        await pool.initialize()
        
    # Get the filtered stats directly from the connection pool
    stats = pool.get_filtered_rpc_stats()
    
    return stats

@router.get("/solana/rpc/test-fallback", response_model=Dict[str, Any], tags=["solana"])
async def test_fallback_endpoint():
    """
    Test endpoint that forces the use of a non-Helius fallback endpoint.
    
    This is for testing purposes only, to ensure that non-Helius endpoints are working correctly.
    
    Returns:
        Dict: Result of the RPC call using a non-Helius endpoint
    """
    from app.utils.solana_rpc import get_connection_pool, SolanaClient
    import logging
    import random
    import time
    
    # Get or create the connection pool
    pool = await get_connection_pool()
    
    # Initialize the pool if not already initialized
    if not pool._initialized:
        await pool.initialize()
    
    # Get a list of non-Helius endpoints
    non_helius_endpoints = [ep for ep in pool.endpoints if "helius" not in ep.lower()]
    
    if not non_helius_endpoints:
        return {"error": "No non-Helius endpoints available"}
    
    # Choose a random non-Helius endpoint
    endpoint = random.choice(non_helius_endpoints)
    
    # Create a client for this endpoint
    client = SolanaClient(
        endpoint=endpoint,
        timeout=pool.timeout,
        max_retries=pool.max_retries,
        retry_delay=pool.retry_delay
    )
    
    try:
        # Connect to the endpoint
        await client.connect()
        
        # Make a simple RPC call
        start_time = time.time()
        result = await client.get_version()
        latency = time.time() - start_time
        
        # Update the stats for this endpoint using the pool's method
        pool.update_endpoint_stats(endpoint, success=True, latency=latency)
        
        return {
            "endpoint": endpoint,
            "result": result,
            "latency": latency
        }
    except Exception as e:
        # Update stats to record the failure
        pool.update_endpoint_stats(endpoint, success=False)
        
        logging.error(f"Error testing fallback endpoint {endpoint}: {str(e)}")
        return {
            "endpoint": endpoint,
            "error": str(e),
            "latency": None
        }
    finally:
        # Close the client
        await client.close()
