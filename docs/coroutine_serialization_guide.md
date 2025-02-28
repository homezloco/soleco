# Best Practices for Handling Coroutines and Serialization

This guide outlines best practices for handling coroutines and serialization when working with the Soleco API and Solana RPC integration. Following these practices will help ensure robust, efficient, and maintainable code.

## Coroutine Handling

### 1. Proper Awaiting

Always ensure that coroutines are properly awaited. Failure to await coroutines can lead to unexpected behavior, race conditions, and resource leaks.

```python
# ❌ Incorrect - not awaiting coroutine
def get_data():
    result = client.get_account_info(address)  # Returns a coroutine
    return result

# ✅ Correct - properly awaiting coroutine
async def get_data():
    result = await client.get_account_info(address)
    return result
```

### 2. Timeout Management

Always implement timeouts for RPC calls to prevent hanging operations. Use the `safe_rpc_call_async` function which includes built-in timeout handling.

```python
# ✅ Using safe_rpc_call_async with timeout
async def get_account_data(address):
    try:
        result = await safe_rpc_call_async(
            lambda: client.get_account_info(address),
            method_name="get_account_info",
            timeout=10.0  # 10 second timeout
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"Timeout getting account info for {address}")
        return None
```

### 3. Concurrent Execution

Use `asyncio.gather` for concurrent execution of multiple coroutines, but be careful not to overwhelm the RPC node with too many simultaneous requests.

```python
# ✅ Concurrent execution with gather
async def get_multiple_accounts(addresses):
    tasks = [
        safe_rpc_call_async(
            lambda addr=addr: client.get_account_info(addr),
            method_name=f"get_account_info_{addr}",
            timeout=10.0
        )
        for addr in addresses
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results, handling any exceptions
    processed_results = {}
    for addr, result in zip(addresses, results):
        if isinstance(result, Exception):
            logger.error(f"Error getting account {addr}: {result}")
            processed_results[addr] = None
        else:
            processed_results[addr] = result
            
    return processed_results
```

### 4. Error Handling

Implement comprehensive error handling for coroutines, including specific handling for different error types.

```python
# ✅ Comprehensive error handling
async def get_transaction(signature):
    try:
        result = await safe_rpc_call_async(
            lambda: client.get_transaction(signature),
            method_name="get_transaction",
            timeout=10.0
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"Timeout getting transaction {signature}")
        return {"status": "timeout", "data": None}
    except RPCError as e:
        logger.error(f"RPC error getting transaction {signature}: {e}")
        return {"status": "rpc_error", "error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error getting transaction {signature}")
        return {"status": "error", "error": str(e)}
```

### 5. Execution Tracking

Track execution time for coroutines to identify performance bottlenecks. The `safe_rpc_call_async` function includes built-in execution time tracking.

```python
# ✅ Using safe_rpc_call_async with execution tracking
async def get_performance_metrics():
    start_time = time.time()
    result = await safe_rpc_call_async(
        lambda: client.get_recent_performance_samples(),
        method_name="get_recent_performance_samples",
        timeout=15.0
    )
    execution_time = time.time() - start_time
    
    logger.info(f"Performance metrics retrieved in {execution_time:.2f} seconds")
    return result
```

## Serialization

### 1. Type-Specific Handling

Use the `serialize_solana_object` function for proper serialization of different Solana object types.

```python
# ✅ Using serialize_solana_object for different types
from backend.app.utils.solana_helpers import serialize_solana_object

def process_account_data(account):
    # Handles various types including Pubkey, bytes, etc.
    serialized = serialize_solana_object(account)
    return serialized
```

### 2. Handling Special Types

Pay special attention to Solana-specific types like `Pubkey` objects.

```python
# ✅ Handling Pubkey objects
from solana.publickey import Pubkey

def process_pubkey(pubkey_str):
    try:
        # Convert string to Pubkey object
        pubkey = Pubkey(pubkey_str)
        
        # Serialize for storage or transmission
        serialized = serialize_solana_object(pubkey)
        
        return serialized
    except ValueError:
        logger.error(f"Invalid pubkey: {pubkey_str}")
        return None
```

### 3. Recursive Serialization

For nested structures, ensure that all nested objects are properly serialized.

