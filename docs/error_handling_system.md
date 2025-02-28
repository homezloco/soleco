# Solana RPC Error Handling System

## Overview

The Solana RPC Error Handling System is a critical component of the Soleco platform that ensures robust interaction with the Solana blockchain. It provides comprehensive error detection, classification, recovery mechanisms, and detailed logging to maintain system reliability even when facing network issues or RPC node failures.

## Key Features

### 1. Comprehensive Error Classification

- **Hierarchical Error Types**: Structured hierarchy of error types for precise handling
- **Retryable vs. Non-Retryable Errors**: Clear distinction between errors that can be retried and those that cannot
- **Specialized Error Types**: Custom error types for specific scenarios (e.g., `NodeBehindError`, `RateLimitError`)

### 2. Coroutine Handling

- **Proper Awaiting**: Ensures coroutines are properly awaited to prevent asyncio issues
- **Timeout Management**: Implements timeout handling for coroutines to prevent hanging
- **Execution Tracking**: Tracks coroutine execution time for performance monitoring

### 3. Response Processing

- **Structured Response Handling**: Processes responses in a structured way to extract relevant data
- **Nested Structure Navigation**: Handles complex nested structures in RPC responses
- **Recursive Search**: Implements recursive search for data in complex response structures

### 4. Rate Limiting and Backoff

- **Automatic Backoff**: Implements exponential backoff for rate-limited requests
- **Header Analysis**: Analyzes response headers to extract rate limit information
- **Adaptive Throttling**: Adjusts request rate based on rate limit information

### 5. Detailed Logging

- **Execution Time Tracking**: Logs execution time for RPC calls to identify slow endpoints
- **Error Context**: Provides detailed context for errors to aid debugging
- **Statistical Logging**: Maintains statistics on error types and frequencies

## Implementation Details

### Error Hierarchy

```
RPCError (Base class for RPC errors)
├── RateLimitError (Rate limit exceeded)
├── RetryableError (Base class for errors that can be retried)
│   ├── NodeBehindError (Node is behind)
│   ├── NodeUnhealthyError (Node is unhealthy)
│   ├── MissingBlocksError (Blocks are missing)
│   └── SlotSkippedError (Slot was skipped)
```

### Safe RPC Call Function

The `safe_rpc_call_async` function is the core of the error handling system:

```python
async def safe_rpc_call_async(
    client,
    method: str,
    params: List[Any] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Make an RPC call with robust error handling and retries.
    
    Args:
        client: The RPC client to use
        method: The RPC method to call
        params: Parameters for the RPC method
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries (will be exponentially increased)
        timeout: Timeout for the RPC call
        
    Returns:
        The RPC response
        
    Raises:
        RPCError: If the call fails after all retries
    """
    # Implementation details...
```

### Coroutine Handling

The system includes specialized handling for coroutines:

```python
async def _get_data_with_timeout(data, timeout):
    """
    Get data from a coroutine or return the data directly, with timeout.
    
    Args:
        data: The data or coroutine to get data from
        timeout: Timeout in seconds
        
    Returns:
        The resolved data
    """
    if asyncio.iscoroutine(data):
        try:
            return await asyncio.wait_for(data, timeout=timeout)
        except asyncio.TimeoutError:
            # Handle timeout
            raise TimeoutError(f"Operation timed out after {timeout} seconds")
    return data
```

### Response Processing

The system includes specialized handlers for different response types:

```python
def _process_stake_info(stake_info, validator_pubkey):
    """
    Process stake info to find validator data.
    
    Args:
        stake_info: The stake info to process
        validator_pubkey: The validator public key to search for
        
    Returns:
        The validator data if found, None otherwise
    """
    # Implementation details...
```

### Rate Limiting

The system implements a sophisticated rate limiting mechanism:

```python
class RateLimits:
    """Track rate limit information from response headers"""
    
    def __init__(self):
        self.method_limit = 0
        self.method_remaining = 0
        self.rps_limit = 0
        self.rps_remaining = 0
        self.endpoint_limit = 0
        self.endpoint_remaining = 0
        self.last_update = time.time()
        self.consecutive_failures = 0
        self.cooldown_until = 0
        
    def update_from_headers(self, headers: Dict[str, str]):
        """Update rate limit info from response headers"""
        # Implementation details...
        
    def should_throttle(self):
        """Check if we should throttle requests based on rate limits"""
        # Implementation details...
        
    def get_backoff_time(self):
        """Get the time to back off in seconds"""
        # Implementation details...
```

## Best Practices

### 1. Error Handling

- **Always use try/except**: Wrap RPC calls in try/except blocks
- **Handle specific errors**: Catch specific error types for precise handling
- **Implement retries**: Use retry mechanisms for transient errors
- **Log errors with context**: Include relevant context in error logs

### 2. Rate Limiting

- **Respect rate limits**: Adhere to rate limits from RPC providers
- **Implement backoff**: Use exponential backoff for rate-limited requests
- **Monitor usage**: Track rate limit usage to avoid hitting limits

### 3. Timeout Management

- **Set appropriate timeouts**: Use timeouts that match the expected operation time
- **Handle timeouts gracefully**: Implement proper handling for timeout errors
- **Adjust timeouts dynamically**: Consider adjusting timeouts based on network conditions

### 4. Logging

- **Log at appropriate levels**: Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- **Include context**: Include relevant context in log messages
- **Track performance**: Log execution times to identify performance issues

## Example Usage

```python
from app.utils.solana_rpc import get_connection_pool

async def get_block_safely(slot: int):
    try:
        pool = await get_connection_pool()
        async with pool.acquire() as client:
            result = await client.get_block(slot)
        return result
    except NodeBehindError:
        logger.warning(f"Node is behind when trying to get block {slot}, retrying with different node")
        # Retry with a different node or handle appropriately
    except RateLimitError:
        logger.warning("Rate limit exceeded, implementing backoff")
        # Implement backoff strategy
    except RPCError as e:
        logger.error(f"RPC error when getting block {slot}: {str(e)}")
        # Handle other RPC errors
    except Exception as e:
        logger.exception(f"Unexpected error when getting block {slot}: {str(e)}")
        # Handle unexpected errors
```
