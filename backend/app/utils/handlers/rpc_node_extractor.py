"""
RPC Node Extractor - Extracts and analyzes available RPC nodes from the Solana network
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio
from datetime import datetime, timezone
import random
import aiohttp
import json
from ..solana_query import SolanaQueryHandler
import time
import traceback

logger = logging.getLogger(__name__)

class RPCNodeExtractor:
    """Handles extraction and analysis of Solana RPC nodes."""
    
    def __init__(self, solana_query: SolanaQueryHandler, use_enhanced_mode: bool = True):
        """
        Initialize the RPC node extractor.
        
        Args:
            solana_query: SolanaQueryHandler instance for blockchain queries
            use_enhanced_mode: Whether to use enhanced error handling and reliability features
        """
        self.solana_query = solana_query
        self.timeout = 5.0  # Timeout for RPC health checks
        self.check_health = True  # Perform health checks on RPC nodes
        self.use_enhanced_mode = use_enhanced_mode
        self._errors = []  # List to store errors encountered during extraction
        
    def get_errors(self) -> List[Dict[str, str]]:
        """
        Get the list of errors encountered during extraction.
        
        Returns:
            List of error dictionaries with source and message
        """
        return self._errors
        
    def _add_error(self, source: str, message: str):
        """
        Add an error to the error list.
        
        Args:
            source: Source of the error (e.g., endpoint, method)
            message: Error message
        """
        if self.use_enhanced_mode:
            self._errors.append({
                "source": source,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            logger.warning(f"Error in {source}: {message}")
    
    async def get_all_rpc_nodes(self) -> Dict[str, Any]:
        """
        Extract all available RPC nodes from the Solana network.
        
        Returns:
            Dict containing RPC node information and statistics
        """
        try:
            # Get cluster nodes
            logger.info("Attempting to get cluster nodes from Solana network")
            
            # Ensure the solana_query handler is initialized
            if hasattr(self.solana_query, 'ensure_initialized'):
                try:
                    await self.solana_query.ensure_initialized()
                    logger.debug("SolanaQueryHandler initialized successfully")
                except Exception as init_error:
                    logger.error(f"Failed to initialize SolanaQueryHandler: {str(init_error)}", exc_info=True)
                    self._add_error("SolanaQueryHandler", str(init_error))
                    
                    # In enhanced mode, we continue even if initialization fails
                    if not self.use_enhanced_mode:
                        return {
                            "status": "error",
                            "error": "Failed to initialize Solana query handler",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
            
            # Get cluster nodes from the Solana network
            nodes = None
            try:
                logger.info("Requesting cluster nodes from Solana network")
                nodes = await self.solana_query.get_cluster_nodes()
            except Exception as nodes_error:
                logger.error(f"Error getting cluster nodes: {str(nodes_error)}", exc_info=True)
                self._add_error("get_cluster_nodes", str(nodes_error))
                
                # In enhanced mode, we'll try to get nodes from a different source
                if not self.use_enhanced_mode:
                    return {
                        "status": "error",
                        "error": "Failed to retrieve cluster nodes",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    # Try fallback method in enhanced mode
                    try:
                        logger.info("Attempting fallback method to get cluster nodes")
                        nodes = await self._get_cluster_nodes_fallback()
                    except Exception as fallback_error:
                        logger.error(f"Fallback method failed: {str(fallback_error)}", exc_info=True)
                        self._add_error("fallback_get_cluster_nodes", str(fallback_error))
            
            # Process nodes response
            if nodes is not None:
                # Check if the response is a list (expected format)
                if isinstance(nodes, list):
                    logger.info(f"Successfully retrieved {len(nodes)} cluster nodes")
                    
                    # Filter out nodes without pubkey or rpc
                    valid_nodes = []
                    for node in nodes:
                        if not isinstance(node, dict):
                            logger.warning(f"Skipping non-dict node: {type(node)}")
                            self._add_error("node_validation", f"Non-dict node found: {type(node)}")
                            continue
                            
                        if 'pubkey' not in node:
                            logger.warning("Skipping node without pubkey")
                            self._add_error("node_validation", "Node without pubkey found")
                            continue
                            
                        valid_nodes.append(node)
                    
                    logger.info(f"Found {len(valid_nodes)} valid nodes out of {len(nodes)} total nodes")
                    
                    return {
                        "status": "success",
                        "nodes": valid_nodes,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                # Check if the response is a dict with an error
                elif isinstance(nodes, dict) and 'error' in nodes:
                    error_msg = nodes.get('error', {}).get('message', str(nodes['error']))
                    logger.error(f"RPC error in response: {error_msg}")
                    self._add_error("get_cluster_nodes", error_msg)
                    
                    # In enhanced mode, we'll try to get nodes from a different source
                    if not self.use_enhanced_mode:
                        return {
                            "status": "error",
                            "error": f"RPC error: {error_msg}",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    else:
                        # Try fallback method in enhanced mode
                        try:
                            logger.info("Attempting fallback method after RPC error")
                            nodes = await self._get_cluster_nodes_fallback()
                            if isinstance(nodes, list):
                                return {
                                    "status": "success",
                                    "nodes": nodes,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                        except Exception as fallback_error:
                            logger.error(f"Fallback method failed: {str(fallback_error)}", exc_info=True)
                            self._add_error("fallback_after_error", str(fallback_error))
                            
                            # If we still have no nodes, return an empty list in enhanced mode
                            if self.use_enhanced_mode:
                                logger.warning("Using empty node list as fallback in enhanced mode")
                                return {
                                    "status": "partial_success",
                                    "nodes": [],
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "warning": "Using empty node list due to RPC errors"
                                }
                            
                            return {
                                "status": "error",
                                "error": f"RPC error: {error_msg}",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                else:
                    logger.error(f"Cannot process nodes response of type {type(nodes)}")
                    self._add_error("get_cluster_nodes", f"Invalid response format: {type(nodes)}")
                    
                    # In enhanced mode, we'll try to get nodes from a different source
                    if not self.use_enhanced_mode:
                        return {
                            "status": "error",
                            "error": "Invalid response format from Solana RPC",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    else:
                        # Try fallback method in enhanced mode
                        try:
                            logger.info("Attempting fallback method after invalid response format")
                            nodes = await self._get_cluster_nodes_fallback()
                            if isinstance(nodes, list):
                                return {
                                    "status": "success",
                                    "nodes": nodes,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                        except Exception as fallback_error:
                            logger.error(f"Fallback method failed: {str(fallback_error)}", exc_info=True)
                            self._add_error("fallback_after_invalid", str(fallback_error))
                            
                            # If we still have no nodes, return an empty list in enhanced mode
                            if self.use_enhanced_mode:
                                logger.warning("Using empty node list as fallback in enhanced mode")
                                return {
                                    "status": "partial_success",
                                    "nodes": [],
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "warning": "Using empty node list due to invalid response format"
                                }
                            
                            return {
                                "status": "error",
                                "error": "Invalid response format from Solana RPC",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
            else:
                # No nodes were returned
                logger.error("No nodes returned from Solana RPC")
                self._add_error("get_cluster_nodes", "No nodes returned")
                
                # In enhanced mode, we'll try to get nodes from a different source
                if not self.use_enhanced_mode:
                    return {
                        "status": "error",
                        "error": "No nodes returned from Solana RPC",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    # Try fallback method in enhanced mode
                    try:
                        logger.info("Attempting fallback method after no nodes returned")
                        nodes = await self._get_cluster_nodes_fallback()
                        if isinstance(nodes, list):
                            return {
                                "status": "success",
                                "nodes": nodes,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                    except Exception as fallback_error:
                        logger.error(f"Fallback method failed: {str(fallback_error)}", exc_info=True)
                        self._add_error("fallback_after_none", str(fallback_error))
                        
                        # If we still have no nodes, return an empty list in enhanced mode
                        if self.use_enhanced_mode:
                            logger.warning("Using empty node list as fallback in enhanced mode")
                            return {
                                "status": "partial_success",
                                "nodes": [],
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "warning": "Using empty node list due to no nodes returned"
                            }
                        
                        return {
                            "status": "error",
                            "error": "No nodes returned from Solana RPC",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
            
        except Exception as e:
            logger.error(f"Unexpected error getting RPC nodes: {str(e)}")
            logger.exception(e)
            self._add_error("get_all_rpc_nodes", str(e))
            
            # In enhanced mode, return an empty list instead of an error
            if self.use_enhanced_mode:
                logger.warning("Using empty node list as fallback in enhanced mode after exception")
                return {
                    "status": "partial_success",
                    "nodes": [],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "warning": "Using empty node list due to unexpected error"
                }
                
            return {
                "status": "error",
                "error": "Failed to retrieve cluster nodes",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    async def _get_cluster_nodes_fallback(self) -> List[Dict[str, Any]]:
        """
        Fallback method to get cluster nodes when the primary method fails.
        
        Returns:
            List of cluster nodes
        """
        logger.info("Using fallback method to get cluster nodes")
        
        # Try to get nodes from a different endpoint
        try:
            # Use a different client from the connection pool
            client = await self.solana_query.get_client(prefer_endpoint_type="mainnet")
            if client:
                try:
                    logger.info(f"Using fallback endpoint: {client.endpoint}")
                    nodes = await client.get_cluster_nodes()
                    if isinstance(nodes, list):
                        logger.info(f"Fallback successful, got {len(nodes)} nodes")
                        return nodes
                finally:
                    await self.solana_query.release_client(client)
        except Exception as e:
            logger.error(f"Fallback endpoint failed: {str(e)}")
            self._add_error("fallback_endpoint", str(e))
        
        # If that fails, try direct RPC calls to known endpoints
        try:
            logger.info("Trying direct RPC calls to known endpoints")
            nodes = await self._direct_rpc_call_for_nodes()
            if nodes:
                logger.info(f"Direct RPC call successful, got {len(nodes)} nodes")
                return nodes
        except Exception as e:
            logger.error(f"Direct RPC call failed: {str(e)}")
            self._add_error("direct_rpc_call", str(e))
        
        # If all else fails, return an empty list
        logger.warning("All fallback methods failed, returning empty list")
        return []
        
    async def _direct_rpc_call_for_nodes(self) -> List[Dict[str, Any]]:
        """
        Make direct RPC calls to known endpoints to get cluster nodes.
        
        Returns:
            List of cluster nodes
        """
        # List of known reliable endpoints
        endpoints = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
            "https://rpc.ankr.com/solana"
        ]
        
        # Try each endpoint
        for endpoint in endpoints:
            try:
                logger.info(f"Trying direct RPC call to {endpoint}")
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        endpoint,
                        json={"jsonrpc": "2.0", "id": 1, "method": "getClusterNodes"},
                        timeout=self.timeout
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "result" in data and isinstance(data["result"], list):
                                logger.info(f"Got {len(data['result'])} nodes from {endpoint}")
                                return data["result"]
            except Exception as e:
                logger.error(f"Error with endpoint {endpoint}: {str(e)}")
                self._add_error(f"endpoint_{endpoint}", str(e))
                continue
        
        # If we get here, all endpoints failed
        return []
    
    def _filter_reliable_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter nodes to only include those that are likely to be reliable.
        
        Args:
            nodes: List of node information dictionaries
            
        Returns:
            Filtered list of reliable nodes
        """
        if not nodes:
            return []
            
        # Start with all nodes
        filtered_nodes = nodes.copy()
        
        # Filter out nodes with unknown versions
        version_filtered = [node for node in filtered_nodes if node.get("version") != "unknown"]
        
        # If we have a reasonable number of nodes after filtering by version, use those
        if len(version_filtered) >= 10 or len(version_filtered) >= len(filtered_nodes) * 0.5:
            logger.info(f"Filtered nodes from {len(filtered_nodes)} to {len(version_filtered)} based on version")
            filtered_nodes = version_filtered
        else:
            logger.warning(f"After version filtering, only {len(version_filtered)} nodes remain. Using all {len(filtered_nodes)} nodes instead.")
        
        # Filter out nodes with very old feature sets if we have enough nodes
        if len(filtered_nodes) > 20:
            # Get feature sets and sort them
            feature_sets = [node.get("feature_set", 0) for node in filtered_nodes]
            feature_sets = sorted([fs for fs in feature_sets if fs > 0])
            
            # If we have feature sets, determine a reasonable cutoff
            if feature_sets:
                # Use the feature set at the 25th percentile as the cutoff
                cutoff_index = max(0, int(len(feature_sets) * 0.25) - 1)
                cutoff_feature_set = feature_sets[cutoff_index]
                
                # Filter out nodes with feature sets below the cutoff
                feature_filtered = [node for node in filtered_nodes if node.get("feature_set", 0) >= cutoff_feature_set]
                
                # If we still have enough nodes, use the feature-filtered set
                if len(feature_filtered) >= 10:
                    logger.info(f"Filtered nodes from {len(filtered_nodes)} to {len(feature_filtered)} based on feature set (cutoff: {cutoff_feature_set})")
                    filtered_nodes = feature_filtered
        
        # Log the filtering results
        if len(filtered_nodes) < len(nodes):
            logger.info(f"Filtered down to {len(filtered_nodes)} reliable nodes")
        else:
            logger.info(f"All {len(nodes)} nodes passed reliability filtering")
            
        return filtered_nodes
    
    async def extract_rpc_nodes(self, include_all: bool = False) -> List[Dict[str, Any]]:
        """
        Extract RPC nodes from the Solana network.
        
        Args:
            include_all: Whether to include all RPC nodes, even those that may be unreliable
            
        Returns:
            List of RPC node information dictionaries
        """
        try:
            start_time = time.time()
            logger.info(f"Extracting RPC nodes (include_all={include_all}, enhanced_mode={self.use_enhanced_mode})")
            
            # Get all RPC nodes
            result = await self.get_all_rpc_nodes()
            
            # Check if we got a successful response
            if result.get("status") != "success" and result.get("status") != "partial_success":
                detailed_error = result.get("error", "Unknown error")
                logger.error(f"RPC node extraction failed with detailed error: {detailed_error}")
                
                # In enhanced mode, we'll try to continue with an empty list
                if not self.use_enhanced_mode:
                    return []
                
                # In enhanced mode, we'll use an empty list and continue
                logger.warning("Using empty node list in enhanced mode after error")
                rpc_nodes = []
            else:
                rpc_nodes = result.get("nodes", [])
                logger.info(f"Found {len(rpc_nodes)} RPC nodes before filtering")
            
            # Check if we have any nodes
            if not rpc_nodes and not self.use_enhanced_mode:
                logger.warning("No RPC nodes found")
                return []
            
            # Process nodes to extract RPC endpoints
            processed_nodes = []
            for node in rpc_nodes:
                if not isinstance(node, dict):
                    logger.warning(f"Skipping non-dict node: {type(node)}")
                    self._add_error("node_processing", f"Non-dict node found: {type(node)}")
                    continue
                
                # Extract node information
                try:
                    pubkey = node.get('pubkey', '')
                    version = node.get('version', 'unknown')
                    feature_set = node.get('featureSet', 0)
                    gossip = node.get('gossip', '')
                    shred_version = node.get('shredVersion', 0)
                    
                    # Extract RPC endpoint if available
                    rpc_endpoint = None
                    if 'rpc' in node:
                        rpc_endpoint = node['rpc']
                    
                    # Skip nodes without RPC endpoints
                    if not rpc_endpoint:
                        logger.debug(f"Skipping node {pubkey} without RPC endpoint")
                        continue
                    
                    # Create node info
                    node_info = {
                        'pubkey': pubkey,
                        'rpc_endpoint': rpc_endpoint,
                        'version': version,
                        'feature_set': feature_set,
                        'gossip': gossip,
                        'shred_version': shred_version
                    }
                    
                    processed_nodes.append(node_info)
                except Exception as node_error:
                    logger.warning(f"Error processing node {node.get('pubkey', 'unknown')}: {str(node_error)}")
                    self._add_error(f"node_{node.get('pubkey', 'unknown')}", str(node_error))
                    continue
            
            # Filter out potentially unreliable nodes unless include_all is True
            filtered_nodes = processed_nodes
            if not include_all:
                filtered_nodes = self._filter_reliable_nodes(processed_nodes)
                logger.info(f"Filtered down to {len(filtered_nodes)} reliable RPC nodes")
            
            # Perform health checks if requested
            if self.check_health:
                try:
                    logger.info("Performing health checks on RPC nodes")
                    # Only check a sample of nodes if there are many
                    nodes_to_check = filtered_nodes
                    if len(filtered_nodes) > 10:
                        # Check 10 random nodes
                        nodes_to_check = random.sample(filtered_nodes, 10)
                        logger.info(f"Checking health of 10 random nodes out of {len(filtered_nodes)}")
                    
                    # Check health of selected nodes
                    health_checked_nodes = await self._check_nodes_health(nodes_to_check)
                    
                    # Update the filtered nodes with health information
                    for checked_node in health_checked_nodes:
                        # Find the corresponding node in filtered_nodes
                        for node in filtered_nodes:
                            if node['rpc_endpoint'] == checked_node['rpc_endpoint']:
                                # Add health information
                                node["health"] = checked_node.get("health", False)
                                if "health_error" in checked_node:
                                    node["health_error"] = checked_node["health_error"]
                                break
                except Exception as health_error:
                    logger.error(f"Error during health checks: {str(health_error)}", exc_info=True)
                    self._add_error("health checks", str(health_error))
                    # Continue with the nodes we have, even if health checks failed
            
            # Log execution time
            execution_time = time.time() - start_time
            logger.info(f"Extracted and processed {len(filtered_nodes)} RPC nodes in {execution_time:.2f} seconds")
            
            return filtered_nodes
            
        except Exception as e:
            logger.error(f"Error extracting RPC nodes: {str(e)}")
            logger.exception(e)
            self._add_error("extract_rpc_nodes", str(e))
            
            # In enhanced mode, return an empty list instead of failing
            if self.use_enhanced_mode:
                logger.warning("Returning empty list in enhanced mode after exception")
                return []
                
            return []
    
    async def _check_nodes_health(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Check the health of a list of RPC nodes.
        
        Args:
            nodes: List of node information dictionaries
            
        Returns:
            List of node information dictionaries with health information added
        """
        if not nodes:
            return []
            
        # Create a copy of the nodes to avoid modifying the original
        health_results = []
        
        # Check each node's health
        for node in nodes:
            try:
                rpc_endpoint = node.get("rpc_endpoint")
                if not rpc_endpoint:
                    logger.warning(f"Node {node.get('pubkey', 'unknown')} has no RPC endpoint")
                    health_results.append({
                        "rpc_endpoint": rpc_endpoint,
                        "health": False,
                        "health_error": "No RPC endpoint available"
                    })
                    continue
                
                # Add http:// prefix if needed
                if not rpc_endpoint.startswith("http"):
                    rpc_endpoint = f"http://{rpc_endpoint}"
                
                # Check node health
                health_info = await self._check_node_health(rpc_endpoint)
                
                # Add the health information to the result
                health_result = {
                    "rpc_endpoint": node.get("rpc_endpoint"),
                    "health": health_info.get("healthy", False)
                }
                
                # Add error information if available
                if "error" in health_info:
                    health_result["health_error"] = health_info["error"]
                
                # Add response time if available
                if "response_time_ms" in health_info:
                    health_result["response_time_ms"] = health_info["response_time_ms"]
                
                health_results.append(health_result)
                
            except Exception as e:
                logger.error(f"Error checking health for node {node.get('pubkey', 'unknown')}: {str(e)}")
                self._add_error(f"health_check_{node.get('pubkey', 'unknown')}", str(e))
                
                health_results.append({
                    "rpc_endpoint": node.get("rpc_endpoint"),
                    "health": False,
                    "health_error": str(e)
                })
        
        return health_results
        
    async def _check_node_health(self, rpc_endpoint: str) -> Dict[str, Any]:
        """
        Check the health of a single RPC node.
        
        Args:
            rpc_endpoint: RPC endpoint URL
            
        Returns:
            Dictionary with health information
        """
        start_time = time.time()
        result = {
            "healthy": False,
            "endpoint": rpc_endpoint
        }
        
        try:
            # Create a client with a short timeout
            timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Create the JSON-RPC request
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth",
                    "params": []
                }
                
                # Make the request
                async with session.post(rpc_endpoint, json=payload) as response:
                    # Calculate response time
                    response_time_ms = (time.time() - start_time) * 1000
                    result["response_time_ms"] = round(response_time_ms, 2)
                    
                    # Check if the response is OK
                    if response.status != 200:
                        result["error"] = f"HTTP error {response.status}"
                        logger.warning(f"Health check failed for {rpc_endpoint}: HTTP {response.status}")
                        return result
                    
                    # Parse the response
                    response_data = await response.json()
                    
                    # Check for JSON-RPC error
                    if "error" in response_data:
                        error_message = response_data["error"].get("message", "Unknown JSON-RPC error")
                        result["error"] = f"JSON-RPC error: {error_message}"
                        logger.warning(f"Health check failed for {rpc_endpoint}: {error_message}")
                        return result
                    
                    # Check the result
                    health_status = response_data.get("result", "")
                    if health_status == "ok":
                        result["healthy"] = True
                        logger.debug(f"Health check passed for {rpc_endpoint} in {response_time_ms:.2f}ms")
                    else:
                        result["error"] = f"Unexpected health status: {health_status}"
                        logger.warning(f"Health check failed for {rpc_endpoint}: Unexpected status {health_status}")
                    
                    return result
                    
        except asyncio.TimeoutError:
            result["error"] = "Timeout"
            logger.warning(f"Health check timed out for {rpc_endpoint}")
            return result
            
        except aiohttp.ClientError as e:
            result["error"] = f"Connection error: {str(e)}"
            logger.warning(f"Health check connection error for {rpc_endpoint}: {str(e)}")
            return result
            
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error during health check for {rpc_endpoint}: {str(e)}")
            return result
    
    def _get_current_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    async def get_network_status(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the Solana network status with enhanced error handling.
        
        Returns:
            Dict with network status information including:
            - node_count: Total number of nodes
            - active_nodes: Number of active nodes
            - delinquent_nodes: Number of delinquent nodes
            - version_distribution: Distribution of node versions
            - feature_set_distribution: Distribution of feature sets
            - stake_distribution: Distribution of stake among validators
            - errors: Any errors encountered during data collection
            - status: Overall network status (healthy, degraded, or unhealthy)
        """
        # Initialize the result structure
        result = {
            'node_count': 0,
            'active_nodes': 0,
            'delinquent_nodes': 0,
            'version_distribution': {},
            'feature_set_distribution': {},
            'stake_distribution': {},
            'errors': [],
            'status': 'unknown',
            'timestamp': datetime.now().isoformat()
        }
        
        # Reset errors for this operation
        self._reset_errors()
        
        try:
            start_time = time.time()
            logger.info(f"Retrieving network status with enhanced error handling (enhanced_mode={self.use_enhanced_mode})")
            
            # Get all RPC nodes first
            nodes_result = await self.get_all_rpc_nodes()
            
            # Check if we got a successful response
            if nodes_result.get("status") != "success" and nodes_result.get("status") != "partial_success":
                detailed_error = nodes_result.get("error", "Unknown error")
                logger.error(f"Network status retrieval failed with detailed error: {detailed_error}")
                
                # Add error to the result
                result['errors'].append({
                    'source': 'get_all_rpc_nodes',
                    'error': detailed_error,
                    'timestamp': datetime.now().isoformat()
                })
                
                # In enhanced mode, we'll try to continue with an empty list
                if not self.use_enhanced_mode:
                    result['status'] = 'error'
                    return result
                
                # In enhanced mode, we'll use an empty list and continue
                logger.warning("Using empty node list in enhanced mode after error")
                nodes = []
            else:
                nodes = nodes_result.get("nodes", [])
                logger.info(f"Found {len(nodes)} nodes for network status analysis")
            
            # Process node information
            result['node_count'] = len(nodes)
            
            # Track version and feature set distribution
            version_counts = {}
            feature_set_counts = {}
            
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                    
                # Count active vs delinquent nodes
                if node.get('delinquent', False):
                    result['delinquent_nodes'] += 1
                else:
                    result['active_nodes'] += 1
                    
                # Track version distribution
                version = node.get('version', 'unknown')
                version_counts[version] = version_counts.get(version, 0) + 1
                
                # Track feature set distribution
                feature_set = node.get('feature_set', 0)
                feature_set_counts[feature_set] = feature_set_counts.get(feature_set, 0) + 1
            
            # Convert counts to percentages
            total_nodes = result['node_count']
            
            if total_nodes > 0:
                for version, count in version_counts.items():
                    result['version_distribution'][version] = {
                        'count': count,
                        'percentage': round((count / total_nodes) * 100, 2)
                    }
                    
                for feature_set, count in feature_set_counts.items():
                    result['feature_set_distribution'][str(feature_set)] = {
                        'count': count,
                        'percentage': round((count / total_nodes) * 100, 2)
                    }
            
            # Try to get vote accounts for stake distribution
            try:
                # Create a client with a short timeout
                timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
                
                # Try up to 3 different endpoints
                endpoints = await self._get_reliable_endpoints(3)
                
                vote_accounts = None
                vote_accounts_error = None
                
                for endpoint in endpoints:
                    try:
                        logger.info(f"Fetching vote accounts from {endpoint}")
                        
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            # Create the JSON-RPC request
                            payload = {
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "getVoteAccounts",
                                "params": []
                            }
                            
                            # Make the request
                            async with session.post(endpoint, json=payload) as response:
                                if response.status != 200:
                                    logger.warning(f"HTTP error {response.status} from {endpoint} when fetching vote accounts")
                                    continue
                                
                                # Parse the response
                                response_data = await response.json()
                                
                                # Check for JSON-RPC error
                                if "error" in response_data:
                                    error_message = response_data["error"].get("message", "Unknown JSON-RPC error")
                                    logger.warning(f"JSON-RPC error from {endpoint} when fetching vote accounts: {error_message}")
                                    continue
                                
                                # Check the result
                                if "result" in response_data:
                                    vote_accounts = response_data["result"]
                                    logger.info(f"Successfully retrieved vote accounts from {endpoint}")
                                    break
                    except Exception as e:
                        logger.warning(f"Error fetching vote accounts from {endpoint}: {str(e)}")
                        vote_accounts_error = str(e)
                        continue
                
                if vote_accounts and isinstance(vote_accounts, dict):
                    # Calculate total stake
                    current = vote_accounts.get('current', [])
                    delinquent = vote_accounts.get('delinquent', [])
                    
                    total_stake = 0
                    for validator in current + delinquent:
                        total_stake += validator.get('activatedStake', 0)
                        
                    # Only process if we have some stake
                    if total_stake > 0:
                        # Group validators by stake
                        stake_groups = {
                            'high': {'count': 0, 'stake': 0},  # Top 10% of validators by stake
                            'medium': {'count': 0, 'stake': 0},  # Middle 40% of validators
                            'low': {'count': 0, 'stake': 0},    # Bottom 50% of validators
                            'delinquent': {'count': 0, 'stake': 0}  # Delinquent validators
                        }
                        
                        # Process current validators
                        sorted_validators = sorted(current, key=lambda v: v.get('activatedStake', 0), reverse=True)
                        validator_count = len(sorted_validators)
                        
                        if validator_count > 0:
                            # Determine thresholds
                            high_threshold = max(1, int(validator_count * 0.1))
                            medium_threshold = max(high_threshold, int(validator_count * 0.5))
                            
                            # Categorize validators
                            for i, validator in enumerate(sorted_validators):
                                stake = validator.get('activatedStake', 0)
                                
                                if i < high_threshold:
                                    stake_groups['high']['count'] += 1
                                    stake_groups['high']['stake'] += stake
                                elif i < medium_threshold:
                                    stake_groups['medium']['count'] += 1
                                    stake_groups['medium']['stake'] += stake
                                else:
                                    stake_groups['low']['count'] += 1
                                    stake_groups['low']['stake'] += stake
                                    
                        # Process delinquent validators
                        for validator in delinquent:
                            stake = validator.get('activatedStake', 0)
                            stake_groups['delinquent']['count'] += 1
                            stake_groups['delinquent']['stake'] += stake
                            
                        # Calculate percentages
                        for group, data in stake_groups.items():
                            data['stake_percentage'] = round((data['stake'] / total_stake) * 100, 2)
                            
                        result['stake_distribution'] = stake_groups
                else:
                    error_msg = "Failed to retrieve vote accounts"
                    if vote_accounts_error:
                        error_msg += f": {vote_accounts_error}"
                        
                    result['errors'].append({
                        'source': 'get_vote_accounts',
                        'error': error_msg,
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as vote_error:
                logger.error(f"Error processing vote accounts: {str(vote_error)}", exc_info=True)
                result['errors'].append({
                    'source': 'get_vote_accounts',
                    'error': str(vote_error),
                    'type': type(vote_error).__name__,
                    'timestamp': datetime.now().isoformat()
                })
                
            # Determine overall network status
            active_percentage = 0
            if total_nodes > 0:
                active_percentage = (result['active_nodes'] / total_nodes) * 100
                
            if active_percentage >= 95:
                result['status'] = 'healthy'
            elif active_percentage >= 80:
                result['status'] = 'degraded'
            else:
                result['status'] = 'unhealthy'
                
            # Add performance metrics if available
            try:
                performance_data = await self._get_recent_performance()
                
                if performance_data and isinstance(performance_data, list) and len(performance_data) > 0:
                    # Calculate average TPS from the most recent samples
                    recent_samples = performance_data[:min(5, len(performance_data))]
                    
                    total_tps = 0
                    sample_count = 0
                    
                    for sample in recent_samples:
                        if isinstance(sample, dict) and 'numTransactions' in sample and 'samplePeriodSecs' in sample:
                            num_txns = sample.get('numTransactions', 0)
                            period_secs = sample.get('samplePeriodSecs', 1)
                            
                            if period_secs > 0:
                                tps = num_txns / period_secs
                                total_tps += tps
                                sample_count += 1
                                
                    if sample_count > 0:
                        result['average_tps'] = round(total_tps / sample_count, 2)
                        
                else:
                    result['errors'].append({
                        'source': 'get_recent_performance',
                        'error': 'Failed to retrieve performance samples',
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as perf_error:
                logger.error(f"Error processing performance data: {str(perf_error)}", exc_info=True)
                result['errors'].append({
                    'source': 'get_recent_performance',
                    'error': str(perf_error),
                    'type': type(perf_error).__name__,
                    'timestamp': datetime.now().isoformat()
                })
                
            # Add any errors from the error collection
            if self._errors:
                for source, error in self._errors.items():
                    result['errors'].append({
                        'source': source,
                        'error': error,
                        'timestamp': datetime.now().isoformat()
                    })
            
            # Log execution time
            execution_time = time.time() - start_time
            logger.info(f"Network status retrieval completed in {execution_time:.2f} seconds")
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving network status: {str(e)}", exc_info=True)
            self._add_error("get_network_status", str(e))
            
            result['errors'].append({
                'source': 'get_network_status',
                'error': str(e),
                'type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            })
            
            result['status'] = 'error'
            return result
            
    async def _get_reliable_endpoints(self, count: int = 3) -> List[str]:
        """
        Get a list of reliable RPC endpoints to use for queries.
        
        Args:
            count: Number of endpoints to return
            
        Returns:
            List of reliable RPC endpoint URLs
        """
        try:
            # Start with some known public endpoints
            known_endpoints = [
                "https://api.mainnet-beta.solana.com",
                "https://solana-api.projectserum.com",
                "https://rpc.ankr.com/solana"
            ]
            
            # Try to get nodes from our extractor
            nodes_result = await self.get_all_rpc_nodes()
            
            if nodes_result.get("status") in ["success", "partial_success"]:
                nodes = nodes_result.get("nodes", [])
                
                # Extract RPC endpoints
                endpoints = []
                for node in nodes:
                    if isinstance(node, dict) and 'rpc_endpoint' in node:
                        endpoint = node['rpc_endpoint']
                        if endpoint and isinstance(endpoint, str):
                            # Add http:// prefix if needed
                            if not endpoint.startswith(('http://', 'https://')):
                                endpoint = f"https://{endpoint}"
                            endpoints.append(endpoint)
                
                # Combine with known endpoints and return the requested number
                all_endpoints = list(set(known_endpoints + endpoints))
                return all_endpoints[:count]
            
            # If we couldn't get nodes, return the known endpoints
            return known_endpoints[:count]
            
        except Exception as e:
            logger.error(f"Error getting reliable endpoints: {str(e)}")
            return ["https://api.mainnet-beta.solana.com"]
            
    async def _get_recent_performance(self) -> List[Dict[str, Any]]:
        """
        Get recent performance samples from the Solana network.
        
        Returns:
            List of performance sample dictionaries
        """
        try:
            # Create a client with a short timeout
            timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
            
            # Try up to 3 different endpoints
            endpoints = await self._get_reliable_endpoints(3)
            
            for endpoint in endpoints:
                try:
                    logger.info(f"Fetching recent performance from {endpoint}")
                    
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        # Create the JSON-RPC request
                        payload = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "getRecentPerformanceSamples",
                            "params": [5]  # Get 5 most recent samples
                        }
                        
                        # Make the request
                        async with session.post(endpoint, json=payload) as response:
                            if response.status != 200:
                                logger.warning(f"HTTP error {response.status} from {endpoint} when fetching performance samples")
                                continue
                            
                            # Parse the response
                            response_data = await response.json()
                            
                            # Check for JSON-RPC error
                            if "error" in response_data:
                                error_message = response_data["error"].get("message", "Unknown JSON-RPC error")
                                logger.warning(f"JSON-RPC error from {endpoint} when fetching performance samples: {error_message}")
                                continue
                            
                            # Check the result
                            if "result" in response_data:
                                samples = response_data["result"]
                                if isinstance(samples, list):
                                    logger.info(f"Successfully retrieved {len(samples)} performance samples from {endpoint}")
                                    return samples
                except Exception as e:
                    logger.warning(f"Error fetching performance samples from {endpoint}: {str(e)}")
                    continue
            
            # If we get here, all endpoints failed
            logger.error("Failed to retrieve performance samples from any endpoint")
            return []
            
        except Exception as e:
            logger.error(f"Error getting recent performance: {str(e)}")
            self._add_error("get_recent_performance", str(e))
            return []
