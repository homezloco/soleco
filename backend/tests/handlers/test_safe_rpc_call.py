"""
Tests for the safe_rpc_call_async function in the Solana RPC error handling.

This test suite covers:
1. Error handling in RPC calls
2. Execution time tracking
3. Handling of various response types
4. Structured error responses
"""

import pytest
import unittest
from unittest.mock import patch, MagicMock
import asyncio
import logging
import time

from app.utils.solana_query import SolanaQueryHandler
from app.utils import handlers
from app.utils import solana_error


class TestSafeRpcCall(unittest.TestCase):
    """Test cases for the safe_rpc_call_async function."""

    def setUp(self):
        """Set up test fixtures."""
        # Set up logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger('test_safe_rpc_call')

    @pytest.mark.asyncio
    async def test_safe_rpc_call_success(self):
        """Test safe_rpc_call_async with successful response."""
        # Create a mock coroutine that returns a successful response
        async def mock_coro():
            return {"result": "success", "id": 1}

        # Call the function
        result = await handlers.safe_rpc_call_async(mock_coro, "test_method")
        
        # Assert the result is correct
        self.assertEqual(result, "success")

    @pytest.mark.asyncio
    async def test_safe_rpc_call_error_response(self):
        """Test safe_rpc_call_async with error in response."""
        # Create a mock coroutine that returns an error response
        async def mock_coro():
            return {"error": {"code": 123, "message": "Test error"}, "id": 1}

        # Call the function and expect an exception
        with self.assertRaises(solana_error.RPCError) as context:
            await handlers.safe_rpc_call_async(mock_coro, "test_method")
        
        # Assert the exception message contains the error details
        self.assertIn("Test error", str(context.exception))
        self.assertIn("123", str(context.exception))

    @pytest.mark.asyncio
    async def test_safe_rpc_call_rate_limit_error(self):
        """Test safe_rpc_call_async with rate limit error."""
        # Create a mock coroutine that returns a rate limit error
        async def mock_coro():
            return {"error": {"code": -32005, "message": "Rate limit exceeded"}, "id": 1}

        # Call the function and expect a RateLimitError
        with self.assertRaises(solana_error.RateLimitError) as context:
            await handlers.safe_rpc_call_async(mock_coro, "test_method")
        
        # Assert the exception is of the correct type
        self.assertIsInstance(context.exception, solana_error.RateLimitError)

    @pytest.mark.asyncio
    async def test_safe_rpc_call_node_unhealthy_error(self):
        """Test safe_rpc_call_async with node unhealthy error."""
        # Create a mock coroutine that returns a node unhealthy error
        async def mock_coro():
            return {"error": {"code": -32015, "message": "Node is behind"}, "id": 1}

        # Call the function and expect a NodeUnhealthyError
        with self.assertRaises(solana_error.NodeUnhealthyError) as context:
            await handlers.safe_rpc_call_async(mock_coro, "test_method")
        
        # Assert the exception is of the correct type
        self.assertIsInstance(context.exception, solana_error.NodeUnhealthyError)

    @pytest.mark.asyncio
    async def test_safe_rpc_call_exception(self):
        """Test safe_rpc_call_async with exception in coroutine."""
        # Create a mock coroutine that raises an exception
        async def mock_coro():
            raise ValueError("Test exception")

        # Call the function and expect an exception
        with self.assertRaises(ValueError) as context:
            await handlers.safe_rpc_call_async(mock_coro, "test_method")
        
        # Assert the exception message is correct
        self.assertEqual(str(context.exception), "Test exception")

    @pytest.mark.asyncio
    async def test_safe_rpc_call_timeout(self):
        """Test safe_rpc_call_async with timeout."""
        # Create a mock coroutine that takes longer than the timeout
        async def mock_coro():
            await asyncio.sleep(0.5)
            return {"result": "success", "id": 1}

        # Call the function with a short timeout
        with self.assertRaises(asyncio.TimeoutError):
            await handlers.safe_rpc_call_async(mock_coro, "test_method", timeout=0.1)

    @pytest.mark.asyncio
    async def test_safe_rpc_call_execution_time_tracking(self):
        """Test safe_rpc_call_async tracks execution time."""
        # Create a mock coroutine that takes a known amount of time
        async def mock_coro():
            await asyncio.sleep(0.1)
            return {"result": "success", "id": 1}

        # Mock the time.time function to control the timing
        start_time = 1000.0
        with patch('time.time', side_effect=[start_time, start_time + 0.1]):
            # Call the function
            with patch('logging.Logger.debug') as mock_debug:
                await handlers.safe_rpc_call_async(mock_coro, "test_method")
                
                # Assert the execution time was logged
                mock_debug.assert_any_call("test_method completed in 0.10 seconds")

    @pytest.mark.asyncio
    async def test_safe_rpc_call_missing_result(self):
        """Test safe_rpc_call_async with missing result."""
        # Create a mock coroutine that returns a response without result or error
        async def mock_coro():
            return {"id": 1}

        # Call the function and expect an exception
        with self.assertRaises(solana_error.RPCError) as context:
            await handlers.safe_rpc_call_async(mock_coro, "test_method")
        
        # Assert the exception message indicates missing result
        self.assertIn("Missing result", str(context.exception))

    @pytest.mark.asyncio
    async def test_safe_rpc_call_null_result(self):
        """Test safe_rpc_call_async with null result."""
        # Create a mock coroutine that returns a null result
        async def mock_coro():
            return {"result": None, "id": 1}

        # Call the function
        result = await handlers.safe_rpc_call_async(mock_coro, "test_method")
        
        # Assert the result is None
        self.assertIsNone(result)

    @pytest.mark.asyncio
    async def test_safe_rpc_call_invalid_response(self):
        """Test safe_rpc_call_async with invalid response type."""
        # Create a mock coroutine that returns an invalid response
        async def mock_coro():
            return "not a dict"

        # Call the function and expect an exception
        with self.assertRaises(solana_error.RPCError) as context:
            await handlers.safe_rpc_call_async(mock_coro, "test_method")
        
        # Assert the exception message indicates invalid response
        self.assertIn("Invalid response", str(context.exception))


if __name__ == "__main__":
    unittest.main()
