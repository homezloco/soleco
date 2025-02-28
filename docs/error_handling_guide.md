# Solana RPC Error Handling Developer Guide

## Introduction

This guide explains how to properly use the enhanced Solana RPC error handling features in the Soleco platform. The system has been improved to handle coroutines more effectively, process complex responses, and provide better serialization of Solana objects.

## Core Components

### 1. Safe RPC Call Function

The `safe_rpc_call_async` function is the primary way to make RPC calls with proper error handling:

```python
from app.utils.solana_helpers import safe_rpc_call_async

async def get_block_data(slot):
    # Pass a coroutine directly
    result = await safe_rpc_call_async(
        client.get_block(slot),
        method_name="get_block",
        timeout=30.0
    )
    
    # Or pass a function that returns a coroutine
    result = await safe_rpc_call_async(
        lambda: client.get_block(slot),
        method_name="get_block",
        timeout=30.0
    )
```

#### Best Practices:

1. **Always provide a descriptive method_name**: This helps with logging and debugging.
2. **Set appropriate timeouts**: Adjust the timeout based on the expected response time of the method.
3. **Handle specific exceptions**: The function can raise several specific exceptions that you should handle:
   ```python
   try:
       result = await safe_rpc_call_async(coro, "method_name")
   except RateLimitError:
       # Handle rate limiting
   except NodeUnhealthyError:
       # Handle unhealthy node
   except RPCError as e:
       # Handle general RPC errors
   except asyncio.TimeoutError:
       # Handle timeout
   ```

### 2. Coroutine Handling

The `_get_data_with_timeout` method in `NetworkStatusHandler` demonstrates best practices for handling coroutines:

```python
async def get_data_with_timeout(self, data_source, name):
    # Check if data_source is a coroutine or callable
    if not asyncio.iscoroutine(data_source):
        if callable(data_source):
            data_source = data_source()
        else:
            # Handle non-coroutine, non-callable input
            return name, data_source
    
    try:
        # Execute with timeout
        result = await asyncio.wait_for(data_source, timeout=self.timeout)
        return name, result
    except asyncio.TimeoutError:
        # Handle timeout
        return name, None
```

#### Best Practices:

1. **Always check if input is a coroutine**: Use `asyncio.iscoroutine()` to check.
2. **Handle callable inputs**: If the input is callable but not a coroutine, call it to get the coroutine.
3. **Use try/except with asyncio.wait_for()**: Always handle TimeoutError explicitly.
4. **Provide fallback mechanisms**: Consider using cached data as a fallback when a coroutine fails.

### 3. Response Processing

The `_process_stake_info` method in `NetworkStatusHandler` demonstrates how to handle complex nested responses:

```python
def process_complex_response(response):
    # Validate input type
    if not isinstance(response, dict):
        return {'error': f"Invalid response type: {type(response)}"}
    
    # Try direct access first
    if 'data' in response:
        return response['data']
    
    # Try recursive search for nested data
    def find_data(obj, key):
        if isinstance(obj, dict):
            if key in obj:
                return obj[key]
            for k, v in obj.items():
                result = find_data(v, key)
                if result:
                    return result
        return None
    
    # Find data at any level of nesting
    data = find_data(response, 'data')
    if data:
        return data
    
    # Return empty result if data not found
    return {}
```

#### Best Practices:

1. **Always validate input types**: Check that the response is of the expected type.
2. **Try direct access first**: Check for the expected structure before attempting complex processing.
3. **Implement recursive search**: Use recursive functions to find data in complex nested structures.
4. **Provide meaningful fallbacks**: Return empty structures or error messages when data is not found.
5. **Log response structures**: Log the structure of unexpected responses to aid debugging.

### 4. Serialization

The `serialize_solana_object` function handles various Solana object types:

```python
from app.utils.solana_helpers import serialize_solana_object

# Serialize a complex object with Pubkey fields
serialized_data = serialize_solana_object(complex_object)

# Use in JSON response
return JSONResponse(content=serialized_data)
```

#### Best Practices:

