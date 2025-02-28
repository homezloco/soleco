# Troubleshooting Guide: Solana RPC Error Handling

This guide provides solutions for common issues encountered when working with the enhanced Solana RPC error handling system. Use this guide to diagnose and resolve problems related to RPC calls, coroutine handling, response processing, and serialization.

## Common Error Scenarios

### 1. RPC Connection Errors

#### Symptoms
- `ConnectionRefusedError`
- `ClientConnectorError`
- Timeout errors when attempting to connect to RPC nodes

#### Possible Causes
- RPC endpoint is down or unreachable
- Network connectivity issues
- Rate limiting by the RPC provider

#### Solutions

1. **Check RPC endpoint availability**:
   ```python
   async def check_rpc_availability(endpoint_url):
       try:
           client = AsyncClient(endpoint_url)
           health = await safe_rpc_call_async(
               lambda: client.get_health(),
               method_name="get_health",
               timeout=5.0
           )
           logger.info(f"RPC endpoint {endpoint_url} is available: {health}")
           return True
       except Exception as e:
           logger.error(f"RPC endpoint {endpoint_url} is unavailable: {e}")
           return False
   ```

2. **Implement endpoint fallback**:
   ```python
   async def get_with_fallback(method, *args, **kwargs):
       endpoints = [
           "https://api.mainnet-beta.solana.com",
           "https://solana-api.projectserum.com",
           "https://rpc.ankr.com/solana"
       ]
       
       for endpoint in endpoints:
           try:
               client = AsyncClient(endpoint)
               result = await safe_rpc_call_async(
                   lambda: getattr(client, method)(*args, **kwargs),
                   method_name=method,
                   timeout=10.0
               )
               return result
           except Exception as e:
               logger.warning(f"Error with endpoint {endpoint}: {e}")
               continue
               
       raise RPCError("All RPC endpoints failed")
   ```

3. **Implement exponential backoff**:
   ```python
   async def get_with_backoff(method, *args, max_retries=3, base_delay=1.0, **kwargs):
       client = AsyncClient("https://api.mainnet-beta.solana.com")
       
       for retry in range(max_retries):
           try:
               return await safe_rpc_call_async(
                   lambda: getattr(client, method)(*args, **kwargs),
                   method_name=method,
                   timeout=10.0
               )
           except Exception as e:
               delay = base_delay * (2 ** retry)
               logger.warning(f"Attempt {retry+1} failed: {e}. Retrying in {delay}s")
               await asyncio.sleep(delay)
               
       raise RPCError(f"Failed after {max_retries} retries")
   ```

### 2. Coroutine Handling Issues

#### Symptoms
- `RuntimeWarning: coroutine was never awaited`
- Event loop is closed errors
- Unexpected `None` results from coroutines

#### Possible Causes
- Forgetting to await coroutines
- Improper handling of coroutines in non-async contexts
- Mixing sync and async code incorrectly

#### Solutions

1. **Ensure proper awaiting**:
   ```python
   # ❌ Incorrect
   def get_data():
       return client.get_account_info(address)  # Returns a coroutine
       
   # ✅ Correct
   async def get_data():
       return await client.get_account_info(address)
   ```

2. **Use `asyncio.run()` for top-level coroutines**:
   ```python
   def main():
       result = asyncio.run(get_data())
       print(result)
   ```

3. **Check if an object is a coroutine before awaiting**:
   ```python
   async def safe_execute(obj):
       if asyncio.iscoroutine(obj):
           return await obj
       return obj
   ```

4. **Use the `_get_data_with_timeout` method from `NetworkStatusHandler`**:
   ```python
   async def get_safe_data(coro, name):
       handler = NetworkStatusHandler()
       status, data = await handler._get_data_with_timeout(coro, name)
       return data
   ```

### 3. Response Processing Errors

#### Symptoms
- `KeyError` when accessing response data
- `TypeError` when processing response
- Missing or incomplete data in processed results

