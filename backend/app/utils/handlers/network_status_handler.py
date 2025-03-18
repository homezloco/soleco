"""
Network Status Handler - Handles comprehensive Solana network status analysis
"""
from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime, timezone, timedelta
import asyncio
from ..solana_query import SolanaQueryHandler
from ..solana_response import ResponseHandler
import traceback

logger = logging.getLogger(__name__)

class NetworkStatusHandler:
    """Handles network status analysis and monitoring."""
    
    def __init__(self, solana_query: SolanaQueryHandler):
        """
        Initialize the network status handler.
        
        Args:
            solana_query: SolanaQueryHandler instance for blockchain queries
        """
        self.solana_query = solana_query
        self.timeout = 10.0  # Increased timeout for slower endpoints
        self.cache = {}
        self.cache_ttl = {
            'nodes': timedelta(minutes=5),
            'stakes': timedelta(minutes=5),
            'performance': timedelta(minutes=1),
            'version': timedelta(hours=1),
            'epoch': timedelta(minutes=1)
        }
        self.cached_status = None
        self.last_updated = None
        
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self.cache:
            return False
        cached_time = self.cache[key]['timestamp']
        ttl = self.cache_ttl[key]
        return datetime.now(timezone.utc) - cached_time < ttl
        
    def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data if valid."""
        if self._is_cache_valid(key):
            return self.cache[key]['data']
        return None
        
    def _update_cache(self, key: str, data: Any):
        """Update cache with new data."""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now(timezone.utc)
        }
        
    async def _get_data_with_timeout(self, coro, name: str) -> Tuple[str, Any]:
        """Run coroutine with timeout and caching."""
        try:
            # Check cache first
            cached_data = self._get_cached_data(name)
            if cached_data is not None:
                logger.debug(f"Using cached data for {name}")
                return name, cached_data
                
            # If not in cache, fetch with timeout
            try:
                # Ensure we're dealing with a coroutine object
                if not asyncio.iscoroutine(coro):
                    logger.warning(f"{name} is not a coroutine, attempting to call it")
                    if callable(coro):
                        coro = coro()
                    else:
                        logger.error(f"{name} is neither a coroutine nor callable")
                        return name, None
                
                # Now await the coroutine with timeout
                logger.info(f"Fetching {name} data with timeout {self.timeout}s")
                result = await asyncio.wait_for(coro, timeout=self.timeout)
                
                # Log the result type and structure
                if result is not None:
                    logger.debug(f"Received {name} data of type {type(result)}")
                    if isinstance(result, dict):
                        logger.debug(f"Keys in {name} response: {list(result.keys())}")
                    elif isinstance(result, list):
                        logger.debug(f"Received list of {len(result)} items for {name}")
                    
                    # Update cache
                    self._update_cache(name, result)
                else:
                    logger.warning(f"Received None result for {name}")
                
                return name, result
            except asyncio.TimeoutError:
                logger.error(f"Timeout getting {name}")
                # Try to use expired cache data as fallback
                if name in self.cache:
                    logger.warning(f"Using expired cache data for {name}")
                    return name, self.cache[name]['data']
                return name, None
                
        except Exception as e:
            logger.error(f"Error getting {name}: {str(e)}")
            logger.exception(e)  # Log full stack trace
            # Try to use expired cache data as fallback
            if name in self.cache:
                logger.warning(f"Using expired cache data for {name} due to error")
                return name, self.cache[name]['data']
            return name, None
            
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get Solana network performance metrics.
        
        Returns:
            Dict containing performance metrics data
        """
        try:
            # Get performance samples
            performance_coro = self.solana_query.get_recent_performance()
            _, performance_data = await self._get_data_with_timeout(performance_coro, 'performance')
            
            # Process performance data
            metrics = self._process_performance_metrics(performance_data)
            
            # Add timestamp
            metrics['timestamp'] = self._get_current_timestamp()
            
            # Set status based on data availability
            if performance_data is None or not metrics.get('data_available', False):
                metrics['status'] = 'partial'
                metrics['message'] = 'Performance data not available from current endpoints'
                
                # Try to use cached data if available
                if 'performance' in self.cache and self.cache['performance'].get('data'):
                    logger.info("Using cached performance data as fallback")
                    cached_metrics = self._process_performance_metrics(self.cache['performance']['data'])
                    
                    # Only use cached metrics if they have data
                    if cached_metrics.get('data_available', False):
                        metrics = cached_metrics
                        metrics['timestamp'] = self._get_current_timestamp()
                        metrics['status'] = 'cached'
                        metrics['message'] = 'Using cached performance data'
            else:
                metrics['status'] = 'success'
            
            return metrics
            
        except Exception as e:
            error_msg = f"Error retrieving performance metrics: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            
            return {
                'status': 'error',
                'error': error_msg,
                'timestamp': self._get_current_timestamp(),
                'num_blocks': 0,
                'num_slots': 0,
                'num_transactions': 0,
                'sample_period_secs': 60,
                'transactions_per_second': 0,
                'data_available': False
            }
            
    async def get_comprehensive_status(self, summary_only: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive network status including nodes, version, epoch info, and performance.
        
        Args:
            summary_only: If True, only return summary information without detailed node data
            
        Returns:
            Dict containing detailed network status information
        """
        status_data = {
            'status': 'initializing',
            'errors': [],
            'timestamp': self._get_current_timestamp()
        }
        
        try:
            # Create the coroutines - ensure each is properly awaited
            nodes_coro = self.solana_query.get_cluster_nodes()
            version_coro = self.solana_query.get_version()
            epoch_coro = self.solana_query.get_epoch_info()
            performance_coro = self.solana_query.get_recent_performance()
            stakes_coro = self.solana_query.get_vote_accounts()
            
            # Gather all RPC calls concurrently with timeouts
            tasks = [
                self._get_data_with_timeout(nodes_coro, 'nodes'),
                self._get_data_with_timeout(version_coro, 'version'),
                self._get_data_with_timeout(epoch_coro, 'epoch'),
                self._get_data_with_timeout(performance_coro, 'performance'),
                self._get_data_with_timeout(stakes_coro, 'stakes')
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Initialize default values for all sections
            status_data['network_summary'] = {
                'total_nodes': 0,
                'rpc_nodes_available': 0,
                'rpc_availability_percentage': 0,
                'latest_version': 'unknown',
                'current_epoch': 0,
                'epoch_progress': 0,
                'slot_height': 0,
                'average_slot_time_ms': 0,
                'transactions_per_second': 0
            }
            
            # Only include detailed sections if not summary_only
            if not summary_only:
                status_data['cluster_nodes'] = {
                    'total_nodes': 0,
                    'nodes': []
                }
                
                status_data['version_info'] = {
                    'solana_core': 'unknown',
                    'feature_set': 0
                }
                
                status_data['epoch_info'] = {
                    'epoch': 0,
                    'slot_index': 0,
                    'slots_in_epoch': 0,
                    'absolute_slot': 0,
                    'block_height': 0
                }
                
                status_data['performance_metrics'] = {
                    'num_blocks': 0,
                    'num_slots': 0,
                    'num_transactions': 0,
                    'sample_period_secs': 0
                }
                
                status_data['stake_distribution'] = {
                    'total_active_stake': 0,
                    'total_delinquent_stake': 0,
                    'stake_health_percentage': 0,
                    'active_validators': 0,
                    'delinquent_validators': 0
                }
            
            # Process results
            for i, (name, result) in enumerate(zip(['nodes', 'version', 'epoch', 'performance', 'stakes'], results)):
                if isinstance(result, tuple):
                    # Normal result from _get_data_with_timeout
                    _, data = result
                    if data is None:
                        status_data['errors'].append({name: 'Failed to retrieve data'})
                        continue
                elif isinstance(result, Exception):
                    # Handle exception from gather
                    logger.error(f"Error in {name} task: {str(result)}")
                    status_data['errors'].append({name: f'Task error: {str(result)}'})
                    continue
                else:
                    logger.error(f"Unexpected result type for {name}: {type(result)}")
                    status_data['errors'].append({name: f'Unexpected result type'})
                    continue
                    
                try:
                    if name == "nodes":
                        nodes_info = self._process_cluster_nodes(data)
                        if not summary_only:
                            status_data['cluster_nodes'] = {
                                'total_nodes': len(nodes_info),
                                'nodes': nodes_info
                            }
                        # Add network summary
                        status_data['network_summary'] = self._generate_network_summary(nodes_info)
                    elif name == "version":
                        status_data['version_info'] = data
                    elif name == "epoch":
                        status_data['epoch_info'] = data
                    elif name == "performance":
                        status_data['performance_metrics'] = self._process_performance_metrics(data)
                    elif name == "stakes":
                        stake_info = self._process_stake_info(data)
                        if 'cluster_nodes' in status_data:
                            status_data['cluster_nodes']['stake_distribution'] = stake_info
                        else:
                            status_data['stake_distribution'] = stake_info
                except Exception as e:
                    logger.error(f"Error processing {name} data: {str(e)}")
                    status_data['errors'].append({name: f'Failed to process data: {str(e)}'})
            
            # Update final status based on error severity
            error_count = len(status_data['errors'])
            if error_count == 0:
                status_data['status'] = 'healthy'
            elif error_count <= 2:  # Allow some non-critical failures
                status_data['status'] = 'degraded'
            else:
                status_data['status'] = 'error'
            
            return status_data
            
        except Exception as e:
            error_msg = f"Critical error in network status: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)  # Log full stack trace
            return {
                'status': 'error',
                'error': error_msg,
                'timestamp': self._get_current_timestamp()
            }
    
    async def get_network_status(self, summary_only: bool = False) -> Dict[str, Any]:
        """
        Get the current network status.
        
        Args:
            summary_only: If True, return only summary information without detailed node lists
            
        Returns:
            Dict with network status information
        """
        try:
            # Check if we have cached data
            if self.cached_status and (datetime.now() - self.last_updated) < self.cache_ttl['nodes']:
                logging.info("Using cached network status")
                return self._get_summary_if_needed(self.cached_status, summary_only)
                
            # Initialize the status dict
            status = {
                "status": "unknown",
                "message": "",
                "last_updated": datetime.now().isoformat(),
                "metrics": {
                    "total_nodes": 0,
                    "active_nodes": 0,
                    "inactive_nodes": 0,
                    "delinquent_nodes": 0,
                    "version_distribution": {},
                    "feature_set_distribution": {},
                    "stake_distribution": {}
                },
                "errors": []
            }
            
            # Set up a timeout for the entire operation
            try:
                # Use asyncio.wait_for with a more aggressive timeout
                await asyncio.wait_for(
                    self._gather_network_status_data_parallel(status),
                    timeout=8.0  # Reduced timeout for faster response
                )
            except asyncio.TimeoutError:
                logging.warning("Network status data gathering timed out after 8 seconds")
                status["status"] = "degraded"
                status["message"] = "Data gathering timed out"
                status["errors"].append({
                    "type": "timeout",
                    "message": "Network status data gathering timed out after 8 seconds",
                    "timestamp": datetime.now().isoformat()
                })
                
            # Update cache even if we had a timeout
            self.cached_status = status
            self.last_updated = datetime.now()
            
            return self._get_summary_if_needed(status, summary_only)
            
        except Exception as e:
            logging.error(f"Error getting network status: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error getting network status: {str(e)}",
                "last_updated": datetime.now().isoformat(),
                "metrics": {
                    "total_nodes": 0,
                    "active_nodes": 0,
                    "inactive_nodes": 0,
                    "delinquent_nodes": 0,
                    "version_distribution": {},
                    "feature_set_distribution": {},
                    "stake_distribution": {}
                },
                "errors": [{
                    "type": "network_status_error",
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                    "timestamp": datetime.now().isoformat()
                }]
            }
            
    def _get_summary_if_needed(self, status: Dict[str, Any], summary_only: bool) -> Dict[str, Any]:
        """Return a summary version of the status if requested."""
        if summary_only:
            return {
                "status": status["status"],
                "message": status["message"],
                "last_updated": status["last_updated"],
                "metrics": {
                    "total_nodes": status["metrics"]["total_nodes"],
                    "active_nodes": status["metrics"]["active_nodes"],
                    "inactive_nodes": status["metrics"]["inactive_nodes"],
                    "delinquent_nodes": status["metrics"]["delinquent_nodes"],
                    "version_distribution": status["metrics"]["version_distribution"],
                    "feature_set_distribution": status["metrics"]["feature_set_distribution"]
                },
                "errors": status.get("errors", [])
            }
        else:
            return status
            
    async def _gather_network_status_data_parallel(self, status: Dict[str, Any]) -> None:
        """Gather all network status data in parallel for better performance."""
        tasks = []
        
        # Create tasks for each data retrieval operation
        tasks.append(self._gather_cluster_nodes_data(status))
        tasks.append(self._gather_vote_accounts_data(status))
        tasks.append(self._gather_epoch_info_data(status))
        tasks.append(self._gather_performance_data(status))
        
        # Run all tasks concurrently with individual timeouts
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _gather_cluster_nodes_data(self, status: Dict[str, Any]) -> None:
        """Gather cluster nodes data with timeout."""
        try:
            # Set a shorter timeout for this specific operation
            nodes = await asyncio.wait_for(
                self.solana_query.get_cluster_nodes(),
                timeout=5.0  # 5 second timeout for cluster nodes
            )
            
            if not nodes or len(nodes) == 0:
                logging.warning("No cluster nodes returned or empty list, network status may be degraded")
                status["status"] = "degraded"
                status["message"] = "No cluster nodes data available"
                status["errors"].append({
                    "type": "data_retrieval",
                    "message": "Failed to retrieve cluster nodes data - empty list returned",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Set default values for metrics to avoid UI errors
                status["metrics"]["total_nodes"] = 0
                status["metrics"]["active_nodes"] = 0
                status["metrics"]["inactive_nodes"] = 0
                status["metrics"]["delinquent_nodes"] = 0
                status["metrics"]["version_distribution"] = {}
                status["metrics"]["feature_set_distribution"] = {}
                return
                
            logging.info(f"Successfully retrieved {len(nodes)} cluster nodes")
            
            # Count active and delinquent nodes
            active_nodes = 0
            delinquent_nodes = 0
            version_distribution = {}
            feature_set_distribution = {}
            
            for node in nodes:
                # Count versions
                version = node.get("version", "unknown")
                if version in version_distribution:
                    version_distribution[version] += 1
                else:
                    version_distribution[version] = 1
                    
                # Count feature sets
                feature_set = node.get("featureSet", 0)
                feature_set_str = str(feature_set)
                if feature_set_str in feature_set_distribution:
                    feature_set_distribution[feature_set_str] += 1
                else:
                    feature_set_distribution[feature_set_str] = 1
                    
                # Check if node is delinquent
                if node.get("delinquent", False):
                    delinquent_nodes += 1
                else:
                    active_nodes += 1
                    
            # Update metrics
            status["metrics"]["total_nodes"] = len(nodes)
            status["metrics"]["active_nodes"] = active_nodes
            status["metrics"]["inactive_nodes"] = len(nodes) - active_nodes
            status["metrics"]["delinquent_nodes"] = delinquent_nodes
            status["metrics"]["version_distribution"] = version_distribution
            status["metrics"]["feature_set_distribution"] = feature_set_distribution
            
            # Determine overall status
            if active_nodes > 0:
                if delinquent_nodes > len(nodes) * 0.2:  # More than 20% delinquent
                    status["status"] = "degraded"
                    status["message"] = f"Network has {delinquent_nodes} delinquent nodes ({int(delinquent_nodes/len(nodes)*100)}%)"
                else:
                    status["status"] = "operational"
                    status["message"] = f"Network is operational with {active_nodes} active nodes"
            else:
                status["status"] = "down"
                status["message"] = "No active nodes found"
                status["errors"].append({
                    "type": "network_health",
                    "message": "No active nodes detected in the network",
                    "timestamp": datetime.now().isoformat()
                })
                
        except asyncio.TimeoutError:
            logging.warning("Cluster nodes data gathering timed out after 5 seconds")
            status["status"] = "degraded"
            status["message"] = "Cluster nodes data gathering timed out"
            status["errors"].append({
                "type": "timeout",
                "message": "Cluster nodes data gathering timed out after 5 seconds",
                "timestamp": datetime.now().isoformat()
            })
            
            # Set default values for metrics to avoid UI errors
            status["metrics"]["total_nodes"] = 0
            status["metrics"]["active_nodes"] = 0
            status["metrics"]["inactive_nodes"] = 0
            status["metrics"]["delinquent_nodes"] = 0
            status["metrics"]["version_distribution"] = {}
            status["metrics"]["feature_set_distribution"] = {}
            
        except Exception as e:
            logging.error(f"Error gathering cluster nodes data: {str(e)}", exc_info=True)
            status["status"] = "error"
            status["message"] = f"Error gathering cluster nodes data: {str(e)}"
            status["errors"].append({
                "type": "data_retrieval_error",
                "message": f"Error gathering cluster nodes data: {str(e)}",
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            })
            
            # Set default values for metrics to avoid UI errors
            status["metrics"]["total_nodes"] = 0
            status["metrics"]["active_nodes"] = 0
            status["metrics"]["inactive_nodes"] = 0
            status["metrics"]["delinquent_nodes"] = 0
            status["metrics"]["version_distribution"] = {}
            status["metrics"]["feature_set_distribution"] = {}
            
    async def _gather_vote_accounts_data(self, status: Dict[str, Any]) -> None:
        """Gather vote accounts data with timeout."""
        try:
            # Set a shorter timeout for this specific operation
            vote_accounts = await asyncio.wait_for(
                self.solana_query.get_vote_accounts(),
                timeout=4.0  # 4 second timeout for vote accounts
            )
            
            if vote_accounts and "current" in vote_accounts and "delinquent" in vote_accounts:
                # Calculate stake distribution
                stake_distribution = {}
                total_stake = 0
                
                # Process current vote accounts
                for account in vote_accounts["current"]:
                    stake = int(account.get("activatedStake", 0))
                    total_stake += stake
                    
                # Process delinquent vote accounts
                for account in vote_accounts["delinquent"]:
                    stake = int(account.get("activatedStake", 0))
                    total_stake += stake
                    
                # Calculate percentages if total stake is non-zero
                if total_stake > 0:
                    for account in vote_accounts["current"]:
                        stake = int(account.get("activatedStake", 0))
                        node_pubkey = account.get("nodePubkey", "unknown")
                        stake_percentage = (stake / total_stake) * 100
                        stake_distribution[node_pubkey] = {
                            "stake": stake,
                            "percentage": stake_percentage
                        }
                        
                    for account in vote_accounts["delinquent"]:
                        stake = int(account.get("activatedStake", 0))
                        node_pubkey = account.get("nodePubkey", "unknown")
                        stake_percentage = (stake / total_stake) * 100
                        stake_distribution[node_pubkey] = {
                            "stake": stake,
                            "percentage": stake_percentage,
                            "delinquent": True
                        }
                        
                    # Update metrics
                    status["metrics"]["stake_distribution"] = stake_distribution
                    status["metrics"]["total_stake"] = total_stake
                    
            else:
                logging.warning("Invalid vote accounts data format")
                status["errors"].append({
                    "type": "vote_accounts_format",
                    "message": "Invalid vote accounts data format",
                    "timestamp": datetime.now().isoformat()
                })
                
        except asyncio.TimeoutError:
            logging.error("Timeout getting vote accounts data")
            status["errors"].append({
                "type": "timeout",
                "message": "Timeout getting vote accounts data",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"Error getting vote accounts: {str(e)}", exc_info=True)
            status["errors"].append({
                "type": "vote_accounts_error",
                "message": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            })
            
    async def _gather_epoch_info_data(self, status: Dict[str, Any]) -> None:
        """Gather epoch info data with timeout."""
        try:
            # Set a shorter timeout for this specific operation
            epoch_info = await asyncio.wait_for(
                self.solana_query.get_epoch_info(),
                timeout=3.0  # 3 second timeout for epoch info
            )
            
            if epoch_info:
                # Add epoch info to status
                status["epoch_info"] = epoch_info
                
                # Cache the epoch info for summary generation
                self._update_cache("epoch", epoch_info)
                
        except asyncio.TimeoutError:
            logging.error("Timeout getting epoch info data")
            status["errors"].append({
                "type": "timeout",
                "message": "Timeout getting epoch info data",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"Error getting epoch info: {str(e)}", exc_info=True)
            status["errors"].append({
                "type": "epoch_info_error",
                "message": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            })
            
    async def _gather_performance_data(self, status: Dict[str, Any]) -> None:
        """Gather performance data with timeout."""
        try:
            # Set a shorter timeout for this specific operation
            performance = await asyncio.wait_for(
                self.solana_query.get_recent_performance(),
                timeout=3.0  # 3 second timeout for performance data
            )
            
            if performance:
                # Process performance metrics
                metrics = self._process_performance_metrics(performance)
                
                # Add performance metrics to status
                status["performance_metrics"] = metrics
                
                # Cache the performance data for summary generation
                self._update_cache("performance", performance)
                
        except asyncio.TimeoutError:
            logging.error("Timeout getting performance data")
            status["errors"].append({
                "type": "timeout",
                "message": "Timeout getting performance data",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logging.error(f"Error getting performance data: {str(e)}", exc_info=True)
            status["errors"].append({
                "type": "performance_error",
                "message": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            })
    
    def _process_cluster_nodes(self, nodes: List[Dict[str, Any]]) -> list:
        """Process and format cluster node information."""
        try:
            processed_nodes = []
            for node in nodes:
                processed_node = {
                    'pubkey': node.get('pubkey', ''),
                    'gossip': node.get('gossip', ''),
                    'tpu': node.get('tpu', ''),
                    'rpc': node.get('rpc', ''),
                    'version': node.get('version', ''),
                    'feature_set': node.get('featureSet', 0),
                    'shred_version': node.get('shredVersion', 0)
                }
                processed_nodes.append(processed_node)
            return processed_nodes
        except Exception as e:
            logger.error(f"Error processing cluster nodes: {str(e)}")
            return []
    
    def _generate_network_summary(self, nodes_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of the network status."""
        try:
            # Count total nodes
            total_nodes = len(nodes_info)
            
            # Count RPC nodes
            rpc_nodes = sum(1 for node in nodes_info if node.get('rpc') is True)
            
            # Calculate RPC availability percentage
            rpc_availability = (rpc_nodes / total_nodes * 100) if total_nodes > 0 else 0
            
            # Get version distribution
            versions = {}
            for node in nodes_info:
                version = node.get('version', 'unknown')
                if version in versions:
                    versions[version] += 1
                else:
                    versions[version] = 1
                    
            # Find latest version (assuming semantic versioning)
            latest_version = 'unknown'
            if versions:
                try:
                    # Sort versions and get the latest one
                    sorted_versions = sorted(
                        [v for v in versions.keys() if v != 'unknown'],
                        key=lambda v: [int(x) for x in v.split('.') if x.isdigit()],
                        reverse=True
                    )
                    if sorted_versions:
                        latest_version = sorted_versions[0]
                except Exception as e:
                    logger.warning(f"Error sorting versions: {e}")
            
            # Create summary
            summary = {
                'total_nodes': total_nodes,
                'rpc_nodes_available': rpc_nodes,
                'rpc_availability_percentage': round(rpc_availability, 2),
                'latest_version': latest_version,
                'current_epoch': 0,
                'epoch_progress': 0,
                'slot_height': 0,
                'average_slot_time_ms': 0,
                'transactions_per_second': 0
            }
            
            # Add epoch and performance data if available
            if 'epoch' in self.cache and self.cache['epoch'].get('data'):
                epoch_data = self.cache['epoch']['data']
                
                # Handle different response formats
                if isinstance(epoch_data, dict):
                    # Direct response format
                    if 'epoch' in epoch_data:
                        summary.update({
                            'current_epoch': epoch_data.get('epoch', 0),
                            'epoch_progress': round((epoch_data.get('slotIndex', 0) / epoch_data.get('slotsInEpoch', 1)) * 100, 2),
                            'slot_height': epoch_data.get('absoluteSlot', 0)
                        })
                    # Nested response format
                    elif 'result' in epoch_data and isinstance(epoch_data['result'], dict):
                        result = epoch_data['result']
                        summary.update({
                            'current_epoch': result.get('epoch', 0),
                            'epoch_progress': round((result.get('slotIndex', 0) / result.get('slotsInEpoch', 1)) * 100, 2),
                            'slot_height': result.get('absoluteSlot', 0)
                        })
            
            # Add performance data if available
            if 'performance' in self.cache and self.cache['performance'].get('data'):
                perf_data = self.cache['performance']['data']
                
                # Check if we have valid performance data
                if isinstance(perf_data, list) and perf_data:
                    # Calculate average slot time
                    avg_slots = sum(s.get('numSlots', 0) for s in perf_data) / len(perf_data) if perf_data else 0
                    sample_period = perf_data[0].get('samplePeriodSecs', 60) if perf_data else 60
                    slots_per_second = avg_slots / sample_period if sample_period > 0 else 0
                    avg_slot_time_ms = (1000 / slots_per_second) if slots_per_second > 0 else 0
                    
                    # Calculate TPS
                    avg_txs = sum(s.get('numTransactions', 0) for s in perf_data) / len(perf_data) if perf_data else 0
                    tps = avg_txs / sample_period if sample_period > 0 else 0
                    
                    summary.update({
                        'average_slot_time_ms': round(avg_slot_time_ms, 2),
                        'transactions_per_second': round(tps, 2)
                    })
                else:
                    logger.warning("Performance data is not in expected format")
            else:
                logger.warning("No valid performance data available for network summary")
            
            return summary
        except Exception as e:
            logger.error(f"Error generating network summary: {e}")
            return {
                'total_nodes': 0,
                'rpc_nodes_available': 0,
                'rpc_availability_percentage': 0,
                'latest_version': 'unknown',
                'current_epoch': 0,
                'epoch_progress': 0,
                'slot_height': 0,
                'average_slot_time_ms': 0,
                'transactions_per_second': 0
            }
    
    def _process_performance_metrics(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process performance metrics from samples."""
        metrics = {
            "average_slot_time_ms": 0,
            "transactions_per_second": 0,
            "data_available": False
        }
        
        try:
            if not samples or not isinstance(samples, list):
                logger.warning("No performance samples available")
                return metrics
            
            if len(samples) == 0:
                logger.warning("Empty performance samples list")
                return metrics
            
            # Check if the first sample contains an error message
            if len(samples) == 1 and 'error' in samples[0]:
                logger.warning(f"Performance samples contain error: {samples[0]['error']}")
                metrics['error'] = samples[0]['error']
                metrics['endpoints_tried'] = samples[0].get('endpoints_tried', 0)
                metrics['timestamp'] = samples[0].get('timestamp', 0)
                return metrics
            
            # Calculate average slot time
            total_slots = 0
            total_time = 0
            
            for sample in samples:
                if not isinstance(sample, dict):
                    logger.warning(f"Invalid sample type: {type(sample)}")
                    continue
                
                num_slots = sample.get('numSlots', 0)
                sample_period = sample.get('samplePeriodSecs', 60)
                
                if num_slots > 0 and sample_period > 0:
                    total_slots += num_slots
                    total_time += sample_period
            
            if total_time > 0 and total_slots > 0:
                slots_per_second = total_slots / total_time
                avg_slot_time_ms = 1000 / slots_per_second if slots_per_second > 0 else 0
                metrics['average_slot_time_ms'] = round(avg_slot_time_ms, 2)
            
            # Calculate TPS
            total_txs = 0
            for sample in samples:
                if isinstance(sample, dict):
                    total_txs += sample.get('numTransactions', 0)
            
            if total_time > 0:
                tps = total_txs / total_time
                metrics['transactions_per_second'] = round(tps, 2)
            
            metrics['data_available'] = True
            return metrics
        except Exception as e:
            logger.error(f"Error processing performance metrics: {e}")
            return metrics
    
    def _process_stake_info(self, vote_accounts: Dict[str, Any]) -> Dict[str, Any]:
        """Process and analyze validator stake distribution."""
        try:
            # Add debug logging
            logger.debug(f"Processing vote accounts data type: {type(vote_accounts)}")
            logger.debug(f"Vote accounts content: {vote_accounts}")
            
            # Validate input type
            if not isinstance(vote_accounts, dict):
                error_msg = f"Invalid vote_accounts data type: {type(vote_accounts)}"
                logger.error(error_msg)
                return {'error': error_msg, 'total_stake': 0, 'active_validators': 0}
            
            # Extract and validate validator lists
            # Handle both direct response and nested response formats
            current = []
            delinquent = []
            
            if 'current' in vote_accounts:
                current = vote_accounts.get('current', [])
                delinquent = vote_accounts.get('delinquent', [])
            elif 'result' in vote_accounts and isinstance(vote_accounts['result'], dict):
                result = vote_accounts['result']
                current = result.get('current', [])
                delinquent = result.get('delinquent', [])
            else:
                # Try to find current/delinquent at any level of nesting
                def find_validators(obj, key):
                    if isinstance(obj, dict):
                        if key in obj:
                            return obj[key]
                        for k, v in obj.items():
                            result = find_validators(v, key)
                            if result:
                                return result
                    return None
                
                current = find_validators(vote_accounts, 'current') or []
                delinquent = find_validators(vote_accounts, 'delinquent') or []
            
            # If still not found, return empty data
            if not current and not delinquent:
                logger.warning("Missing current/delinquent validators in response, returning empty data")
                return {
                    'total_stake': 0, 
                    'active_validators': 0,
                    'delinquent_validators': 0,
                    'delinquent_stake': 0,
                    'processing_errors': 0,
                    'active_stake_percentage': 0,
                    'delinquent_stake_percentage': 0,
                    'top_validators': []
                }
            
            # Log validator counts for debugging
            logger.debug(f"Found {len(current)} current validators and {len(delinquent)} delinquent validators")
            
            # Combine validator lists
            all_validators = []
            try:
                all_validators.extend(current)
                all_validators.extend(delinquent)
            except Exception as e:
                error_msg = f"Error combining validator lists: {str(e)}"
                logger.error(error_msg)
                return {
                    'total_stake': 0, 
                    'active_validators': 0,
                    'delinquent_validators': 0,
                    'delinquent_stake': 0,
                    'processing_errors': 0,
                    'active_stake_percentage': 0,
                    'delinquent_stake_percentage': 0,
                    'top_validators': []
                }
            
            if not all_validators:
                logger.warning("No validators found in vote accounts data")
                return {
                    'total_stake': 0, 
                    'active_validators': 0,
                    'delinquent_validators': 0,
                    'delinquent_stake': 0,
                    'processing_errors': 0,
                    'active_stake_percentage': 0,
                    'delinquent_stake_percentage': 0,
                    'top_validators': []
                }
            
            # Calculate total stake and active validators with enhanced error handling
            total_stake = 0
            active_validators = 0
            stake_errors = 0
            
            for v in all_validators:
                try:
                    if not isinstance(v, dict):
                        if hasattr(v, '__dict__'):
                            v = v.__dict__
                        else:
                            logger.warning(f"Invalid validator data type: {type(v)}")
                            continue
                    
                    stake_value = v.get('activatedStake')
                    if stake_value is None and hasattr(v, 'activatedStake'):
                        stake_value = getattr(v, 'activatedStake')
                    
                    if stake_value is None:
                        logger.warning("Missing activatedStake field in validator data")
                        continue
                    
                    stake = float(stake_value) / 1e9  # Convert to SOL
                    if stake < 0:
                        logger.warning(f"Negative stake value found: {stake}")
                        continue
                    
                    total_stake += stake
                    if stake > 0:
                        active_validators += 1
                except (ValueError, TypeError, AttributeError) as e:
                    stake_errors += 1
                    logger.error(f"Error processing validator stake: {e}")
                    continue
            
            if stake_errors > 0:
                logger.warning(f"Encountered {stake_errors} errors while processing validator stakes")
            
            # Calculate delinquent stats with validation
            delinquent_stake = 0
            for v in delinquent:
                try:
                    stake_value = None
                    if isinstance(v, dict):
                        stake_value = v.get('activatedStake')
                    elif hasattr(v, 'activatedStake'):
                        stake_value = getattr(v, 'activatedStake')
                    
                    if stake_value is not None:
                        delinquent_stake += float(stake_value) / 1e9
                except (ValueError, TypeError, AttributeError) as e:
                    logger.error(f"Error processing delinquent stake: {e}")
            
            # Calculate stake concentration
            stake_concentration = {}
            if total_stake > 0:
                try:
                    stake_concentration = self._calculate_stake_concentration(all_validators, total_stake)
                except Exception as e:
                    logger.error(f"Error calculating stake concentration: {e}")
            
            result = {
                'total_stake': round(total_stake, 2),
                'active_validators': active_validators,
                'delinquent_validators': len(delinquent),
                'delinquent_stake': round(delinquent_stake, 2),
                'processing_errors': stake_errors,
                **stake_concentration
            }
            
            logger.debug(f"Processed stake info result: {result}")
            return result
            
        except Exception as e:
            error_msg = f"Critical error processing stake info: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)  # Log full stack trace
            return {'error': error_msg, 'total_stake': 0, 'active_validators': 0}
    
    def _calculate_stake_concentration(self, validators: List[Dict[str, Any]], total_stake: float) -> Dict[str, float]:
        """Calculate stake concentration metrics."""
        try:
            if not validators or total_stake == 0:
                return {}
                
            # Sort validators by stake amount
            sorted_validators = sorted(
                validators,
                key=lambda x: float(x.get('activatedStake', 0)),
                reverse=True
            )
            
            # Calculate concentration percentages
            top_10_stake = sum(float(v.get('activatedStake', 0)) / 1e9 for v in sorted_validators[:10])
            top_20_stake = sum(float(v.get('activatedStake', 0)) / 1e9 for v in sorted_validators[:20])
            
            return {
                'top_10_validators': round((top_10_stake / total_stake) * 100, 2),
                'top_20_validators': round((top_20_stake / total_stake) * 100, 2)
            }
        except Exception as e:
            logger.error(f"Error calculating stake concentration: {str(e)}")
            return {}
            
    def _get_current_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()