```python
# ✅ Handling nested structures
def process_transaction_data(transaction):
    # serialize_solana_object handles nested structures recursively
    serialized = serialize_solana_object(transaction)
    return serialized
```

### 4. Error Handling During Serialization

Implement error handling during serialization to catch and handle unexpected object types.

```python
# ✅ Error handling during serialization
def safe_serialize(obj):
    try:
        return serialize_solana_object(obj)
    except Exception as e:
        logger.exception(f"Error serializing object: {e}")
        # Return a basic representation or None
        return str(obj) if obj is not None else None
```

### 5. Custom Serialization Methods

For complex objects, implement custom serialization methods.

```python
# ✅ Custom serialization for complex objects
class TransactionAnalytics:
    def __init__(self, signature, block_time, fee, status):
        self.signature = signature
        self.block_time = block_time
        self.fee = fee
        self.status = status
        
    def to_dict(self):
        """Custom serialization method"""
        return {
            "signature": self.signature,
            "block_time": self.block_time,
            "fee": self.fee,
            "status": self.status
        }
        
# Usage
def process_analytics(analytics_obj):
    if hasattr(analytics_obj, 'to_dict'):
        return analytics_obj.to_dict()
    else:
        return serialize_solana_object(analytics_obj)
```

## Combined Patterns

### 1. Safe RPC Calls with Serialization

Combine safe RPC calls with proper serialization for robust data handling.

```python
# ✅ Combined pattern
async def get_and_process_account(address):
    # Safe RPC call with timeout
    account_info = await safe_rpc_call_async(
        lambda: client.get_account_info(address),
        method_name="get_account_info",
        timeout=10.0
    )
    
    # Proper serialization
    if account_info:
        return serialize_solana_object(account_info)
    else:
        return None
```

### 2. Comprehensive Status Collection

Implement comprehensive status collection with proper error handling and serialization.

```python
# ✅ Comprehensive status collection
async def get_comprehensive_status():
    # Define coroutines to execute
    coroutines = {
        "health": safe_rpc_call_async(
            lambda: client.get_health(),
            method_name="get_health",
            timeout=5.0
        ),
        "vote_accounts": safe_rpc_call_async(
            lambda: client.get_vote_accounts(),
            method_name="get_vote_accounts",
            timeout=10.0
        ),
        "performance": safe_rpc_call_async(
            lambda: client.get_recent_performance_samples(),
            method_name="get_recent_performance_samples",
            timeout=15.0
        )
    }
    
    # Execute coroutines concurrently
    results = {}
    for name, coro in coroutines.items():
        try:
            result = await coro
            results[name] = serialize_solana_object(result)
        except Exception as e:
            logger.error(f"Error getting {name}: {e}")
            results[name] = {"error": str(e)}
    
    return results
```

### 3. Graceful Degradation

Implement graceful degradation when data is incomplete or unavailable.

```python
# ✅ Graceful degradation
async def get_network_status_with_fallback():
    try:
        # Try to get comprehensive status
        status = await get_comprehensive_status()
        return status
    except Exception as e:
        logger.error(f"Error getting comprehensive status: {e}")
        
        # Fall back to minimal status
        try:
            health = await safe_rpc_call_async(
                lambda: client.get_health(),
                method_name="get_health",
                timeout=5.0
            )
            
            return {
                "health": serialize_solana_object(health),
                "limited_data": True,
                "error": str(e)
            }
        except Exception as fallback_error:
            logger.critical(f"Critical error getting minimal status: {fallback_error}")
            return {
                "health": "unknown",
                "limited_data": True,
                "error": str(e),
                "fallback_error": str(fallback_error)
            }
```

## Conclusion

Following these best practices for handling coroutines and serialization will help ensure that your Solana RPC integration is robust, efficient, and maintainable. The enhanced error handling system provides the tools needed to implement these practices effectively.

Remember these key principles:
1. Always properly await coroutines
2. Implement timeouts for all RPC calls
3. Use the `safe_rpc_call_async` function for RPC calls
4. Use the `serialize_solana_object` function for serialization
5. Implement comprehensive error handling
6. Track execution time for performance monitoring
7. Implement graceful degradation for robustness

By following these practices, you'll create a more reliable and maintainable codebase that can handle the complexities of interacting with the Solana blockchain.
