"""
RPC Node Extractor - Extracts and analyzes available RPC nodes from the Solana network
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio
from datetime import datetime, timezone
import random
import aiohttp
from ..solana_query import SolanaQueryHandler

logger = logging.getLogger(__name__)

class RPCNodeExtractor:
    """Handles extraction and analysis of Solana RPC nodes."""
    
    def __init__(self, solana_query: SolanaQueryHandler):
        """
        Initialize the RPC node extractor.
        
        Args:
            solana_query: SolanaQueryHandler instance for blockchain queries
        """
        self.solana_query = solana_query
        self.timeout = 5.0  # Timeout for RPC health checks
        
    async def get_all_rpc_nodes(self) -> Dict[str, Any]:
        """
        Extract all available RPC nodes from the Solana network.
        
        Returns:
            Dict containing RPC node information and statistics
        """
        try:
            # Get cluster nodes
            logger.info("Attempting to get cluster nodes from Solana network")
            nodes = await self.solana_query.get_cluster_nodes()
            
            if not nodes:
                logger.warning("No cluster nodes returned from Solana network")
                return {
                    "status": "error",
                    "error": "Failed to retrieve cluster nodes",
                    "timestamp": self._get_current_timestamp(),
                    "rpc_nodes": []
                }
            
            logger.info(f"Successfully retrieved {len(nodes)} cluster nodes")
            
            # Extract RPC nodes
            rpc_nodes = []
            for node in nodes:
                rpc_endpoint = node.get('rpc')
                if rpc_endpoint:
                    rpc_nodes.append({
                        'pubkey': node.get('pubkey', ''),
                        'rpc_endpoint': rpc_endpoint,
                        'version': node.get('version', 'unknown'),
                        'feature_set': node.get('featureSet', 0),
                        'gossip': node.get('gossip', ''),
                        'shred_version': node.get('shredVersion', 0)
                    })
            
            logger.info(f"Extracted {len(rpc_nodes)} RPC nodes from cluster nodes")
            
            # Check health of a sample of RPC nodes (to avoid too many requests)
            sample_size = min(20, len(rpc_nodes))  # Check up to 20 nodes
            if sample_size > 0:
                sample_nodes = random.sample(rpc_nodes, sample_size)
                health_results = await self._check_nodes_health(sample_nodes)
                
                # Calculate health statistics
                healthy_count = sum(1 for result in health_results if result['is_healthy'])
                health_percentage = (healthy_count / sample_size) * 100 if sample_size > 0 else 0
            else:
                health_results = []
                health_percentage = 0
            
            # Group nodes by version
            version_groups = {}
            for node in rpc_nodes:
                version = node.get('version', 'unknown')
                if version in version_groups:
                    version_groups[version].append(node)
                else:
                    version_groups[version] = [node]
            
            # Create version summary
            version_summary = [
                {
                    'version': version,
                    'count': len(nodes),
                    'percentage': (len(nodes) / len(rpc_nodes)) * 100 if rpc_nodes else 0
                }
                for version, nodes in sorted(
                    version_groups.items(),
                    key=lambda x: len(x[1]),
                    reverse=True
                )
            ]
            
            return {
                "status": "success",
                "timestamp": self._get_current_timestamp(),
                "total_rpc_nodes": len(rpc_nodes),
                "health_sample_size": sample_size,
                "estimated_health_percentage": round(health_percentage, 2),
                "version_distribution": version_summary[:5],  # Top 5 versions
                "rpc_nodes": rpc_nodes
            }
            
        except Exception as e:
            logger.error(f"Error extracting RPC nodes: {str(e)}")
            logger.exception(e)
            return {
                "status": "error",
                "error": f"Failed to extract RPC nodes: {str(e)}",
                "timestamp": self._get_current_timestamp()
            }
    
    async def _check_nodes_health(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Check the health of a list of RPC nodes.
        
        Args:
            nodes: List of RPC node information
            
        Returns:
            List of health check results
        """
        tasks = [self._check_node_health(node) for node in nodes]
        return await asyncio.gather(*tasks)
    
    async def _check_node_health(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check the health of a single RPC node.
        
        Args:
            node: RPC node information
            
        Returns:
            Dict containing health check results
        """
        rpc_endpoint = node.get('rpc_endpoint')
        result = {
            'pubkey': node.get('pubkey', ''),
            'rpc_endpoint': rpc_endpoint,
            'is_healthy': False,
            'response_time_ms': None,
            'error': None
        }
        
        if not rpc_endpoint:
            result['error'] = 'No RPC endpoint provided'
            return result
        
        # Ensure the endpoint has http/https prefix
        if not rpc_endpoint.startswith(('http://', 'https://')):
            rpc_endpoint = f"http://{rpc_endpoint}"
        
        try:
            # Simple health check payload
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getHealth"
            }
            
            start_time = datetime.now()
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    rpc_endpoint,
                    json=payload,
                    timeout=self.timeout
                ) as response:
                    response_data = await response.json()
                    end_time = datetime.now()
                    
                    # Calculate response time
                    response_time = (end_time - start_time).total_seconds() * 1000  # ms
                    result['response_time_ms'] = round(response_time, 2)
                    
                    # Check if response is healthy
                    if response.status == 200 and 'result' in response_data:
                        health_status = response_data['result']
                        result['is_healthy'] = health_status == 'ok'
                        if not result['is_healthy']:
                            result['error'] = f"Unhealthy status: {health_status}"
                    else:
                        result['error'] = f"Invalid response: {response.status}"
                        
        except asyncio.TimeoutError:
            result['error'] = 'Request timed out'
        except Exception as e:
            result['error'] = f"Error: {str(e)}"
            
        return result
    
    def _get_current_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()
