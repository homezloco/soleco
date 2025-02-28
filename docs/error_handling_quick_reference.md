# Solana RPC Error Handling: Quick Reference Guide

This quick reference guide provides a summary of the key components and best practices for using the enhanced Solana RPC error handling system.

## Key Functions

### `safe_rpc_call_async`

```python
async def safe_rpc_call_async(coro_func, method_name=None, timeout=30.0):
    """
    Safely execute an RPC call with timeout and error handling.
    
    Args:
        coro_func: Function that returns a coroutine
        method_name: Name of the method (for logging)
        timeout: Timeout in seconds
        
    Returns:
        Result of the RPC call
        
    Raises:
        RPCError: On RPC-related errors
        asyncio.TimeoutError: On timeout
    """
```

**Usage Example:**
```python
result = await safe_rpc_call_async(
    lambda: client.get_account_info(address),
    method_name="get_account_info",
    timeout=10.0
)
```

### `serialize_solana_object`

```python
def serialize_solana_object(obj):
    """
    Serialize Solana objects for JSON serialization.
    
    Handles:
    - Pubkey objects
    - Coroutines
    - Objects with to_json/to_dict methods
    - Basic Python types
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON-serializable representation
    """
```

**Usage Example:**
```python
serialized_data = serialize_solana_object(account_info)
json_data = json.dumps(serialized_data)
```

### `_get_data_with_timeout`

```python
async def _get_data_with_timeout(self, coro, name: str) -> Tuple[str, Any]:
    """
    Execute a coroutine with timeout handling and caching.
    
    Args:
        coro: Coroutine to execute
        name: Name for the data (for logging and caching)
        
    Returns:
        Tuple of (status, data)
    """
```

**Usage Example:**
```python
handler = NetworkStatusHandler()
status, data = await handler._get_data_with_timeout(
    client.get_vote_accounts(),
    "vote_accounts"
)
```

## Common Error Patterns

### 1. Basic Error Handling

```python
try:
    result = await safe_rpc_call_async(
        lambda: client.get_account_info(address),
        method_name="get_account_info",
        timeout=10.0
    )
    return result
except asyncio.TimeoutError:
    logger.warning(f"Timeout getting account info for {address}")
    return None
except RPCError as e:
    logger.error(f"RPC error: {e}")
    return None
```

### 2. Retry Pattern

```python
async def get_with_retry(method, *args, max_retries=3, **kwargs):
    for retry in range(max_retries):
        try:
            return await safe_rpc_call_async(
                lambda: getattr(client, method)(*args, **kwargs),
                method_name=method,
                timeout=10.0
            )
        except (RPCError, asyncio.TimeoutError) as e:
            if retry == max_retries - 1:
                raise
            logger.warning(f"Attempt {retry+1} failed: {e}. Retrying...")
            await asyncio.sleep(2 ** retry)  # Exponential backoff
```

### 3. Fallback Pattern

```python
async def get_with_fallback(method, *args, **kwargs):
    endpoints = [
        "https://api.mainnet-beta.solana.com",
        "https://solana-api.projectserum.com"
    ]
    
    for endpoint in endpoints:
        try:
            client = AsyncClient(endpoint)
            return await safe_rpc_call_async(
                lambda: getattr(client, method)(*args, **kwargs),
                method_name=method,
                timeout=10.0
            )
        except Exception as e:
            logger.warning(f"Error with endpoint {endpoint}: {e}")
            continue
            
    raise RPCError("All endpoints failed")
```

### 4. Comprehensive Status Collection

```python
async def get_comprehensive_status():
    tasks = {
        "health": safe_rpc_call_async(
            lambda: client.get_health(),
            method_name="get_health",
            timeout=5.0
        ),
        "vote_accounts": safe_rpc_call_async(
            lambda: client.get_vote_accounts(),
            method_name="get_vote_accounts",
            timeout=10.0
        )
    }
    
    results = {}
    for name, task in tasks.items():
        try:
            results[name] = await task
        except Exception as e:
            logger.error(f"Error getting {name}: {e}")
            results[name] = {"error": str(e)}
    
    return results
```

