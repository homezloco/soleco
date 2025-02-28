"""
Network Status Handler - Handles comprehensive Solana network status analysis
"""
from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime, timezone, timedelta
import asyncio
from ..solana_query import SolanaQueryHandler
from ..solana_response import ResponseHandler

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
            
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """
        Get comprehensive network status including nodes, version, epoch info, and performance.
        
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
            status_data['cluster_nodes'] = {
                'total_nodes': 0,
                'nodes': []
            }
            status_data['network_summary'] = {
                'total_nodes': 0,
                'rpc_nodes_available': 0,
                'rpc_availability_percentage': 0,
                'latest_version': 'unknown',
                'nodes_on_latest_version_percentage': 0,
                'version_distribution': [],
                'total_versions_in_use': 0,
                'total_feature_sets_in_use': 0
            }
            status_data['network_version'] = {
                'solana_core': 'unknown',
                'feature_set': 0
            }
            status_data['epoch_info'] = {
                'epoch': 0,
                'slot_index': 0,
                'slots_in_epoch': 0,
                'absolute_slot': 0,
                'block_height': 0,
                'transaction_count': 0
            }
            status_data['performance_metrics'] = {
                'samples_analyzed': 0,
                'average_slots_per_sample': 0,
                'average_transactions_per_sample': 0,
                'average_non_vote_transactions_per_sample': 0,
                'recent_tps': 0,
                'recent_non_vote_tps': 0,
                'sample_period_secs': 60,
                'slot_time_ms': 400,
                'slots_per_second': 0,
                'block_time_ms': 0
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
                        status_data['cluster_nodes'] = {
                            'total_nodes': len(nodes_info),
                            'nodes': nodes_info
                        }
                        # Add network summary
                        status_data['network_summary'] = self._generate_network_summary(nodes_info)
                    elif name == "version":
                        status_data['network_version'] = data
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
    
    def _generate_network_summary(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of network statistics from node data."""
        try:
            if not nodes:
                return {}
            
            # Version distribution
            version_counts = {}
            feature_set_counts = {}
            rpc_nodes_count = 0
            
            for node in nodes:
                # Count versions
                version = node.get('version')
                if not version or not isinstance(version, str):
                    version = 'unknown'
                
                if version in version_counts:
                    version_counts[version] += 1
                else:
                    version_counts[version] = 1
                
                # Count feature sets
                feature_set = node.get('feature_set', 0)
                if feature_set in feature_set_counts:
                    feature_set_counts[feature_set] += 1
                else:
                    feature_set_counts[feature_set] = 1
                
                # Count RPC nodes
                if node.get('rpc'):
                    rpc_nodes_count += 1
            
            # Sort versions by count (descending)
            sorted_versions = sorted(
                version_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Calculate percentages
            total_nodes = len(nodes)
            version_distribution = []
            
            if total_nodes > 0:
                version_distribution = [
                    {
                        'version': v[0],
                        'count': v[1],
                        'percentage': round((v[1] / total_nodes) * 100, 2)
                    }
                    for v in sorted_versions
                ]
            
            # Get latest version
            valid_versions = [v for v in version_counts.keys() if v != 'unknown' and v is not None and isinstance(v, str)]
            if valid_versions:
                try:
                    latest_version = sorted(
                        valid_versions,
                        key=lambda v: [int(x) for x in v.split('.') if x.isdigit()],
                        reverse=True
                    )[0]
                except Exception as e:
                    logger.warning(f"Error sorting versions: {str(e)}. Using first valid version instead.")
                    latest_version = valid_versions[0]
            else:
                latest_version = 'unknown'
            
            # Calculate nodes on latest version
            latest_version_count = version_counts.get(latest_version, 0)
            latest_version_percentage = round((latest_version_count / total_nodes) * 100, 2) if total_nodes > 0 else 0
            
            return {
                'total_nodes': total_nodes,
                'rpc_nodes_available': rpc_nodes_count,
                'rpc_availability_percentage': round((rpc_nodes_count / total_nodes) * 100, 2) if total_nodes > 0 else 0,
                'latest_version': latest_version,
                'nodes_on_latest_version_percentage': latest_version_percentage,
                'version_distribution': version_distribution[:5] if version_distribution else [],  # Top 5 versions
                'total_versions_in_use': len(version_counts),
                'total_feature_sets_in_use': len(feature_set_counts)
            }
        except Exception as e:
            logger.error(f"Error generating network summary: {str(e)}")
            return {}
    
    def _process_performance_metrics(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process and analyze performance samples."""
        try:
            # Default metrics structure
            metrics = {
                'samples_analyzed': 0,
                'average_slots_per_sample': 0,
                'average_transactions_per_sample': 0,
                'average_non_vote_transactions_per_sample': 0,
                'recent_tps': 0,
                'recent_non_vote_tps': 0,
                'sample_period_secs': 60,  # Default sample period
                'slot_time_ms': 400,  # Default slot time
                'slots_per_second': 0,
                'block_time_ms': 0
            }
            
            # If no samples, return default metrics
            if not samples or not isinstance(samples, list) or len(samples) == 0:
                logger.warning("No performance samples available")
                return metrics
                
            # Calculate averages
            num_samples = len(samples)
            avg_slots = sum(s.get('numSlots', 0) for s in samples) / num_samples if num_samples > 0 else 0
            avg_transactions = sum(s.get('numTransactions', 0) for s in samples) / num_samples if num_samples > 0 else 0
            avg_non_vote_txs = sum(s.get('numNonVoteTransactions', 0) for s in samples) / num_samples if num_samples > 0 else 0
            
            # Get sample period
            sample_period_secs = samples[0].get('samplePeriodSecs', 60) if samples else 60
            
            # Calculate TPS and slots per second
            recent_tps = avg_transactions / sample_period_secs if sample_period_secs > 0 else 0
            recent_non_vote_tps = avg_non_vote_txs / sample_period_secs if sample_period_secs > 0 else 0
            slots_per_second = avg_slots / sample_period_secs if sample_period_secs > 0 else 0
            
            # Calculate block time
            block_time_ms = (1000 / slots_per_second) if slots_per_second > 0 else 0
            
            # Update metrics
            metrics.update({
                'samples_analyzed': num_samples,
                'average_slots_per_sample': round(avg_slots, 2),
                'average_transactions_per_sample': round(avg_transactions, 2),
                'average_non_vote_transactions_per_sample': round(avg_non_vote_txs, 2),
                'recent_tps': round(recent_tps, 2),
                'recent_non_vote_tps': round(recent_non_vote_tps, 2),
                'sample_period_secs': sample_period_secs,
                'slots_per_second': round(slots_per_second, 3),
                'block_time_ms': round(block_time_ms, 2)
            })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error processing performance metrics: {str(e)}")
            logger.exception(e)  # Log full stack trace
            
            # Return default metrics on error
            return {
                'samples_analyzed': 0,
                'average_slots_per_sample': 0,
                'average_transactions_per_sample': 0,
                'recent_tps': 0,
                'sample_period_secs': 60,
                'error': str(e)
            }
    
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
