# Solana RPC Connection Pool

## Overview

The Solana RPC Connection Pool is a critical component of the Soleco platform that manages connections to Solana RPC nodes. It provides a robust mechanism for handling RPC requests with automatic fallback, performance tracking, and dynamic endpoint selection.

## Key Features

### 1. Prioritized Endpoint Selection

- **Helius Prioritization**: The Helius endpoint with API key is always prioritized as the default endpoint when available
- **Performance-Based Selection**: Top-performing endpoints are selected based on response times and success rates
- **Fallback Mechanism**: If an endpoint fails, the pool automatically falls back to the next best endpoint

### 2. Dynamic Endpoint Management

- **Failure Tracking**: Endpoints with too many failures are temporarily skipped
- **Performance Metrics**: Detailed tracking of endpoint performance including success/failure counts and latency
- **Automatic Adaptation**: The pool automatically adapts to changing network conditions

### 3. Connection Pooling

- **Resource Efficiency**: Maintains a pool of connections to avoid creating new connections for each request
- **Context Manager Support**: Proper context manager support for client acquisition and release
- **Performance Tracking**: Automatically tracks performance metrics during client usage

### 4. Health Monitoring

- **Endpoint Health Checks**: Regular health checks to ensure endpoints are responsive
- **Performance Statistics**: Detailed statistics about endpoint performance
- **Exponential Moving Average**: Uses exponential moving average for latency calculations to adapt quickly to changing conditions

## Usage

### Basic Usage

```python
from app.utils.solana_rpc import get_connection_pool

async def example_function():
    # Get the connection pool
    pool = await get_connection_pool()
    
    # Use the pool with context manager
    async with pool.acquire() as client:
        # Make RPC calls
        result = await client.get_block(12345)
        
    # The client is automatically released back to the pool
```

### Getting Performance Statistics

```python
async def get_performance_stats():
    pool = await get_connection_pool()
    stats = pool.get_rpc_stats()
    return stats
```

## Configuration

The connection pool can be configured through environment variables or directly in the code:

- `HELIUS_API_KEY`: API key for Helius RPC endpoint
- `POOL_SIZE`: Number of connections to maintain in the pool (default: 5)
- `DEFAULT_TIMEOUT`: Timeout for RPC requests in seconds (default: 30)
- `DEFAULT_MAX_RETRIES`: Maximum number of retries for failed requests (default: 3)
- `DEFAULT_RETRY_DELAY`: Delay between retries in seconds (default: 1)

## Implementation Details

### Endpoint Statistics

The connection pool maintains detailed statistics for each endpoint:

- **Success Count**: Number of successful requests
- **Failure Count**: Number of failed requests
- **Average Latency**: Average response time in seconds
- **Success Rate**: Percentage of successful requests

### Performance Sorting Algorithm

Endpoints are sorted based on a combination of factors:

1. **Success Rate**: Higher success rates are preferred
2. **Average Latency**: Lower latency is preferred
3. **Current Failure Count**: Lower failure counts are preferred

### Exponential Moving Average

The pool uses an exponential moving average for latency calculations:

```
new_avg = alpha * new_latency + (1 - alpha) * old_avg
```

Where `alpha` is a weighting factor (default: 0.2) that gives more weight to recent measurements.

## API Endpoints

The connection pool statistics are exposed through API endpoints:

- `/api/soleco/solana/network/solana/rpc/stats`: Detailed statistics about all RPC endpoints
- `/api/soleco/solana/network/solana/rpc/filtered-stats`: Filtered statistics excluding private endpoints with API keys

## Best Practices

1. **Always use the context manager**: This ensures proper resource management
2. **Handle exceptions properly**: RPC calls can fail, so always handle exceptions
3. **Monitor performance**: Regularly check endpoint statistics to identify issues
4. **Configure appropriate timeouts**: Set timeouts based on your application's needs
