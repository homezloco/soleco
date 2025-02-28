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
        
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the Solana network.
        
        Returns:
            Dict containing comprehensive network status information
        """
        # Implementation details...
```

### Key Methods

The system provides several key methods for different aspects of network monitoring:

#### 1. Comprehensive Status

```python
async def get_comprehensive_status(self) -> Dict[str, Any]:
    """
    Get comprehensive status of the Solana network.
    
    Returns:
        Dict containing comprehensive network status information
    """
    # Implementation details...
```

#### 2. Validator Information

```python
async def get_vote_accounts(self) -> Dict[str, Any]:
    """
    Get information about validator vote accounts.
    
    Returns:
        Dict containing vote account information
    """
    # Implementation details...
```

#### 3. Performance Metrics

```python
async def get_performance_metrics(self) -> Dict[str, Any]:
    """
    Get performance metrics for the Solana network.
    
    Returns:
        Dict containing performance metrics
    """
    # Implementation details...
```

#### 4. Block Production

```python
async def get_block_production(self) -> Dict[str, Any]:
    """
    Get block production information.
    
    Returns:
        Dict containing block production information
    """
    # Implementation details...
```

### Data Collection Process

1. **Initialization**: Initialize handlers and connection pool
2. **Parallel Data Collection**: Collect different metrics in parallel using asyncio
3. **Data Processing**: Process and analyze collected data
4. **Result Aggregation**: Combine results into a comprehensive status report
5. **Caching**: Cache results to reduce load on RPC nodes

### Response Format

The system provides a structured response format:

```json
{
  "status": "healthy",
  "cluster_nodes": {
    "total": 1500,
    "rpc_nodes": 250,
    "version_distribution": {
      "1.14.17": 45,
      "1.14.16": 30,
      "1.14.15": 25,
      "other": 150
    }
  },
  "validators": {
    "total": 1200,
    "active": 1150,
    "delinquent": 50,
    "stake_distribution": {
      "top_10_percent": 45.5,
      "top_25_percent": 68.2,
      "top_50_percent": 85.7
    }
  },
  "performance": {
    "current_slot": 123456789,
    "current_block_height": 123456700,
    "transactions_per_second": 2500,
    "average_confirmation_time": 0.5,
    "recent_performance_samples": [
      {"slot": 123456788, "num_transactions": 2500, "num_slots": 1, "sample_period_secs": 1},
      {"slot": 123456787, "num_transactions": 2600, "num_slots": 1, "sample_period_secs": 1}
    ]
  },
  "block_production": {
    "total_blocks_produced": 123456700,
    "total_slots": 123456789,
    "slot_skip_rate": 0.0007,
    "current_leader": "5XKJwdKB2Hs7pkEXzifAyXRSYGCjXaRXPVK47aXnywoD"
  },
  "timestamp": "2023-04-15T12:34:56Z"
}
```

## Usage

### API Endpoint

The Network Status Monitoring system is exposed through the `/api/soleco/solana/network/status` endpoint with the following query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_validators` | boolean | `true` | Include validator information |
| `include_performance` | boolean | `true` | Include performance metrics |
| `include_block_production` | boolean | `true` | Include block production information |
| `include_cluster_nodes` | boolean | `true` | Include cluster node information |

### Example Usage

```python
from app.utils.handlers.network_status_handler import NetworkStatusHandler
from app.utils.solana_query import SolanaQueryHandler
from app.utils.solana_rpc import get_connection_pool

async def get_network_status():
    # Get connection pool
    pool = await get_connection_pool()
    
    # Initialize query handler
    query_handler = SolanaQueryHandler(pool)
    
    # Initialize network status handler
    status_handler = NetworkStatusHandler(query_handler)
    
    # Get comprehensive status
    status = await status_handler.get_comprehensive_status()
    
    return status
```

## Performance Considerations

- **Parallel Data Collection**: Collects different metrics in parallel to reduce response time
- **Caching**: Implements caching to reduce load on RPC nodes
- **Selective Data Collection**: Allows selective inclusion of data components
- **Timeout Management**: Implements timeouts to prevent hanging on slow RPC nodes

## Monitoring Best Practices

1. **Regular Polling**: Poll network status at regular intervals
2. **Trend Analysis**: Track trends over time to identify issues
3. **Alert Configuration**: Configure alerts for critical metrics
4. **Validator Monitoring**: Monitor validator performance and delinquency
5. **Performance Benchmarking**: Benchmark performance against historical data
