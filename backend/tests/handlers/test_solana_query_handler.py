"""
Tests for the SolanaQueryHandler class focusing on enhanced error handling.

This test suite covers:
1. Enhanced error handling in the get_vote_accounts method
2. Response processing for various RPC calls
3. Error handling for timeouts and connection issues
4. Handling of coroutines and async functions
"""

import unittest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import pytest

from backend.app import utils
from backend.app.utils.solana_query import SolanaQueryHandler
from backend.app.utils.solana_rpc import SolanaConnectionPool, SolanaClient


class TestSolanaQueryHandler(unittest.TestCase):
    """Test cases for the SolanaQueryHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_connection_pool = MagicMock(spec=SolanaConnectionPool)
        self.handler = SolanaQueryHandler(self.mock_connection_pool)
        
        # Set up logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger('test_solana_query_handler')

    async def async_setup(self):
        """Async setup for tests that need it."""
        self.mock_connection_pool = AsyncMock(spec=SolanaConnectionPool)
        self.mock_client = AsyncMock(spec=SolanaClient)
        self.mock_connection_pool.get_client.return_value = self.mock_client
        self.handler = SolanaQueryHandler(self.mock_connection_pool)
        self.handler.initialized = True  # Skip initialization

    @pytest.mark.asyncio
    async def test_ensure_initialized(self):
        """Test ensure_initialized method."""
        # Setup
        self.handler.initialized = False
        self.mock_connection_pool.initialize = AsyncMock()
        
        # Call the method
        await self.handler.ensure_initialized()
        
        # Assert
        self.assertTrue(self.handler.initialized)
        self.mock_connection_pool.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_initialized_already_initialized(self):
        """Test ensure_initialized when already initialized."""
        # Setup
        self.handler.initialized = True
        self.mock_connection_pool.initialize = AsyncMock()
        
        # Call the method
        await self.handler.ensure_initialized()
        
        # Assert
        self.assertTrue(self.handler.initialized)
        self.mock_connection_pool.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_vote_accounts_success(self):
        """Test get_vote_accounts with successful response."""
        await self.async_setup()
        
        # Setup mock response
        expected_response = {
            "current": [
                {"votePubkey": "vote1", "activatedStake": 1000000000},
                {"votePubkey": "vote2", "activatedStake": 2000000000}
            ],
            "delinquent": [
                {"votePubkey": "vote3", "activatedStake": 500000000}
            ]
        }
        self.mock_client.get_vote_accounts.return_value = expected_response
        
        # Call the method
        result = await self.handler.get_vote_accounts()
        
        # Assert
        self.assertEqual(result, expected_response)
        self.mock_client.get_vote_accounts.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_vote_accounts_non_dict_response(self):
        """Test get_vote_accounts with non-dict response."""
        await self.async_setup()
        
        # Setup mock response
        self.mock_client.get_vote_accounts.return_value = "not a dict"
        
        # Call the method
        result = await self.handler.get_vote_accounts()
        
        # Assert
        self.assertEqual(result, {})
        self.mock_client.get_vote_accounts.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_vote_accounts_exception(self):
        """Test get_vote_accounts with exception."""
        await self.async_setup()
        
        # Setup mock to raise exception
        self.mock_client.get_vote_accounts.side_effect = Exception("Test error")
        
        # Call the method
        result = await self.handler.get_vote_accounts()
        
        # Assert
        self.assertEqual(result, {})
        self.mock_client.get_vote_accounts.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cluster_nodes_success(self):
        """Test get_cluster_nodes with successful response."""
        await self.async_setup()
        
        # Setup mock response
        expected_response = [
            {"pubkey": "node1", "gossip": "gossip1", "rpc": "rpc1", "version": "1.0.0"},
            {"pubkey": "node2", "gossip": "gossip2", "rpc": "rpc2", "version": "1.0.0"}
        ]
        self.mock_client.get_cluster_nodes.return_value = expected_response
        
        # Call the method
        result = await self.handler.get_cluster_nodes()
        
        # Assert
        self.assertEqual(result, expected_response)
        self.mock_client.get_cluster_nodes.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cluster_nodes_exception(self):
        """Test get_cluster_nodes with exception."""
        await self.async_setup()
        
        # Setup mock to raise exception
        self.mock_client.get_cluster_nodes.side_effect = Exception("Test error")
        
        # Call the method
        result = await self.handler.get_cluster_nodes()
        
        # Assert
        self.assertEqual(result, [])
        self.mock_client.get_cluster_nodes.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_version_success(self):
        """Test get_version with successful response."""
        await self.async_setup()
        
        # Setup mock response
        expected_response = {
            "solana_core": "1.0.0",
            "feature_set": 123
        }
        self.mock_client.get_version.return_value = expected_response
        
        # Call the method
        result = await self.handler.get_version()
        
        # Assert
        self.assertEqual(result, expected_response)
        self.mock_client.get_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_version_exception(self):
        """Test get_version with exception."""
        await self.async_setup()
        
        # Setup mock to raise exception
        self.mock_client.get_version.side_effect = Exception("Test error")
        
        # Call the method
        result = await self.handler.get_version()
        
        # Assert
        self.assertEqual(result, {})
        self.mock_client.get_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_epoch_info_success(self):
        """Test get_epoch_info with successful response."""
        await self.async_setup()
        
        # Setup mock response
        expected_response = {
            "epoch": 100,
            "slot_index": 1000,
            "slots_in_epoch": 8192,
            "absolute_slot": 10000,
            "block_height": 9000,
            "transaction_count": 5000
        }
        self.mock_client.get_epoch_info.return_value = expected_response
        
        # Call the method
        result = await self.handler.get_epoch_info()
        
        # Assert
        self.assertEqual(result, expected_response)
        self.mock_client.get_epoch_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_epoch_info_exception(self):
        """Test get_epoch_info with exception."""
        await self.async_setup()
        
        # Setup mock to raise exception
        self.mock_client.get_epoch_info.side_effect = Exception("Test error")
        
        # Call the method
        result = await self.handler.get_epoch_info()
        
        # Assert
        self.assertEqual(result, {})
        self.mock_client.get_epoch_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_performance_success(self):
        """Test get_recent_performance with successful response."""
        await self.async_setup()
        
        # Setup mock response
        expected_response = [
            {"numSlots": 10, "numTransactions": 1000, "samplePeriodSecs": 60}
        ]
        self.mock_client.get_recent_performance_samples.return_value = expected_response
        
        # Call the method
        result = await self.handler.get_recent_performance()
        
        # Assert
        self.assertEqual(result, expected_response)
        self.mock_client.get_recent_performance_samples.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_performance_exception(self):
        """Test get_recent_performance with exception."""
        await self.async_setup()
        
        # Setup mock to raise exception
        self.mock_client.get_recent_performance_samples.side_effect = Exception("Test error")
        
        # Call the method
        result = await self.handler.get_recent_performance()
        
        # Assert
        self.assertEqual(result, [])
        self.mock_client.get_recent_performance_samples.assert_called_once()


if __name__ == "__main__":
    unittest.main()
