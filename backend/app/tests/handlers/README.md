# Solana RPC Error Handling Tests

This directory contains comprehensive test coverage for the enhanced Solana RPC error handling implementation.

## Test Files

### 1. `test_network_status_handler.py`

Tests for the `NetworkStatusHandler` class focusing on:
- Coroutine handling in `_get_data_with_timeout`
- Response processing in `get_comprehensive_status`
- Error handling in various methods
- Handling of complex nested structures in `_process_stake_info`

### 2. `test_solana_query_handler.py`

Tests for the `SolanaQueryHandler` class focusing on:
- Enhanced error handling in the `get_vote_accounts` method
- Response processing for various RPC calls
- Error handling for timeouts and connection issues
- Handling of coroutines and async functions

### 3. `test_serialization.py`

Tests for the serialization functionality focusing on:
- Serialization of various Solana object types
- Handling of Pubkey objects
- Handling of coroutines during serialization
- Error handling during serialization

### 4. `test_safe_rpc_call.py`

Tests for the `safe_rpc_call_async` function focusing on:
- Error handling in RPC calls
- Execution time tracking
- Handling of various response types
- Structured error responses

### 5. `test_initialization.py`

Tests for the initialization improvements focusing on:
- Proper initialization of handlers before making RPC calls
- Explicit initialization in the `get_performance_metrics` function
- Error handling during initialization

## Running the Tests

To run all the tests, use the `run_handler_tests.py` script in the parent directory:

```bash
python -m app.tests.run_handler_tests
```

Or run individual test files with pytest:

```bash
pytest -xvs app/tests/handlers/test_network_status_handler.py
```

## Test Coverage

These tests provide comprehensive coverage for the enhanced Solana RPC error handling, including:

1. **Coroutine Handling**:
   - Tests for properly awaiting coroutines
   - Tests for handling non-coroutine inputs
   - Tests for timeout handling in coroutines

2. **Response Processing**:
   - Tests for handling various response structures
   - Tests for processing nested response objects
   - Tests for handling malformed or unexpected responses

3. **Error Handling**:
   - Tests for various error scenarios
   - Tests for graceful degradation
   - Tests for proper error propagation

4. **Serialization**:
   - Tests for serializing different object types
   - Tests for handling special objects like Pubkey
   - Tests for error handling during serialization

5. **Initialization**:
   - Tests for proper initialization sequence
   - Tests for handling initialization errors
   - Tests for ensuring initialization before RPC calls

## Edge Cases Covered

- Timeout errors in RPC calls
- Malformed response structures
- Deeply nested response objects
- Missing or invalid data in responses
- Rate limiting and node health errors
- Serialization of complex object structures
- Initialization failures and recovery