#### Possible Causes
- Unexpected response format from RPC
- Missing data in RPC response
- Nested data structure navigation errors

#### Solutions

1. **Use defensive data access with get() method**:
   ```python
   def process_response(response):
       # ❌ Risky direct access
       # validators = response["result"]["validators"]
       
       # ✅ Safe access with fallback
       result = response.get("result", {})
       validators = result.get("validators", [])
       return validators
   ```

2. **Implement recursive data search**:
   ```python
   def find_in_nested_dict(data, key):
       """Recursively search for a key in nested dictionaries."""
       if isinstance(data, dict):
           if key in data:
               return data[key]
           for k, v in data.items():
               result = find_in_nested_dict(v, key)
               if result is not None:
                   return result
       elif isinstance(data, list):
           for item in data:
               result = find_in_nested_dict(item, key)
               if result is not None:
                   return result
       return None
   ```

3. **Validate response structure before processing**:
   ```python
   def validate_response(response, required_keys):
       """Validate that a response contains all required keys."""
       if not isinstance(response, dict):
           return False
           
       result = response.get("result")
       if not isinstance(result, dict):
           return False
           
       for key in required_keys:
           if key not in result:
               return False
               
       return True
   ```

### 4. Serialization Errors

#### Symptoms
- `TypeError: Object of type X is not JSON serializable`
- Circular reference errors
- Missing data in serialized output

#### Possible Causes
- Custom Solana types not properly serialized
- Circular references in data structures
- Coroutines being passed to serialization functions

#### Solutions

1. **Use the enhanced `serialize_solana_object` function**:
   ```python
   from backend.app.utils.solana_helpers import serialize_solana_object
   
   def process_data(data):
       serialized = serialize_solana_object(data)
       return serialized
   ```

2. **Implement custom serialization for complex objects**:
   ```python
   class CustomObject:
       def __init__(self, value):
           self.value = value
           
       def to_json(self):
           return {"value": self.value}
           
   def serialize_with_custom_handler(obj):
       if hasattr(obj, 'to_json'):
           return obj.to_json()
       return serialize_solana_object(obj)
   ```

3. **Handle circular references**:
   ```python
   def serialize_with_circular_check(obj, visited=None):
       if visited is None:
           visited = set()
           
       obj_id = id(obj)
       if obj_id in visited:
           return "<circular reference>"
           
       visited.add(obj_id)
       
       if isinstance(obj, dict):
           return {k: serialize_with_circular_check(v, visited) for k, v in obj.items()}
       elif isinstance(obj, list):
           return [serialize_with_circular_check(item, visited) for item in obj]
       else:
           return serialize_solana_object(obj)
   ```

## Diagnosing Issues

### 1. Enable Detailed Logging

Increase the logging level to get more detailed information about errors:

```python
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Get logger
logger = logging.getLogger('solana_rpc')
```

### 2. Use Execution Time Tracking

Track the execution time of RPC calls to identify performance bottlenecks:

```python
import time

async def track_performance(method, *args, **kwargs):
    start_time = time.time()
    
    try:
        result = await method(*args, **kwargs)
        execution_time = time.time() - start_time
        logger.info(f"{method.__name__} completed in {execution_time:.2f} seconds")
        return result
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"{method.__name__} failed after {execution_time:.2f} seconds: {e}")
        raise
```

### 3. Implement Health Checks

Regularly check the health of RPC endpoints:

```python
async def check_endpoint_health(endpoint_url):
    client = AsyncClient(endpoint_url)
    
    try:
        # Check basic health
        health = await safe_rpc_call_async(
            lambda: client.get_health(),
            method_name="get_health",
            timeout=5.0
        )
        
        # Check response time
        start_time = time.time()
        await safe_rpc_call_async(
            lambda: client.get_slot(),
            method_name="get_slot",
            timeout=5.0
        )
        response_time = time.time() - start_time
        
        return {
            "endpoint": endpoint_url,
            "health": health,
            "response_time": response_time,
            "status": "healthy" if response_time < 1.0 else "degraded"
        }
    except Exception as e:
        return {
            "endpoint": endpoint_url,
            "health": "unhealthy",
            "error": str(e),
            "status": "unhealthy"
        }
```

