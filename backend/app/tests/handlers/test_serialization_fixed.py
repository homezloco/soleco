"""
Tests for the serialization functionality in the Solana RPC error handling.

This test suite covers:
1. Serialization of various Solana object types
2. Handling of Pubkey objects
3. Handling of coroutines during serialization
4. Error handling during serialization
"""

import unittest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import pytest
from solders.pubkey import Pubkey

from app.utils.solana_helpers import serialize_solana_object


class TestSerialization(unittest.TestCase):
    """Test cases for the serialization functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Set up logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger('test_serialization')

    def test_serialize_primitive_types(self):
        """Test serialization of primitive types."""
        # Test with various primitive types
        test_cases = [
            (None, None),
            (123, 123),
            (123.45, 123.45),
            ("test string", "test string"),
            (True, True),
            (False, False)
        ]
        
        for input_value, expected_output in test_cases:
            result = serialize_solana_object(input_value)
            self.assertEqual(result, expected_output)

    def test_serialize_dict(self):
        """Test serialization of dictionaries."""
        # Test with a simple dictionary
        input_dict = {
            "key1": "value1",
            "key2": 123,
            "key3": True
        }
        result = serialize_solana_object(input_dict)
        self.assertEqual(result, input_dict)
        
        # Test with a nested dictionary
        nested_dict = {
            "key1": {
                "nested1": "value1",
                "nested2": 123
            },
            "key2": [1, 2, 3]
        }
        result = serialize_solana_object(nested_dict)
        self.assertEqual(result, nested_dict)

    def test_serialize_list(self):
        """Test serialization of lists."""
        # Test with a simple list
        input_list = [1, 2, 3, "test", True]
        result = serialize_solana_object(input_list)
        self.assertEqual(result, input_list)
        
        # Test with a nested list
        nested_list = [1, [2, 3], {"key": "value"}]
        result = serialize_solana_object(nested_list)
        self.assertEqual(result, nested_list)

    def test_serialize_pubkey(self):
        """Test serialization of Pubkey objects."""
        # Create a Pubkey object
        pubkey = Pubkey.from_string("11111111111111111111111111111111")
        
        # Serialize it
        result = serialize_solana_object(pubkey)
        
        # Assert the result is the string representation
        self.assertEqual(result, str(pubkey))

    @pytest.mark.asyncio
    async def test_serialize_coroutine(self):
        """Test serialization of coroutines."""
        # Create a coroutine
        async def test_coro():
            return "coroutine result"
            
        coro = test_coro()
        
        # Serialize it
        result = serialize_solana_object(coro)
        
        # Assert the result is the awaited value
        self.assertEqual(result, "coroutine result")
        
        # Clean up
        try:
            await coro
        except:
            pass  # Already consumed

    def test_serialize_object_with_to_json(self):
        """Test serialization of objects with to_json method."""
        # Create a mock object with to_json method
        mock_obj = MagicMock()
        mock_obj.to_json.return_value = {"json": "data"}
        
        # Serialize it
        result = serialize_solana_object(mock_obj)
        
        # Assert the result is from to_json
        self.assertEqual(result, {"json": "data"})
        mock_obj.to_json.assert_called_once()

    def test_serialize_object_with_to_dict(self):
        """Test serialization of objects with to_dict method."""
        # Create a mock object with to_dict method
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"dict": "data"}
        mock_obj.to_json = None  # Ensure to_json is not used
        
        # Serialize it
        result = serialize_solana_object(mock_obj)
        
        # Assert the result is from to_dict
        self.assertEqual(result, {"dict": "data"})
        mock_obj.to_dict.assert_called_once()

    def test_serialize_object_with_dict_attr(self):
        """Test serialization of objects with __dict__ attribute."""
        # Create a class with __dict__ attribute
        class TestClass:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 123
        
        # Create an instance
        obj = TestClass()
        
        # Serialize it
        result = serialize_solana_object(obj)
        
        # Assert the result is the __dict__
        self.assertEqual(result, {"attr1": "value1", "attr2": 123})

    def test_serialize_complex_nested_structure(self):
        """Test serialization of complex nested structures."""
        # Create a complex nested structure
        # Using valid base58 encoded pubkey strings for Solana
        # These are valid Solana pubkeys
        pubkey1 = Pubkey.from_string("11111111111111111111111111111111")
        
        # Create a simple class that mimics Pubkey behavior for the second one
        class PubkeyLike:
            def __str__(self):
                return "22222222222222222222222222222222"
        
        pubkey2 = PubkeyLike()
        
        class TestClass:
            def __init__(self):
                self.attr = "value"
        
        mock_obj = MagicMock()
        mock_obj.to_json.return_value = {"json": "data"}
        
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
        
        # Assert the structure is correctly serialized
        self.assertEqual(result["pubkeys"][0], str(pubkey1))
        self.assertEqual(result["pubkeys"][1], str(pubkey2))
        self.assertEqual(result["objects"][0], {"attr": "value"})
        self.assertEqual(result["objects"][1], {"json": "data"})
        self.assertEqual(result["nested"]["list"], [1, 2, 3])
        self.assertEqual(result["nested"]["dict"], {"key": "value"})

    def test_serialize_with_error(self):
        """Test serialization with an error during the process."""
        # Create a mock object that raises an exception during serialization
        mock_obj = MagicMock()
        mock_obj.to_json.side_effect = Exception("to_json error")
        mock_obj.to_dict.side_effect = Exception("to_dict error")
        
        # Create a custom class with a __dict__ property that raises an exception
        class ErrorClass:
            @property
            def __dict__(self):
                raise Exception("__dict__ error")
        
        error_obj = ErrorClass()
        
        # Serialize it
        result = serialize_solana_object(error_obj)
        
        # Assert the result is a string representation
        self.assertTrue(isinstance(result, str))
        self.assertIn("Error serializing", result)


if __name__ == "__main__":
    unittest.main()
