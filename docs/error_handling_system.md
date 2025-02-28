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
- **Type Detection**: Automatically detects if input is a coroutine or callable and handles appropriately
- **Detailed Logging**: Provides comprehensive logging of coroutine execution and response handling
- **Fallback Mechanisms**: Uses cached data as fallback when coroutines timeout or fail

### 3. Response Processing

- **Structured Response Handling**: Processes responses in a structured way to extract relevant data
- **Nested Structure Navigation**: Handles complex nested structures in RPC responses
- **Recursive Search**: Implements recursive search for data in complex response structures
- **Response Validation**: Validates response format and structure before processing
- **Response Type Logging**: Logs response types and structures for debugging
- **Graceful Degradation**: Handles missing or malformed data with appropriate fallbacks

### 4. Rate Limiting and Backoff

- **Automatic Backoff**: Implements exponential backoff for rate-limited requests
- **Header Analysis**: Analyzes response headers to extract rate limit information
- **Adaptive Throttling**: Adjusts request rate based on rate limit information

### 5. Detailed Logging

- **Execution Time Tracking**: Logs execution time for RPC calls to identify slow endpoints
- **Error Context**: Provides detailed context for errors to aid debugging
- **Statistical Logging**: Maintains statistics on error types and frequencies
- **Response Structure Logging**: Logs details about response structure and content
- **Performance Metrics**: Tracks and logs performance metrics for RPC calls

### 6. Enhanced Serialization

- **Type-Specific Handling**: Specialized handling for different Solana object types
- **Pubkey Object Handling**: Proper serialization of Solana Pubkey objects
- **Coroutine Detection**: Identifies and safely handles coroutines during serialization
- **Fallback Mechanisms**: Multiple fallback strategies for complex objects
- **Error Recovery**: Graceful error handling during serialization process

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
    coro_or_func,
    method_name,
    timeout=30.0
) -> Dict[str, Any]:
    """
    Safely execute an RPC call with proper error handling and logging.
    
    Args:
        coro_or_func: A coroutine or function that returns a coroutine
        method_name: Name of the RPC method for logging
        timeout: Timeout in seconds
        
    Returns:
        The result of the RPC call
        
    Raises:
        RPCError: For general RPC errors
        RateLimitError: When rate limit is exceeded
        NodeUnhealthyError: When node is unhealthy
        TimeoutError: When the call times out
    """
    # Implementation details...
```

### Coroutine Handling

The system includes specialized handling for coroutines:

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
            return name, cached_data
            
        # Ensure we're dealing with a coroutine object
        if not asyncio.iscoroutine(coro):
            if callable(coro):
                coro = coro()
            else:
                return name, None
        
        # Await the coroutine with timeout
        result = await asyncio.wait_for(coro, timeout=self.timeout)
        
        # Update cache and return result
        self._update_cache(name, result)
        return name, result
        
    except asyncio.TimeoutError:
        # Try to use expired cache data as fallback
        if name in self.cache:
            return name, self.cache[name]['data']
        return name, None
        
    except Exception as e:
        # Try to use expired cache data as fallback
        if name in self.cache:
            return name, self.cache[name]['data']
        return name, None
```

### Serialization

The `serialize_solana_object` function handles complex Solana objects:

```python
def serialize_solana_object(obj):
    """
    Serialize Solana objects to JSON-compatible formats.
    
    This function handles various Solana object types including:
    - Pubkey objects
    - Coroutines
    - Objects with to_json or to_dict methods
    - Objects with __dict__ attribute
    - Basic Python types
    
    Args:
        obj: The object to serialize
        
    Returns:
        A JSON-serializable representation of the object
    """
    # Implementation details...
```

### Rate Limits

The `RateLimits` class tracks rate limit information:

```python
class RateLimits:
    """Track rate limit information from response headers"""
    
    def __init__(self):
        self.method_limit = 0
        # Additional implementation details...
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