## Advanced Troubleshooting

### 1. Debugging Coroutine Issues

Use `asyncio.create_task()` with proper exception handling to debug coroutine issues:

```python
async def debug_coroutine(coro):
    task = asyncio.create_task(coro)
    
    try:
        result = await task
        return result
    except Exception as e:
        logger.exception(f"Coroutine failed with error: {e}")
        # Get task exception details
        if task.done() and not task.cancelled():
            exception = task.exception()
            if exception:
                logger.error(f"Task exception details: {exception}")
        return None
```

### 2. Analyzing Response Structures

Create a utility to analyze and log the structure of complex responses:

```python
def analyze_structure(obj, prefix="", max_depth=3, current_depth=0):
    """Analyze and log the structure of a complex object."""
    if current_depth >= max_depth:
        return f"{prefix}... (max depth reached)"
        
    if isinstance(obj, dict):
        logger.debug(f"{prefix}Dict with {len(obj)} keys: {', '.join(obj.keys())}")
        for key, value in obj.items():
            analyze_structure(value, f"{prefix}['{key}'] -> ", max_depth, current_depth + 1)
    elif isinstance(obj, list):
        logger.debug(f"{prefix}List with {len(obj)} items")
        if obj and current_depth < max_depth - 1:
            analyze_structure(obj[0], f"{prefix}[0] -> ", max_depth, current_depth + 1)
    else:
        logger.debug(f"{prefix}Value of type {type(obj).__name__}: {str(obj)[:100]}")
```

### 3. Testing RPC Methods in Isolation

Create a utility to test individual RPC methods in isolation:

```python
async def test_rpc_method(endpoint, method_name, *args, **kwargs):
    """Test a specific RPC method in isolation."""
    client = AsyncClient(endpoint)
    method = getattr(client, method_name)
    
    try:
        logger.info(f"Testing {method_name} on {endpoint}")
        start_time = time.time()
        
        result = await safe_rpc_call_async(
            lambda: method(*args, **kwargs),
            method_name=method_name,
            timeout=30.0
        )
        
        execution_time = time.time() - start_time
        logger.info(f"{method_name} completed in {execution_time:.2f} seconds")
        
        # Analyze result structure
        analyze_structure(result)
        
        return {
            "success": True,
            "execution_time": execution_time,
            "result": serialize_solana_object(result)
        }
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"{method_name} failed after {execution_time:.2f} seconds: {e}")
        
        return {
            "success": False,
            "execution_time": execution_time,
            "error": str(e)
        }
```

## Common Error Codes and Solutions

| Error Code | Description | Solution |
|------------|-------------|----------|
| `-32005` | RPC node is still syncing | Wait or try another endpoint |
| `-32000` | Server error or timeout | Implement retries with backoff |
| `-32602` | Invalid params | Check parameter format and values |
| `-32601` | Method not found | Verify method name and RPC version |
| `-32603` | Internal error | Try another endpoint |
| `429` | Rate limit exceeded | Implement rate limiting and backoff |

## Conclusion

The enhanced Solana RPC error handling system provides robust tools for diagnosing and resolving common issues. By following the troubleshooting steps in this guide, you can effectively handle errors, improve reliability, and ensure a smooth user experience even when dealing with network or data issues.

Remember these key principles:
1. Implement proper error handling for all RPC calls
2. Use the `safe_rpc_call_async` function for all RPC interactions
3. Properly handle and await coroutines
4. Implement fallback mechanisms for critical operations
5. Use detailed logging to diagnose issues
6. Validate and safely process response data
7. Properly serialize Solana objects for storage and transmission

By following these practices, you can build robust applications that gracefully handle the complexities of interacting with the Solana blockchain.