1. **Always use the serializer for Solana objects**: Don't rely on default JSON serialization.
2. **Handle special Solana types**: Be aware that Pubkey objects and other Solana-specific types need special handling.
3. **Check for coroutines**: Ensure you're not trying to serialize coroutines directly.
4. **Use try/except**: Wrap serialization in try/except blocks to handle unexpected object types.

## Common Patterns

### 1. Comprehensive Status Collection

The `get_comprehensive_status` method in `NetworkStatusHandler` demonstrates how to collect multiple data points with proper error handling:

```python
async def get_comprehensive_status(self):
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
        self._get_data_with_timeout(stakes_coro, 'stakes'),
        return_exceptions=True
    )
    
    # Process results
    status_data = {}
    for name, data in results:
        if isinstance(data, Exception):
            # Handle exception
            status_data[name] = {'error': str(data)}
        else:
            # Process valid data
            status_data[name] = data
    
    return status_data
```

### 2. Graceful Degradation

Always implement graceful degradation when handling RPC responses:

```python
async def get_validator_data(self, pubkey):
    try:
        # Try primary data source
        data = await self.solana_query.get_vote_accounts()
        
        # Process data with fallbacks
        if not data:
            # Try alternative data source
            data = await self.solana_query.get_validators()
            
        if not data:
            # Return minimal data structure
            return {
                'status': 'unknown',
                'stake': 0,
                'commission': 0
            }
            
        # Process data normally
        return self._process_validator_data(data, pubkey)
        
    except Exception as e:
        # Log error and return minimal data
        logger.error(f"Error getting validator data: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'stake': 0,
            'commission': 0
        }
```

## Testing Error Handling

### 1. Testing Coroutine Handling

```python
@pytest.mark.asyncio
async def test_get_data_with_timeout_coroutine():
    # Create a mock coroutine
    async def mock_coro():
        return {"test": "data"}
    
    # Test with coroutine
    handler = NetworkStatusHandler(mock_solana_query)
    name, result = await handler._get_data_with_timeout(mock_coro(), "test")
    
    assert name == "test"
    assert result == {"test": "data"}
    
    # Test with callable that returns coroutine
    name, result = await handler._get_data_with_timeout(mock_coro, "test2")
    
    assert name == "test2"
    assert result == {"test": "data"}
    
    # Test with timeout
    async def slow_coro():
        await asyncio.sleep(2)
        return {"test": "slow"}
    
    handler.timeout = 0.1  # Set short timeout
    name, result = await handler._get_data_with_timeout(slow_coro(), "slow")
    
    assert name == "slow"
    assert result is None  # Should timeout and return None
```

### 2. Testing Serialization

```python
def test_serialize_complex_nested_structure():
    # Create test Pubkey objects
    pubkey1 = Pubkey.from_string("11111111111111111111111111111111")
    pubkey2 = Pubkey.from_string("11111111111111111111111111111112")
    
    # Create a complex structure
    complex_structure = {
        "pubkeys": [pubkey1, pubkey2],
        "objects": [TestClass(), mock_obj],
        "nested": {
            "list": [1, 2, 3],
            "dict": {"key": "value"}
        }
    }
    
    # Serialize it
    result = serialize_solana_object(complex_structure)
    
    # Verify serialization
    assert isinstance(result, dict)
    assert len(result["pubkeys"]) == 2
    assert isinstance(result["pubkeys"][0], str)
    assert "nested" in result
    assert "list" in result["nested"]
```

## Conclusion

The enhanced Solana RPC error handling system provides robust tools for dealing with the complexities of blockchain data. By following these best practices, you can ensure your code gracefully handles errors, properly processes complex responses, and correctly serializes Solana-specific data types.

Remember these key principles:
1. Always use `safe_rpc_call_async` for RPC calls
2. Properly handle coroutines with timeout management
3. Implement recursive search for complex nested structures
4. Use the `serialize_solana_object` function for all Solana objects
5. Implement graceful degradation with appropriate fallbacks
6. Log detailed information about errors and unexpected responses
