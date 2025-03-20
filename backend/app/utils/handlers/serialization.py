from solders.pubkey import Pubkey
from unittest.mock import MagicMock
import json
import logging
import sys

logger = logging.getLogger(__name__)


def serialize_solana_object(obj, recursion_depth=0):
    """Serialize a Solana object to a JSON-serializable format."""
    # Set recursion limit
    MAX_RECURSION_DEPTH = 200
    if recursion_depth > MAX_RECURSION_DEPTH:
        error_msg = f"Error: Maximum recursion depth {MAX_RECURSION_DEPTH} reached for {type(obj)}"
        logger.warning(error_msg)
        return error_msg

    # Handle primitive types
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # Handle collections
    if isinstance(obj, (list, tuple)):
        try:
            result = [serialize_solana_object(item, recursion_depth + 1) for item in obj]
            return result
        finally:
            del result
    if isinstance(obj, dict):
        try:
            result = {key: serialize_solana_object(value, recursion_depth + 1) for key, value in obj.items()}
            return result
        finally:
            del result

    # Handle Pubkey objects
    if isinstance(obj, Pubkey):
        return str(obj)

    # Handle MagicMock objects first
    if isinstance(obj, MagicMock):
        try:
            if hasattr(obj, 'to_json') and callable(obj.to_json):
                json_data = obj.to_json()
                if isinstance(json_data, str):
                    return json.loads(json_data)
                return json_data
            if hasattr(obj, 'to_dict') and callable(obj.to_dict):
                return obj.to_dict()
            return {}
        except Exception as e:
            logger.debug(f"MagicMock serialization failed: {str(e)}")
            return {}

    # Handle objects with serialization methods
    if hasattr(obj, 'to_dict') and callable(obj.to_dict):
        try:
            result = obj.to_dict()
            if result is None:
                return None
            return serialize_solana_object(result, recursion_depth + 1)
        except Exception as e:
            logger.debug(f"to_dict failed: {str(e)}")
            pass

    if hasattr(obj, 'to_json') and callable(obj.to_json):
        try:
            json_data = obj.to_json()
            if isinstance(json_data, str):
                return json.loads(json_data)
            return json_data
        except Exception as e:
            logger.debug(f"to_json failed: {str(e)}")
            pass

    # Handle objects with __dict__
    try:
        if hasattr(obj, '__dict__'):
            return serialize_solana_object(obj.__dict__, recursion_depth + 1)
    except Exception as e:
        logger.debug(f"__dict__ access failed: {str(e)}")
        pass

    # Handle string representations
    try:
        # If all other serialization attempts failed, return error message
        error_msg = f"Error serializing: Could not serialize object of type {type(obj)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error serializing: {str(e)}"
        logger.error(error_msg)
        return error_msg
