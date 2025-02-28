"""
Tests for the NetworkStatusHandler class focusing on enhanced error handling.

This test suite covers:
1. Coroutine handling in _get_data_with_timeout
2. Response processing in get_comprehensive_status
3. Error handling in various methods
4. Handling of complex nested structures in _process_stake_info
"""

import unittest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import pytest

from app.utils.handlers.network_status_handler import NetworkStatusHandler
from app.utils.solana_query import SolanaQueryHandler


class TestNetworkStatusHandler(unittest.TestCase):
    """Test cases for the NetworkStatusHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_solana_query = MagicMock(spec=SolanaQueryHandler)
        self.handler = NetworkStatusHandler(self.mock_solana_query)
        
        # Set up logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger('test_network_status_handler')

    async def async_setup(self):
        """Async setup for tests that need it."""
        self.mock_solana_query = AsyncMock(spec=SolanaQueryHandler)
        self.handler = NetworkStatusHandler(self.mock_solana_query)

    @pytest.mark.asyncio
    async def test_get_data_with_timeout_coroutine(self):
        """Test _get_data_with_timeout with a coroutine."""
        await self.async_setup()
        # Create a coroutine that returns a value
        async def mock_coro():
            return {"test": "data"}

        # Call the method with the coroutine
        name, result = await self.handler._get_data_with_timeout(mock_coro(), "test_coro")
        
        # Assert the result is correct
        self.assertEqual(name, "test_coro")
        self.assertEqual(result, {"test": "data"})
        self.assertIn("test_coro", self.handler.cache)

    @pytest.mark.asyncio
    async def test_get_data_with_timeout_callable(self):
        """Test _get_data_with_timeout with a callable that returns a coroutine."""
        await self.async_setup()
        # Create a callable that returns a coroutine
        async def mock_coro_result():
            return {"test": "callable_data"}
            
        def mock_callable():
            return mock_coro_result()

        # Call the method with the callable
        name, result = await self.handler._get_data_with_timeout(mock_callable, "test_callable")
        
        # Assert the result is correct
        self.assertEqual(name, "test_callable")
        self.assertEqual(result, {"test": "callable_data"})
        self.assertIn("test_callable", self.handler.cache)

    @pytest.mark.asyncio
    async def test_get_data_with_timeout_not_coroutine_or_callable(self):
        """Test _get_data_with_timeout with something that's neither a coroutine nor callable."""
        await self.async_setup()
        # Call the method with a string
        name, result = await self.handler._get_data_with_timeout("not a coroutine", "test_invalid")
        
        # Assert the result is None due to error
        self.assertEqual(name, "test_invalid")
        self.assertIsNone(result)

    @pytest.mark.asyncio
    async def test_get_data_with_timeout_timeout_error(self):
        """Test _get_data_with_timeout with a timeout error."""
        await self.async_setup()
        # Create a coroutine that takes longer than the timeout
        async def slow_coro():
            await asyncio.sleep(2)
            return {"test": "slow_data"}

        # Set a short timeout
        self.handler.timeout = 0.1
        
        # Call the method with the slow coroutine
        name, result = await self.handler._get_data_with_timeout(slow_coro(), "test_timeout")
        
        # Assert the result is None due to timeout
        self.assertEqual(name, "test_timeout")
        self.assertIsNone(result)

    @pytest.mark.asyncio
    async def test_get_data_with_timeout_exception(self):
        """Test _get_data_with_timeout with an exception in the coroutine."""
        await self.async_setup()
        # Create a coroutine that raises an exception
        async def error_coro():
            raise ValueError("Test error")

        # Call the method with the error coroutine
        name, result = await self.handler._get_data_with_timeout(error_coro(), "test_error")
        
        # Assert the result is None due to error
        self.assertEqual(name, "test_error")
        self.assertIsNone(result)

    @pytest.mark.asyncio
    async def test_get_data_with_timeout_cache_hit(self):
        """Test _get_data_with_timeout with cached data."""
        await self.async_setup()
        # Set up cache
        cache_data = {"cached": "data"}
        self.handler.cache = {
            "test_cache": {
                "data": cache_data,
                "timestamp": datetime.now(timezone.utc)
            }
        }
        
        # Call the method with a name that's in the cache
        name, result = await self.handler._get_data_with_timeout(AsyncMock(), "test_cache")
        
        # Assert the cached data is returned
        self.assertEqual(name, "test_cache")
        self.assertEqual(result, cache_data)

    @pytest.mark.asyncio
    async def test_get_comprehensive_status_success(self):
        """Test get_comprehensive_status with successful responses."""
        await self.async_setup()
        
        # Mock the query handler methods to return test data
        self.mock_solana_query.get_cluster_nodes.return_value = [
            {"pubkey": "node1", "gossip": "gossip1", "rpc": "rpc1", "version": "1.0.0", "featureSet": 123},
            {"pubkey": "node2", "gossip": "gossip2", "rpc": "rpc2", "version": "1.0.0", "featureSet": 123}
        ]
        
        self.mock_solana_query.get_version.return_value = {
            "solana_core": "1.0.0",
            "feature_set": 123
        }
        
        self.mock_solana_query.get_epoch_info.return_value = {
            "epoch": 100,
            "slot_index": 1000,
            "slots_in_epoch": 8192,
            "absolute_slot": 10000,
            "block_height": 9000,
            "transaction_count": 5000
        }
        
        self.mock_solana_query.get_recent_performance.return_value = [
            {"numSlots": 10, "numTransactions": 1000, "samplePeriodSecs": 60}
        ]
        
        self.mock_solana_query.get_vote_accounts.return_value = {
            "current": [
                {"votePubkey": "vote1", "activatedStake": 1000000000},
                {"votePubkey": "vote2", "activatedStake": 2000000000}
            ],
            "delinquent": []
        }
        
        # Call the method
        result = await self.handler.get_comprehensive_status()
        
        # Assert the result is correct
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(len(result["errors"]), 0)
        self.assertEqual(result["cluster_nodes"]["total_nodes"], 2)
        self.assertEqual(result["network_version"]["solana_core"], "1.0.0")
        self.assertEqual(result["epoch_info"]["epoch"], 100)
        self.assertEqual(result["performance_metrics"]["samples_analyzed"], 1)
        self.assertEqual(result["cluster_nodes"]["stake_distribution"]["total_stake"], 3.0)

    @pytest.mark.asyncio
    async def test_get_comprehensive_status_partial_failure(self):
        """Test get_comprehensive_status with some failed responses."""
        await self.async_setup()
        
        # Mock some methods to return data and others to fail
        self.mock_solana_query.get_cluster_nodes.return_value = [
            {"pubkey": "node1", "gossip": "gossip1", "rpc": "rpc1", "version": "1.0.0", "featureSet": 123}
        ]
        
        self.mock_solana_query.get_version.return_value = {
            "solana_core": "1.0.0",
            "feature_set": 123
        }
        
        # Make epoch_info fail
        self.mock_solana_query.get_epoch_info.side_effect = Exception("Test error")
        
        self.mock_solana_query.get_recent_performance.return_value = [
            {"numSlots": 10, "numTransactions": 1000, "samplePeriodSecs": 60}
        ]
        
        self.mock_solana_query.get_vote_accounts.return_value = {
            "current": [
                {"votePubkey": "vote1", "activatedStake": 1000000000}
            ],
            "delinquent": []
        }
        
        # Call the method
        result = await self.handler.get_comprehensive_status()
        
        # Assert the result shows degraded status
        self.assertEqual(result["status"], "degraded")
        self.assertGreater(len(result["errors"]), 0)
        self.assertEqual(result["cluster_nodes"]["total_nodes"], 1)
        self.assertEqual(result["network_version"]["solana_core"], "1.0.0")
        # Default values for failed epoch_info
        self.assertEqual(result["epoch_info"]["epoch"], 0)

    @pytest.mark.asyncio
    async def test_get_comprehensive_status_complete_failure(self):
        """Test get_comprehensive_status with all failed responses."""
        await self.async_setup()
        
        # Make all methods fail
        self.mock_solana_query.get_cluster_nodes.side_effect = Exception("Test error")
        self.mock_solana_query.get_version.side_effect = Exception("Test error")
        self.mock_solana_query.get_epoch_info.side_effect = Exception("Test error")
        self.mock_solana_query.get_recent_performance.side_effect = Exception("Test error")
        self.mock_solana_query.get_vote_accounts.side_effect = Exception("Test error")
        
        # Call the method
        result = await self.handler.get_comprehensive_status()
        
        # Assert the result shows error status
        self.assertEqual(result["status"], "error")
        self.assertGreater(len(result["errors"]), 0)

    @pytest.mark.asyncio
    async def test_process_stake_info_normal_structure(self):
        """Test _process_stake_info with normal response structure."""
        await self.async_setup()
        # Create test data
        vote_accounts = {
            "current": [
                {"votePubkey": "vote1", "activatedStake": 1000000000},
                {"votePubkey": "vote2", "activatedStake": 2000000000}
            ],
            "delinquent": [
                {"votePubkey": "vote3", "activatedStake": 500000000}
            ]
        }
        
        # Call the method
        result = self.handler._process_stake_info(vote_accounts)
        
        # Assert the result is correct
        self.assertEqual(result["total_stake"], 3.5)
        self.assertEqual(result["active_validators"], 3)
        self.assertEqual(result["delinquent_validators"], 1)
        self.assertEqual(result["delinquent_stake"], 0.5)

    @pytest.mark.asyncio
    async def test_process_stake_info_nested_structure(self):
        """Test _process_stake_info with nested response structure."""
        await self.async_setup()
        # Create test data with nested structure
        vote_accounts = {
            "result": {
                "current": [
                    {"votePubkey": "vote1", "activatedStake": 1000000000},
                    {"votePubkey": "vote2", "activatedStake": 2000000000}
                ],
                "delinquent": [
                    {"votePubkey": "vote3", "activatedStake": 500000000}
                ]
            }
        }
        
        # Call the method
        result = self.handler._process_stake_info(vote_accounts)
        
        # Assert the result is correct
        self.assertEqual(result["total_stake"], 3.5)
        self.assertEqual(result["active_validators"], 3)
        self.assertEqual(result["delinquent_validators"], 1)
        self.assertEqual(result["delinquent_stake"], 0.5)

    @pytest.mark.asyncio
    async def test_process_stake_info_deeply_nested_structure(self):
        """Test _process_stake_info with deeply nested response structure."""
        await self.async_setup()
        # Create test data with deeply nested structure
        vote_accounts = {
            "data": {
                "response": {
                    "result": {
                        "current": [
                            {"votePubkey": "vote1", "activatedStake": 1000000000},
                            {"votePubkey": "vote2", "activatedStake": 2000000000}
                        ],
                        "delinquent": [
                            {"votePubkey": "vote3", "activatedStake": 500000000}
                        ]
                    }
                }
            }
        }
        
        # Call the method
        result = self.handler._process_stake_info(vote_accounts)
        
        # Assert the result is correct
        self.assertEqual(result["total_stake"], 3.5)
        self.assertEqual(result["active_validators"], 3)
        self.assertEqual(result["delinquent_validators"], 1)
        self.assertEqual(result["delinquent_stake"], 0.5)

    @pytest.mark.asyncio
    async def test_process_stake_info_invalid_data(self):
        """Test _process_stake_info with invalid data."""
        await self.async_setup()
        # Test with various invalid inputs
        invalid_inputs = [
            None,
            "not a dict",
            123,
            [],
            {},
            {"current": "not a list"},
            {"current": [], "delinquent": "not a list"}
        ]
        
        for invalid_input in invalid_inputs:
            # Call the method with invalid input
            result = self.handler._process_stake_info(invalid_input)
            
            # Assert the result has default values
            self.assertIn("total_stake", result)
            self.assertEqual(result["total_stake"], 0)
            self.assertIn("active_validators", result)
            self.assertEqual(result["active_validators"], 0)

    @pytest.mark.asyncio
    async def test_process_stake_info_invalid_stake_values(self):
        """Test _process_stake_info with invalid stake values."""
        await self.async_setup()
        # Create test data with invalid stake values
        vote_accounts = {
            "current": [
                {"votePubkey": "vote1", "activatedStake": "not a number"},
                {"votePubkey": "vote2", "activatedStake": -1000000000},
                {"votePubkey": "vote3", "activatedStake": 2000000000}
            ],
            "delinquent": []
        }
        
        # Call the method
        result = self.handler._process_stake_info(vote_accounts)
        
        # Assert the result only includes valid stake
        self.assertEqual(result["total_stake"], 2.0)
        self.assertEqual(result["active_validators"], 1)
        self.assertEqual(result["processing_errors"], 2)

    @pytest.mark.asyncio
    async def test_process_stake_info_object_with_dict_attr(self):
        """Test _process_stake_info with objects that have __dict__ attribute."""
        await self.async_setup()
        # Create a mock object with __dict__ attribute
        class MockValidator:
            def __init__(self, pubkey, stake):
                self.votePubkey = pubkey
                self.activatedStake = stake
        
        current = [MockValidator("vote1", 1000000000), MockValidator("vote2", 2000000000)]
        delinquent = [MockValidator("vote3", 500000000)]
        
        # Create test data with objects
        vote_accounts = {
            "current": current,
            "delinquent": delinquent
        }
        
        # Call the method
        result = self.handler._process_stake_info(vote_accounts)
        
        # Assert the result is correct
        self.assertEqual(result["total_stake"], 3.5)
        self.assertEqual(result["active_validators"], 3)
        self.assertEqual(result["delinquent_validators"], 1)
        self.assertEqual(result["delinquent_stake"], 0.5)


if __name__ == "__main__":
    unittest.main()
