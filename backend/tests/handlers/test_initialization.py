"""
Tests for the initialization improvements in the Solana RPC error handling.

This test suite covers:
1. Proper initialization of handlers before making RPC calls
2. Explicit initialization in the get_performance_metrics function
3. Error handling during initialization
"""

import unittest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.utils.handlers import initialize_handlers
from backend.app.utils.solana_rpc import SolanaConnectionPool, SolanaClient
from backend.app.utils.solana_query import SolanaQueryHandler


class TestInitialization(unittest.TestCase):
    """Test cases for the initialization improvements."""

    def setUp(self):
        """Set up test fixtures."""
        # Set up logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger('test_initialization')
        self.handler = SolanaQueryHandler(AsyncMock(spec=SolanaConnectionPool))
        self.handler._initialize = AsyncMock(return_value=None)

    @pytest.mark.asyncio
    async def test_solana_query_handler_initialization(self):
        """Test SolanaQueryHandler initialization."""
        # Create a mock connection pool
        mock_connection_pool = AsyncMock(spec=SolanaConnectionPool)
        
        # Create a handler with the mock pool
        handler = SolanaQueryHandler(mock_connection_pool)
        
        # Assert the handler is not initialized yet
        self.assertFalse(handler.initialized)
        
        # Initialize the handler
        await handler.initialize()
        
        # Assert the handler is now initialized
        self.assertTrue(handler.initialized)
        
        # Assert the connection pool was initialized
        mock_connection_pool.initialize.assert_called_once()
        
        # Assert the handlers were initialized
        self.assertIsNotNone(handler.handlers)
        self.assertIn('base', handler.handlers)
        self.assertIn('mint', handler.handlers)
        self.assertIn('pump', handler.handlers)
        self.assertIn('nft', handler.handlers)
        self.assertIn('instruction', handler.handlers)
        self.assertIn('block', handler.handlers)

    @pytest.mark.asyncio
    async def test_ensure_initialized_when_not_initialized(self):
        """Test ensure_initialized when not initialized."""
        # Create a mock connection pool
        mock_connection_pool = AsyncMock(spec=SolanaConnectionPool)
        
        # Create a handler with the mock pool
        handler = SolanaQueryHandler(mock_connection_pool)
        handler.initialized = False
        
        # Call ensure_initialized
        await handler.ensure_initialized()
        
        # Assert the handler is now initialized
        self.assertTrue(handler.initialized)
        
        # Assert the connection pool was initialized
        mock_connection_pool.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_initialized_when_already_initialized(self):
        """Test ensure_initialized when already initialized."""
        # Create a mock connection pool
        mock_connection_pool = AsyncMock(spec=SolanaConnectionPool)
        
        # Create a handler with the mock pool
        handler = SolanaQueryHandler(mock_connection_pool)
        handler.initialized = True
        
        # Call ensure_initialized
        await handler.ensure_initialized()
        
        # Assert the handler is still initialized
        self.assertTrue(handler.initialized)
        
        # Assert the connection pool was not initialized again
        mock_connection_pool.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialization_error_handling(self):
        """Test error handling during initialization."""
        # Create a mock connection pool that raises an exception during initialization
        mock_connection_pool = AsyncMock(spec=SolanaConnectionPool)
        mock_connection_pool.initialize.side_effect = Exception("Test initialization error")
        
        # Create a handler with the mock pool
        handler = SolanaQueryHandler(mock_connection_pool)
        
        # Call initialize and expect an exception
        with self.assertRaises(Exception) as context:
            await handler.initialize()
        
        # Assert the exception message is correct
        self.assertEqual(str(context.exception), "Test initialization error")
        
        # Assert the handler is not initialized
        self.assertFalse(handler.initialized)

    @pytest.mark.asyncio
    async def test_get_performance_metrics_initialization(self):
        """Test explicit initialization in get_performance_metrics."""
        # Create a mock connection pool
        mock_connection_pool = AsyncMock(spec=SolanaConnectionPool)
        
        # Create a mock client
        mock_client = AsyncMock(spec=SolanaClient)
        mock_connection_pool.get_client.return_value = mock_client
        
        # Mock the get_recent_performance_samples method
        mock_client.get_recent_performance_samples.return_value = [
            {"numSlots": 10, "numTransactions": 1000, "samplePeriodSecs": 60}
        ]
        
        # Create a handler with the mock pool
        handler = SolanaQueryHandler(mock_connection_pool)
        handler.initialized = False
        
        # Call get_recent_performance
        result = await handler.get_recent_performance()
        
        # Assert the handler was initialized
        self.assertTrue(handler.initialized)
        
        # Assert the connection pool was initialized
        mock_connection_pool.initialize.assert_called_once()
        
        # Assert the result is correct
        self.assertEqual(result, [{"numSlots": 10, "numTransactions": 1000, "samplePeriodSecs": 60}])

    @pytest.mark.asyncio
    async def test_rpc_call_ensures_initialization(self):
        """Test that RPC calls ensure initialization."""
        # Create a mock connection pool
        mock_connection_pool = AsyncMock(spec=SolanaConnectionPool)
        
        # Create a mock client
        mock_client = AsyncMock(spec=SolanaClient)
        mock_connection_pool.get_client.return_value = mock_client
        
        # Create a handler with the mock pool
        handler = SolanaQueryHandler(mock_connection_pool)
        handler.initialized = False
        
        # Mock the get_vote_accounts method
        mock_client.get_vote_accounts.return_value = {
            "current": [{"votePubkey": "vote1", "activatedStake": 1000000000}],
            "delinquent": []
        }
        
        # Call get_vote_accounts
        result = await handler.get_vote_accounts()
        
        # Assert the handler was initialized
        self.assertTrue(handler.initialized)
        
        # Assert the connection pool was initialized
        mock_connection_pool.initialize.assert_called_once()
        
        # Assert the result is correct
        self.assertEqual(result, {
            "current": [{"votePubkey": "vote1", "activatedStake": 1000000000}],
            "delinquent": []
        })

    @pytest.mark.asyncio
    async def test_ensure_initialized_when_already_initialized(self):
        # Test setup
        self.handler._initialized = True
        
        # Test execution
        await self.handler.ensure_initialized()
        
        # Verify no initialization occurred
        self.assertFalse(self.handler._initialize.called)

    @pytest.mark.asyncio
    async def test_ensure_initialized_when_not_initialized(self):
        # Test setup
        self.handler._initialized = False
        self.handler._initialize.return_value = None
        
        # Test execution
        await self.handler.ensure_initialized()
        
        # Verify initialization occurred
        self.assertTrue(self.handler._initialize.called)

    @pytest.mark.asyncio
    async def test_get_performance_metrics_initialization(self):
        # Test setup
        self.handler._initialized = False
        self.handler._initialize.return_value = None
        
        # Test execution
        await self.handler.get_performance_metrics()
        
        # Verify initialization occurred
        self.assertTrue(self.handler._initialize.called)

    @pytest.mark.asyncio
    async def test_initialization_error_handling(self):
        # Test setup
        self.handler._initialized = False
        self.handler._initialize.side_effect = Exception('Test error')
        
        # Test execution and verification
        with self.assertRaises(Exception):
            await self.handler.ensure_initialized()

    @pytest.mark.asyncio
    async def test_rpc_call_ensures_initialization(self):
        # Test setup
        self.handler._initialized = False
        self.handler._initialize.return_value = None
        
        # Test execution
        await self.handler._safe_rpc_call('test_method')
        
        # Verify initialization occurred
        self.assertTrue(self.handler._initialize.called)

    @pytest.mark.asyncio
    async def test_solana_query_handler_initialization(self):
        # Test setup
        self.handler._initialized = False
        self.handler._initialize.return_value = None
        
        # Test execution
        await self.handler.get_cluster_nodes()
        
        # Verify initialization occurred
        self.assertTrue(self.handler._initialize.called)


if __name__ == "__main__":
    unittest.main()
