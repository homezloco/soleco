# Solana Network Status Monitoring

## Overview

The Solana Network Status Monitoring system is a comprehensive component of the Soleco platform that provides real-time insights into the health, performance, and status of the Solana blockchain network. It collects, analyzes, and presents critical metrics about the network's operation, validator performance, and transaction processing capabilities.

## Key Features

### 1. Comprehensive Status Reporting

- **Health Metrics**: Overall network health assessment
- **Performance Metrics**: Transaction throughput, block time, and confirmation times
- **Validator Statistics**: Active validators, stake distribution, and delinquency rates
- **Block Production**: Block production rates and slot leadership statistics

### 2. Real-time Monitoring

- **Live Data Collection**: Continuous polling of network metrics
- **Trend Analysis**: Historical trend tracking for key metrics
- **Alerting Thresholds**: Configurable thresholds for metric alerting
- **Status Dashboard**: Visual representation of network status

### 3. Validator Tracking

- **Vote Account Analysis**: Detailed analysis of validator vote accounts
- **Stake Distribution**: Visualization of stake distribution across validators
- **Delinquency Detection**: Identification of delinquent validators
- **Performance Ranking**: Ranking of validators by performance metrics

### 4. Block and Transaction Analytics

- **Block Time Analysis**: Statistics on block production times
- **Transaction Volume**: Tracking of transaction volume over time
- **Fee Analysis**: Analysis of transaction fees and fee market
- **Confirmation Time**: Monitoring of transaction confirmation times

### 5. Enhanced Error Handling

- **Coroutine Management**: Proper handling of asynchronous operations with timeouts
- **Caching System**: Intelligent caching with TTL and fallback mechanisms
- **Recursive Data Processing**: Advanced processing of complex nested data structures
- **Graceful Degradation**: Fallback to cached data when live data is unavailable
- **Comprehensive Logging**: Detailed logging of data collection and processing operations

## Implementation Details

### NetworkStatusHandler Class

The core of the system is the `NetworkStatusHandler` class, which provides methods for collecting and analyzing network status data:

```python
class NetworkStatusHandler:
    """Handler for Solana network status operations"""
    
    def __init__(self, solana_query: SolanaQueryHandler):
        """
        Initialize the network status handler.
        
        Args:
            solana_query: SolanaQueryHandler instance for blockchain queries
        """
        self.solana_query = solana_query
        self.timeout = 10.0  # Timeout for RPC calls
        self.cache = {}  # Cache for network status data
        self.cache_ttl = {  # Time-to-live for cached data
            'nodes': timedelta(minutes=5),
            'stakes': timedelta(minutes=5),
            'performance': timedelta(minutes=1),
            'version': timedelta(hours=1),
            'epoch': timedelta(minutes=1)
        }
```

### Coroutine Handling

The `_get_data_with_timeout` method provides robust handling of coroutines with timeout management and caching:

```python
async def _get_data_with_timeout(self, coro, name: str) -> Tuple[str, Any]:
    """
    Run coroutine with timeout and caching.
    
    Args:
        coro: The coroutine or callable to execute
        name: Name of the operation for logging and caching
        
    Returns:
        A tuple of (name, result)
    """
    try:
        # Check cache first
        cached_data = self._get_cached_data(name)
        if cached_data is not None:
            logger.debug(f"Using cached data for {name}")
            return name, cached_data
            
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
```

### Comprehensive Status Collection

The `get_comprehensive_status` method collects multiple data points concurrently with proper error handling:

```python
async def get_comprehensive_status(self):
    """
    Get comprehensive network status including nodes, stakes, and performance.
    
    Returns:
        Dict containing network status data
    """
    try:
        # Create coroutines for all data sources
        nodes_coro = self.solana_query.get_cluster_nodes()
        version_coro = self.solana_query.get_version()
        epoch_coro = self.solana_query.get_epoch_info()
        performance_coro = self.solana_query.get_recent_performance_samples()
        stakes_coro = self.solana_query.get_vote_accounts()
        
        # Execute all coroutines concurrently with proper timeout handling
        results = await asyncio.gather(
            self._get_data_with_timeout(nodes_coro, 'nodes'),
            self._get_data_with_timeout(version_coro, 'version'),
            self._get_data_with_timeout(epoch_coro, 'epoch'),
            self._get_data_with_timeout(performance_coro, 'performance'),
            self._get_data_with_timeout(stakes_coro, 'stakes')
        )
        
        # Process results
        status_data = {}
        for name, data in results:
            if name == 'nodes':
                status_data['nodes'] = self._process_node_info(data)
            elif name == 'stakes':
                status_data['stakes'] = self._process_stake_info(data)
            elif name == 'performance':
                status_data['performance'] = self._process_performance_info(data)
            elif name == 'version':
                status_data['version'] = data
            elif name == 'epoch':
                status_data['epoch'] = data
        
        # Calculate overall health status
        status_data['health'] = self._calculate_health_status(status_data)
        
        return status_data
    except Exception as e:
        logger.error(f"Error getting comprehensive status: {str(e)}")
        logger.exception(e)
        return {"error": str(e)}
```

### Advanced Response Processing

The `_process_stake_info` method demonstrates advanced processing of complex nested structures:

```python
def _process_stake_info(self, vote_accounts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and analyze validator stake distribution.
    
    Args:
        vote_accounts: Vote accounts data from Solana RPC
        
    Returns:
        Dict containing processed stake information
    """
    try:
        # Add debug logging
        logger.debug(f"Processing vote accounts data type: {type(vote_accounts)}")
        
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
        
        # Process validator data
        # Implementation details...
        
        return processed_data
    except Exception as e:
        logger.error(f"Error processing stake info: {str(e)}")
        logger.exception(e)
        return {
            'total_stake': 0, 
            'active_validators': 0,
            'delinquent_validators': 0,
            'error': str(e)
        }
```

## API Endpoints

The network status monitoring system exposes several API endpoints:

```python
@router.get("/network/status", response_model=NetworkStatusResponse)
async def get_network_status():
    """Get comprehensive network status information"""
    handler = NetworkStatusHandler(solana_query)
    status = await handler.get_comprehensive_status()
    return {
        "status": "success",
        "data": status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

## Response Format

The network status response follows this format:

```json
{
  "status": "healthy",
  "cluster_nodes": {
    "total": 1500,
    "rpc_nodes": 250,
    "validator_nodes": 1250,
    "delinquent_nodes": 15
  },
  "stake_distribution": {
    "total_stake": 500000000,
    "active_stake": 485000000,
    "delinquent_stake": 15000000,
    "top_validators": [
      {
        "pubkey": "ValidatorPubkey1",
        "stake": 50000000,
        "commission": 10
      }
    ]
  },
  "performance": {
    "tps": 2500,
    "avg_confirmation_time": 0.55,
    "block_time": 0.4
  },
  "epoch_info": {
    "epoch": 280,
    "slot": 121445000,
    "slots_in_epoch": 432000,
    "remaining_slots": 310555
  }
}