## Response Processing Patterns

### 1. Safe Data Access

```python
def process_vote_accounts(response):
    if not response or not isinstance(response, dict):
        return {"error": "Invalid response"}
        
    result = response.get("result", {})
    current = result.get("current", [])
    delinquent = result.get("delinquent", [])
    
    return {
        "total": len(current) + len(delinquent),
        "active": len(current),
        "delinquent": len(delinquent)
    }
```

### 2. Recursive Data Search

```python
def find_validators_recursive(data):
    """Find validators in a nested structure."""
    if isinstance(data, dict):
        if "validators" in data:
            return data["validators"]
        for key, value in data.items():
            result = find_validators_recursive(value)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_validators_recursive(item)
            if result is not None:
                return result
    return None
```

### 3. Graceful Degradation

```python
def process_network_data(data):
    result = {"limited_data": False}
    
    # Try to get complete data
    try:
        result["health"] = data["health"]
        result["validators"] = process_validators(data.get("vote_accounts", {}))
        result["performance"] = process_performance(data.get("performance", {}))
        return result
    except Exception as e:
        logger.warning(f"Error processing complete data: {e}")
        
    # Fall back to partial data
    result["limited_data"] = True
    
    if "health" in data:
        result["health"] = data["health"]
    else:
        result["health"] = "unknown"
        
    return result
```

## Serialization Patterns

### 1. Basic Serialization

```python
def serialize_for_api(data):
    return serialize_solana_object(data)
```

### 2. Custom Type Handling

```python
def serialize_transaction(transaction):
    if hasattr(transaction, "transaction"):
        # Handle TransactionWithMeta objects
        tx_data = transaction.transaction
        meta = transaction.meta
        
        return {
            "signature": tx_data.signatures[0] if tx_data.signatures else None,
            "successful": meta.status.Ok is not None if meta and meta.status else None,
            "fee": meta.fee if meta else None,
            "instructions": [serialize_instruction(ix) for ix in tx_data.instructions] if tx_data else []
        }
    else:
        # Fall back to standard serialization
        return serialize_solana_object(transaction)
```

### 3. Error-Safe Serialization

```python
def safe_serialize(obj):
    try:
        return serialize_solana_object(obj)
    except Exception as e:
        logger.error(f"Error serializing object: {e}")
        if obj is None:
            return None
        return str(obj)  # Fallback to string representation
```

## Common Error Codes

| Error Code | Description | Handling Strategy |
|------------|-------------|-------------------|
| `-32005` | Node still syncing | Retry or use another endpoint |
| `-32000` | Server error | Retry with backoff |
| `-32602` | Invalid parameters | Check parameter format |
| `-32601` | Method not found | Check method name |
| `-32603` | Internal error | Use another endpoint |
| `429` | Rate limit exceeded | Implement rate limiting |

## Best Practices Checklist

- [ ] Use `safe_rpc_call_async` for all RPC calls
- [ ] Implement timeouts for all RPC operations
- [ ] Properly await all coroutines
- [ ] Use `serialize_solana_object` for all Solana objects
- [ ] Implement fallback mechanisms for critical operations
- [ ] Use defensive data access with `.get()` method
- [ ] Log execution times for performance monitoring
- [ ] Implement graceful degradation for partial data
- [ ] Handle all specific error types (TimeoutError, RPCError, etc.)
- [ ] Validate response data before processing

## Quick Debugging Tips

1. **Enable detailed logging:**
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Track execution time:**
   ```python
   start_time = time.time()
   result = await operation()
   logger.info(f"Operation took {time.time() - start_time:.2f} seconds")
   ```

3. **Check RPC endpoint health:**
   ```python
   health = await safe_rpc_call_async(
       lambda: client.get_health(),
       method_name="get_health",
       timeout=5.0
   )
   ```

4. **Analyze response structure:**
   ```python
   import pprint
   pprint.pprint(response, depth=3)
   ```

5. **Test serialization:**
   ```python
   serialized = serialize_solana_object(obj)
   json_str = json.dumps(serialized)
   print(f"Serialized size: {len(json_str)} bytes")
   ```
