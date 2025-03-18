"""
RPC Node Extractor - Utility for extracting and managing Solana RPC nodes
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio
import aiohttp
import json
import random
import traceback
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RPCNodeExtractor:
    """Extracts and manages Solana RPC nodes from various sources."""
    
    def __init__(self):
        """Initialize the RPC node extractor."""
        self.timeout = 10.0  # Reduced timeout for faster response
        self.cache = {}
        self.cache_ttl = timedelta(minutes=15)
        self.well_known_endpoints = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
            "https://rpc.ankr.com/solana",
            "https://solana-mainnet.g.alchemy.com/v2/demo",
            f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}",
            "https://solana.getblock.io/mainnet/",
            "https://solana.public-rpc.com",
            "https://api.mainnet.rpcpool.com"
        ]
        
    async def extract_rpc_nodes(self, endpoint: str) -> List[Dict[str, Any]]:
        """
        Extract RPC nodes from a Solana endpoint.
        
        Args:
            endpoint: The RPC endpoint to query
            
        Returns:
            List of RPC node information dictionaries
        """
        try:
            logger.info(f"Extracting RPC nodes from endpoint: {endpoint}")
            
            # Use a shorter timeout for faster response
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Make the getClusterNodes RPC call
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getClusterNodes",
                    "params": []
                }
                
                try:
                    async with session.post(endpoint, json=payload) as response:
                        if response.status != 200:
                            logger.error(f"Error response from {endpoint}: {response.status}")
                            # Try to read the error response body for more details
                            try:
                                error_body = await response.text()
                                logger.error(f"Error body from {endpoint}: {error_body[:500]}")
                            except Exception as body_error:
                                logger.error(f"Could not read error body: {str(body_error)}")
                            return []
                            
                        try:
                            data = await response.json()
                            
                            # Handle different response formats
                            if isinstance(data, dict) and 'result' in data:
                                nodes = data['result']
                                if isinstance(nodes, list):
                                    nodes_count = len(nodes)
                                    logger.info(f"Found {nodes_count} cluster nodes in dict response from {endpoint}")
                                    # Validate nodes
                                    valid_nodes = self._validate_nodes(nodes, endpoint)
                                    return valid_nodes
                                else:
                                    logger.warning(f"Non-list result from {endpoint}: {type(nodes)}")
                                    # Try to convert to list if possible
                                    if isinstance(nodes, dict) and self._is_node_object(nodes):
                                        logger.info(f"Converting single node dict to list from {endpoint}")
                                        return [nodes]
                                    return []
                                
                            elif isinstance(data, list):
                                # Some RPC endpoints return the result directly as a list
                                nodes_count = len(data)
                                logger.info(f"Found {nodes_count} cluster nodes in list response from {endpoint}")
                                # Validate nodes
                                valid_nodes = self._validate_nodes(data, endpoint)
                                return valid_nodes
                                
                            elif isinstance(data, dict) and 'error' in data:
                                error = data['error']
                                error_msg = error.get('message', str(error))
                                error_code = error.get('code', 0)
                                logger.error(f"RPC error from {endpoint}: {error_msg} (code: {error_code})")
                                return []
                                
                            else:
                                logger.warning(f"Unexpected response type from {endpoint}: {type(data)}")
                                if data is not None:
                                    logger.debug(f"Response content: {str(data)[:200]}...")
                                return []
                                
                        except Exception as json_error:
                            logger.error(f"Error parsing JSON from {endpoint}: {str(json_error)}")
                            return []
                except asyncio.TimeoutError:
                    logger.error(f"Timeout extracting RPC nodes from {endpoint}")
                    return []
                except aiohttp.ClientError as client_error:
                    logger.error(f"Client error extracting RPC nodes from {endpoint}: {str(client_error)}")
                    return []
                            
        except Exception as e:
            logger.error(f"Error extracting RPC nodes from {endpoint}: {str(e)}", exc_info=True)
            return []
    
    def _is_node_object(self, obj: Dict[str, Any]) -> bool:
        """
        Check if an object appears to be a Solana node.
        
        Args:
            obj: The object to check
            
        Returns:
            True if the object appears to be a node, False otherwise
        """
        # A node should have at least some of these keys
        node_keys = ['pubkey', 'gossip', 'tpu', 'rpc', 'version']
        return any(key in obj for key in node_keys)
    
    def _validate_nodes(self, nodes: List[Dict[str, Any]], endpoint: str) -> List[Dict[str, Any]]:
        """
        Validate and filter a list of nodes.
        
        Args:
            nodes: The list of nodes to validate
            endpoint: The endpoint that provided these nodes
            
        Returns:
            List of valid nodes
        """
        valid_nodes = []
        for node in nodes:
            if not isinstance(node, dict):
                logger.warning(f"Skipping non-dict node from {endpoint}: {type(node)}")
                continue
                
            if not self._is_node_object(node):
                logger.warning(f"Skipping invalid node object from {endpoint}: {list(node.keys())}")
                continue
                
            # Ensure required fields are present
            if 'pubkey' not in node:
                logger.warning(f"Skipping node without pubkey from {endpoint}")
                continue
                
            # Add the node to the valid list
            valid_nodes.append(node)
            
        logger.info(f"Validated {len(valid_nodes)}/{len(nodes)} nodes from {endpoint}")
        return valid_nodes
            
    async def get_all_rpc_nodes(self) -> List[Dict[str, Any]]:
        """
        Get RPC nodes from all available sources.
        
        Returns:
            List of RPC node information dictionaries
        """
        # Check cache first
        if 'all_nodes' in self.cache:
            cache_entry = self.cache['all_nodes']
            if datetime.now() - cache_entry['timestamp'] < self.cache_ttl:
                logger.info(f"Using cached RPC nodes ({len(cache_entry['data'])} nodes)")
                return cache_entry['data']
        
        all_nodes = []
        tasks = []
        errors = []
        
        # Randomize endpoints to avoid always hitting the same ones first
        endpoints = self.well_known_endpoints.copy()
        random.shuffle(endpoints)
        
        # Try all well-known endpoints with individual timeouts
        for endpoint in endpoints:
            task = asyncio.create_task(self.extract_rpc_nodes(endpoint))
            task.endpoint = endpoint  # Store the endpoint for error reporting
            tasks.append(task)
            
        # Wait for all tasks to complete or timeout after 4 seconds
        try:
            done, pending = await asyncio.wait(
                tasks, 
                timeout=4.0,  # Overall timeout for all tasks
                return_when=asyncio.ALL_COMPLETED
            )
            
            # Cancel any pending tasks
            for task in pending:
                logger.warning(f"Cancelling pending task for endpoint: {getattr(task, 'endpoint', 'unknown')}")
                task.cancel()
                
            # Process completed tasks
            for task in done:
                try:
                    result = task.result()
                    endpoint = getattr(task, 'endpoint', 'unknown')
                    if isinstance(result, list) and result:
                        logger.info(f"Successfully retrieved {len(result)} nodes from {endpoint}")
                        all_nodes.extend(result)
                    else:
                        logger.warning(f"No nodes retrieved from {endpoint}")
                except Exception as e:
                    endpoint = getattr(task, 'endpoint', 'unknown')
                    logger.error(f"Error in RPC node extraction task for {endpoint}: {str(e)}")
                    errors.append({
                        'endpoint': endpoint,
                        'error': str(e),
                        'type': type(e).__name__,
                        'timestamp': datetime.now().isoformat()
                    })
                    
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for RPC node extraction tasks")
            # Cancel all tasks
            for task in tasks:
                endpoint = getattr(task, 'endpoint', 'unknown')
                logger.warning(f"Cancelling task for {endpoint} due to global timeout")
                task.cancel()
                
        # Deduplicate nodes by pubkey
        unique_nodes = {}
        for node in all_nodes:
            if 'pubkey' in node:
                # If we already have this node, prefer the one with more information
                if node['pubkey'] in unique_nodes:
                    existing = unique_nodes[node['pubkey']]
                    # Count the number of non-empty fields in each node
                    existing_fields = sum(1 for k, v in existing.items() if v)
                    new_fields = sum(1 for k, v in node.items() if v)
                    
                    # Keep the node with more information
                    if new_fields > existing_fields:
                        unique_nodes[node['pubkey']] = node
                else:
                    unique_nodes[node['pubkey']] = node
                    
        # Convert back to list
        result_nodes = list(unique_nodes.values())
        
        # Only cache if we actually got some nodes
        if result_nodes:
            # Cache the result
            self.cache['all_nodes'] = {
                'data': result_nodes,
                'timestamp': datetime.now()
            }
            
        logger.info(f"Retrieved {len(result_nodes)} unique RPC nodes")
        
        # Log errors if we didn't get many nodes
        if len(result_nodes) < 10 and errors:
            logger.error(f"Few nodes retrieved ({len(result_nodes)}). Errors: {json.dumps(errors)}")
            
        return result_nodes
        
    async def check_node_health(self, rpc_url: str) -> Dict[str, Any]:
        """
        Check the health of an RPC node.
        
        Args:
            rpc_url: The RPC URL to check
            
        Returns:
            Dict with health check results
        """
        try:
            logger.debug(f"Checking health of RPC node: {rpc_url}")
            
            # Use a shorter timeout for health checks
            timeout = aiohttp.ClientTimeout(total=5.0)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Make a getHealth RPC call
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth",
                    "params": []
                }
                
                start_time = datetime.now()
                
                try:
                    async with session.post(rpc_url, json=payload) as response:
                        response_time = (datetime.now() - start_time).total_seconds()
                        
                        if response.status != 200:
                            logger.warning(f"Health check failed for {rpc_url}: HTTP {response.status}")
                            return {
                                'url': rpc_url,
                                'healthy': False,
                                'response_time': response_time,
                                'error': f"HTTP {response.status}"
                            }
                            
                        try:
                            data = await response.json()
                            
                            # Check for success in the response
                            if isinstance(data, dict):
                                if 'result' in data:
                                    result = data['result']
                                    healthy = result == "ok"
                                    logger.info(f"Health check for {rpc_url}: {result} (response time: {response_time:.2f}s)")
                                    return {
                                        'url': rpc_url,
                                        'healthy': healthy,
                                        'response_time': response_time,
                                        'result': result
                                    }
                                elif 'error' in data:
                                    error = data['error']
                                    error_msg = error.get('message', str(error))
                                    logger.warning(f"Health check error for {rpc_url}: {error_msg}")
                                    return {
                                        'url': rpc_url,
                                        'healthy': False,
                                        'response_time': response_time,
                                        'error': error_msg
                                    }
                            
                            logger.warning(f"Unexpected health check response from {rpc_url}: {data}")
                            return {
                                'url': rpc_url,
                                'healthy': False,
                                'response_time': response_time,
                                'error': "Unexpected response format"
                            }
                            
                        except Exception as json_error:
                            logger.error(f"Error parsing health check JSON from {rpc_url}: {str(json_error)}")
                            return {
                                'url': rpc_url,
                                'healthy': False,
                                'response_time': response_time,
                                'error': f"JSON parsing error: {str(json_error)}"
                            }
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Health check timeout for {rpc_url}")
                    return {
                        'url': rpc_url,
                        'healthy': False,
                        'error': "Timeout"
                    }
                except aiohttp.ClientError as client_error:
                    logger.warning(f"Health check client error for {rpc_url}: {str(client_error)}")
                    return {
                        'url': rpc_url,
                        'healthy': False,
                        'error': f"Connection error: {str(client_error)}"
                    }
                    
        except Exception as e:
            logger.error(f"Error checking health of {rpc_url}: {str(e)}", exc_info=True)
            return {
                'url': rpc_url,
                'healthy': False,
                'error': f"Exception: {str(e)}"
            }
            
    async def check_multiple_nodes_health(self, rpc_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Check the health of multiple RPC nodes in parallel.
        
        Args:
            rpc_urls: List of RPC URLs to check
            
        Returns:
            List of health check results
        """
        tasks = []
        for url in rpc_urls:
            task = asyncio.create_task(self.check_node_health(url))
            tasks.append(task)
            
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        health_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error checking health of {rpc_urls[i]}: {str(result)}")
                health_results.append({
                    'url': rpc_urls[i],
                    'healthy': False,
                    'error': f"Exception: {str(result)}"
                })
            else:
                health_results.append(result)
                
        return health_results
