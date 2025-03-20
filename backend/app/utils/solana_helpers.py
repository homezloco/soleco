"""
Helper functions and utilities for Solana query operations.
"""

import asyncio
import base64
import inspect
import json
import logging
import random
import sys
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union, Set, Callable

import aiohttp
from solders.pubkey import Pubkey

from .solana_error import RetryableError, RPCError, RateLimitError, SlotSkippedError
from .solana_types import NodeUnhealthyError

# Configure logging
logger = logging.getLogger(__name__)

# Default configurations
DEFAULT_BLOCK_OPTIONS = {
    "transactionDetails": "full",
    "rewards": False
}

DEFAULT_BATCH_SIZE = 10
DEFAULT_COMMITMENT = "finalized"

def serialize_solana_object(obj):
    """
    Serialize Solana objects to JSON-compatible formats.
    
    This function handles various Solana object types including:
    - Pubkey objects
    - Coroutines
    - Objects with __dict__ attribute
    - Objects with to_json or to_dict methods
    - Basic Python types
    
    Args:
        obj: The object to serialize
        
    Returns:
        A JSON-serializable representation of the object
    """
    try:
        # Handle None
        if obj is None:
            return None
            
        # Handle coroutines
        if asyncio.iscoroutine(obj):
            logger.warning(f"Attempted to serialize a coroutine: {obj}")
            return str(obj)
            
        # Handle Pubkey objects which have a special __str__ method
        if hasattr(obj, '__class__') and obj.__class__.__name__ == 'Pubkey':
            logger.debug(f"Serializing Pubkey object: {obj}")
            return str(obj)
            
        # Handle basic types that are JSON serializable
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
            
        # Handle dictionaries
        if isinstance(obj, dict):
            logger.debug(f"Serializing dictionary with keys: {list(obj.keys())}")
            return {k: serialize_solana_object(v) for k, v in obj.items()}
            
        # Handle lists and tuples
        if isinstance(obj, (list, tuple)):
            logger.debug(f"Serializing list/tuple of length: {len(obj)}")
            return [serialize_solana_object(item) for item in obj]
            
        # Handle objects with to_json or to_dict methods
        if hasattr(obj, 'to_json') and callable(obj.to_json):
            try:
                logger.debug(f"Serializing object with to_json: {obj}")
                return obj.to_json()
            except Exception as e:
                logger.error(f"Error calling to_json: {e}")
                # Continue with other serialization methods
            
        if hasattr(obj, 'to_dict') and callable(obj.to_dict):
            try:
                logger.debug(f"Serializing object with to_dict: {obj}")
                return obj.to_dict()
            except Exception as e:
                logger.error(f"Error calling to_dict: {e}")
                # Continue with other serialization methods
            
        # Handle objects with custom __str__ method (like PubkeyLike)
        # Check for custom __str__ method before checking __dict__
        if hasattr(obj, '__str__') and obj.__str__ is not object.__str__:
            # For objects that primarily exist to be represented as strings (like Pubkey-like objects)
            # or objects with empty __dict__, use their string representation
            if not hasattr(obj, '__dict__') or not obj.__dict__:
                logger.debug(f"Serializing object with custom __str__ and no/empty __dict__: {obj}")
                return str(obj)
                
        # Handle objects with __dict__ attribute (convert to dict)
        if hasattr(obj, '__dict__'):
            try:
                if obj.__dict__ is not None and isinstance(obj.__dict__, dict):
                    # If __dict__ is empty but object has a custom __str__, use string representation
                    if not obj.__dict__ and hasattr(obj, '__str__') and obj.__str__ is not object.__str__:
                        logger.debug(f"Serializing object with empty __dict__ and custom __str__: {obj}")
                        return str(obj)
                    
                    logger.debug(f"Serializing object with __dict__: {obj}")
                    serialized_dict = {k: serialize_solana_object(v) for k, v in obj.__dict__.items() 
                                    if not k.startswith('_') and not inspect.ismethod(v)}
                    
                    # If serialized dict is empty but object has a custom __str__, use string representation
                    if not serialized_dict and hasattr(obj, '__str__') and obj.__str__ is not object.__str__:
                        logger.debug(f"Serializing object with empty serialized __dict__ and custom __str__: {obj}")
                        return str(obj)
                    
                    return serialized_dict
            except (AttributeError, TypeError) as e:
                logger.error(f"Error accessing __dict__: {e}")
                # Continue with other serialization methods
        
        # Final fallback for custom __str__ method
        if hasattr(obj, '__str__') and obj.__str__ is not object.__str__:
            logger.debug(f"Falling back to custom __str__ serialization for: {obj}")
            return str(obj)
                   
        # Default: convert to string
        logger.debug(f"Falling back to string serialization for: {obj}")
        return str(obj)
        
    except Exception as e:
        logger.error(f"Error serializing object: {e}")
        return f"<Error serializing object: {str(e)}>"

async def safe_rpc_call_async(
    method_or_name,
    *args,
    client=None,
    max_retries=3,
    retry_delay=1.0,
    timeout=30.0,
    error_callback=None,
    **kwargs
):
    """
    Execute an RPC call with retry logic and error handling.
    
    Args:
        method_or_name: Either a callable method or a string method name to call on the client
        *args: Arguments to pass to the method
        client: Optional client to use (if None, one will be obtained from the pool)
        max_retries: Maximum number of retries
        retry_delay: Base delay between retries in seconds
        timeout: Timeout for the operation in seconds
        error_callback: Optional callback function for errors
        **kwargs: Additional keyword arguments for the method
        
    Returns:
        Result of the RPC call
        
    Raises:
        RPCError: If all retries fail
    """
    from ..utils.solana_rpc import get_connection_pool
    
    start_time = time.time()
    attempts = 0
    backoff = retry_delay
    client_from_pool = False
    connection_pool = None
    log_prefix = ""
    
    # Determine what we're calling
    if isinstance(method_or_name, str):
        method_name = method_or_name
        log_prefix = f"{method_name}: "
    else:
        method_name = method_or_name.__name__ if hasattr(method_or_name, "__name__") else "unknown_method"
        log_prefix = f"{method_name}: "
    
    # Keep track of tried endpoints to avoid retrying the same one
    tried_endpoints = set()
    rate_limited_endpoints = set()
    error_endpoints = {}  # Track specific errors by endpoint
    
    # Special handling for getClusterNodes method
    is_get_cluster_nodes = method_name == "get_cluster_nodes" or method_name == "getClusterNodes"
    if is_get_cluster_nodes:
        logger.info(f"Executing getClusterNodes RPC call with special handling")
    
    while attempts < max_retries:
        attempts += 1
        release_client = False
        
        try:
            # Get a client if one wasn't provided
            if client is None:
                # Get the connection pool if we don't have it yet
                if connection_pool is None:
                    connection_pool = await get_connection_pool()
                
                # Get a client from the pool
                client = await connection_pool.get_client()
                client_from_pool = True
                release_client = True
                
                # Skip if we've already tried this endpoint
                endpoint = client.endpoint
                if endpoint in tried_endpoints:
                    logger.debug(f"{log_prefix}Skipping already tried endpoint {endpoint}")
                    
                    # Release the client before continuing
                    if client_from_pool and connection_pool is not None:
                        try:
                            await connection_pool.release(client, success=False)
                        except Exception as release_error:
                            logger.error(f"{log_prefix}Error releasing client: {str(release_error)}")
                    
                    continue
                
                # Skip if this endpoint was rate limited
                if endpoint in rate_limited_endpoints:
                    logger.debug(f"{log_prefix}Skipping rate-limited endpoint {endpoint}")
                    
                    # Release the client before continuing
                    if client_from_pool and connection_pool is not None:
                        try:
                            await connection_pool.release(client, success=False)
                        except Exception as release_error:
                            logger.error(f"{log_prefix}Error releasing client: {str(release_error)}")
                    
                    continue
                
                tried_endpoints.add(endpoint)
            
            # Log the endpoint we're using
            logger.debug(f"{log_prefix}Using endpoint: {client.endpoint}")
            
            # Execute the method
            if isinstance(method_or_name, str):
                # It's a method name, call it on the client
                method = getattr(client, method_or_name)
                
                # Special handling for getClusterNodes
                if is_get_cluster_nodes:
                    logger.debug(f"Calling getClusterNodes on client with endpoint {client.endpoint}")
                
                result = await asyncio.wait_for(method(*args, **kwargs), timeout=timeout)
            else:
                # It's a callable, call it directly
                result = await asyncio.wait_for(method_or_name(client, *args, **kwargs), timeout=timeout)
            
            # If we get here, the call succeeded
            if client_from_pool and connection_pool is not None:
                # Update endpoint stats with success
                if hasattr(connection_pool, 'update_endpoint_stats'):
                    connection_pool.update_endpoint_stats(client.endpoint, True, time.time() - start_time)
            
            # Special handling for getClusterNodes result
            if is_get_cluster_nodes:
                logger.debug(f"getClusterNodes result type: {type(result)}")
                
                # Check for error in the response
                if isinstance(result, dict) and 'error' in result:
                    error = result['error']
                    error_msg = error.get('message', str(error))
                    error_code = error.get('code', 0)
                    
                    # Track this endpoint's error
                    error_endpoints[client.endpoint] = {
                        'message': error_msg,
                        'code': error_code
                    }
                    
                    logger.warning(f"getClusterNodes returned error from {client.endpoint}: {error_msg} (code: {error_code})")
                    
                    # Release the client with failure status
                    if client_from_pool and connection_pool is not None:
                        try:
                            await connection_pool.release(client, success=False)
                            release_client = False  # Already released
                        except Exception as release_error:
                            logger.error(f"{log_prefix}Error releasing client: {str(release_error)}")
                    
                    # If this is the last attempt, return the error result with additional context
                    if attempts >= max_retries:
                        # Add additional context to the error result
                        result['_soleco_context'] = {
                            'attempted_endpoints': list(tried_endpoints),
                            'endpoint_errors': error_endpoints,
                            'attempts': attempts
                        }
                        logger.error(f"All getClusterNodes attempts failed. Last error: {error_msg}")
                        return result
                    
                    # Otherwise, try another endpoint
                    continue
                
                # Check for empty or invalid response
                if isinstance(result, list) and len(result) == 0:
                    logger.warning(f"getClusterNodes returned empty list from {client.endpoint}")
                    
                    # Release the client with failure status
                    if client_from_pool and connection_pool is not None:
                        try:
                            await connection_pool.release(client, success=False)
                            release_client = False  # Already released
                        except Exception as release_error:
                            logger.error(f"{log_prefix}Error releasing client: {str(release_error)}")
                    
                    # If this is the last attempt, add context to the empty result
                    if attempts >= max_retries:
                        empty_result = {
                            'error': {
                                'message': 'All endpoints returned empty cluster nodes list',
                                'code': -32000  # Generic server error
                            },
                            '_soleco_context': {
                                'attempted_endpoints': list(tried_endpoints),
                                'endpoint_errors': error_endpoints,
                                'attempts': attempts
                            }
                        }
                        logger.error("All getClusterNodes attempts returned empty lists")
                        return empty_result
                    
                    # Try another endpoint
                    continue
            
            # Return the successful result
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"{log_prefix}Request timed out after {timeout}s on attempt {attempts}/{max_retries}")
            if client_from_pool and connection_pool is not None and hasattr(connection_pool, 'update_endpoint_stats'):
                # Update endpoint stats with failure
                connection_pool.update_endpoint_stats(client.endpoint, False, timeout)
                
            # Track this endpoint's error
            if is_get_cluster_nodes and client and hasattr(client, 'endpoint'):
                error_endpoints[client.endpoint] = {
                    'message': f'Request timed out after {timeout}s',
                    'code': -32000,  # Generic server error
                    'type': 'TimeoutError'
                }
                
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"{log_prefix}Error on attempt {attempts}/{max_retries}: {error_msg}")
            
            # Check for rate limiting errors
            is_rate_limited = False
            if "429" in error_msg or "rate limit" in error_msg.lower():
                is_rate_limited = True
                if client and hasattr(client, 'endpoint'):
                    rate_limited_endpoints.add(client.endpoint)
                    logger.warning(f"{log_prefix}Endpoint {client.endpoint} is rate limited")
            
            # Update endpoint stats with failure
            if client_from_pool and connection_pool is not None and hasattr(connection_pool, 'update_endpoint_stats'):
                connection_pool.update_endpoint_stats(client.endpoint, False, time.time() - start_time)
            
            # Track this endpoint's error for getClusterNodes
            if is_get_cluster_nodes and client and hasattr(client, 'endpoint'):
                error_endpoints[client.endpoint] = {
                    'message': error_msg,
                    'code': -32000,  # Generic server error
                    'type': type(e).__name__,
                    'stack': traceback.format_exc() if 'traceback' in sys.modules else None
                }
            
            # Call error callback if provided
            if error_callback:
                try:
                    error_callback(e)
                except Exception as callback_error:
                    logger.error(f"{log_prefix}Error in error callback: {str(callback_error)}")
        
        finally:
            # Release the client back to the pool
            if release_client and client and connection_pool is not None:
                try:
                    await connection_pool.release(client, success=False)
                    client = None  # Set to None to get a new client on the next attempt
                except Exception as release_error:
                    logger.error(f"{log_prefix}Error releasing client: {str(release_error)}")
        
        # Exponential backoff for retries
        if attempts < max_retries:
            # Calculate backoff with jitter
            jitter = random.uniform(0.8, 1.2)
            sleep_time = backoff * jitter
            logger.debug(f"{log_prefix}Retrying in {sleep_time:.2f}s (attempt {attempts}/{max_retries})")
            await asyncio.sleep(sleep_time)
            backoff *= 2  # Exponential backoff
    
    # If we get here, all retries failed
    total_time = time.time() - start_time
    
    # Special handling for getClusterNodes failure
    if is_get_cluster_nodes:
        error_result = {
            'error': {
                'message': f'Failed to get cluster nodes after {max_retries} attempts',
                'code': -32000  # Generic server error
            },
            '_soleco_context': {
                'attempted_endpoints': list(tried_endpoints),
                'endpoint_errors': error_endpoints,
                'attempts': attempts,
                'total_time': total_time
            }
        }
        logger.error(f"All getClusterNodes attempts failed after {total_time:.2f}s")
        return error_result
    
    # For other methods, raise an exception
    error_message = f"Failed after {max_retries} attempts and {total_time:.2f}s"
    logger.error(f"{log_prefix}{error_message}")
    
    raise RPCError(error_message)

def handle_rpc_error(error: Exception, context: str) -> None:
    """Standardized error handling for RPC calls."""
    error_msg = str(error).lower()
    
    if "429" in error_msg or "rate limit" in error_msg:
        raise RateLimitError(f"Rate limit exceeded: {context}")
    elif "timeout" in error_msg:
        raise RetryableError(f"Timeout: {context}")
    elif "slot was skipped" in error_msg:
        raise SlotSkippedError(f"Slot skipped: {context}")
    elif "block not available" in error_msg:
        logger.info(f"Block not available: {context}")
        return None
    else:
        raise RPCError(f"RPC error in {context}: {error}")

def extract_message(tx: Any) -> Dict[str, Any]:
    """Extract and decode transaction message."""
    message = {}
    
    try:
        if isinstance(tx, dict):
            # Handle transaction wrapper
            if 'transaction' in tx:
                tx = tx['transaction']
                
            message = tx.get('message', {})
            if isinstance(message, str):
                try:
                    decoded = base64.b64decode(message)
                    message = json.loads(decoded)
                except:
                    logger.error("Failed to decode base64 message")
                    message = {}
        elif hasattr(tx, 'message'):
            message = tx.message
            if hasattr(message, '__dict__'):
                message = message.__dict__
                
        if not isinstance(message, dict):
            logger.debug(f"Invalid message type: {type(message)}")
            message = {}
            
    except Exception as e:
        logger.error(f"Error extracting message: {str(e)}")
        message = {}
        
    return message

def extract_account_keys(message: Dict[str, Any]) -> List[str]:
    """Extract account keys from message."""
    keys = []
    try:
        for key in message.get('accountKeys', []):
            if isinstance(key, dict):
                pubkey = key.get('pubkey')
                if pubkey:
                    keys.append(str(pubkey))
            elif isinstance(key, str):
                keys.append(str(key))
    except Exception as e:
        logger.error(f"Error extracting account keys: {str(e)}")
    return keys

def extract_signatures(tx: Any) -> List[str]:
    """Extract signatures from transaction."""
    signatures = []
    try:
        if isinstance(tx, dict):
            # Handle transaction wrapper
            if 'transaction' in tx:
                tx = tx['transaction']
                
            sigs = tx.get('signatures', [])
            if isinstance(sigs, (list, tuple)):
                signatures.extend(str(sig) for sig in sigs if sig)
    except Exception as e:
        logger.error(f"Error extracting signatures: {str(e)}")
    return signatures

def transform_instruction(instr: Any, account_keys: List[str], idx: int) -> Dict[str, Any]:
    """Transform a single instruction into standardized format."""
    try:
        # Handle raw string instruction
        if isinstance(instr, str):
            try:
                # Try to decode as base64
                decoded = base64.b64decode(instr)
                try:
                    # Try to parse as JSON
                    parsed = json.loads(decoded)
                    if isinstance(parsed, dict):
                        logger.debug(f"Successfully decoded instruction {idx} from base64 JSON")
                        return transform_instruction(parsed, account_keys, idx)
                except json.JSONDecodeError:
                    pass
            except:
                pass
                
            # If decoding fails, wrap raw string
            logger.debug(f"Wrapping raw string instruction {idx}")
            return {
                'programId': account_keys[0] if account_keys else '',
                'accounts': account_keys[1:] if len(account_keys) > 1 else [],
                'data': {
                    'raw': instr,
                    'parsed': None
                }
            }
            
        # Handle dict instruction
        if isinstance(instr, dict):
            logger.debug(f"Processing dict instruction {idx}")
            
            # Get program ID
            program_id = instr.get('programId', '')
            
            # Get accounts
            accounts = []
            raw_accounts = instr.get('accounts', [])
            if isinstance(raw_accounts, list):
                # Convert account indexes to addresses
                for acc_idx in raw_accounts:
                    if isinstance(acc_idx, int) and 0 <= acc_idx < len(account_keys):
                        accounts.append(account_keys[acc_idx])
                        
            # Get instruction data
            data = instr.get('data', '')
            if isinstance(data, dict):
                # Keep parsed data structure
                parsed_data = data
            else:
                # Try to decode if string
                if isinstance(data, str):
                    try:
                        decoded = base64.b64decode(data)
                        try:
                            parsed = json.loads(decoded)
                            parsed_data = {
                                'raw': data,
                                'parsed': parsed
                            }
                        except json.JSONDecodeError:
                            parsed_data = {
                                'raw': data,
                                'parsed': None
                            }
                    except:
                        parsed_data = {
                            'raw': data,
                            'parsed': None
                        }
                else:
                    parsed_data = {
                        'raw': str(data),
                        'parsed': None
                    }
                
            instruction = {
                'programId': program_id,
                'accounts': accounts,
                'data': parsed_data
            }
            
            # Add program ID from index if needed
            if not instruction['programId']:
                program_idx = instr.get('programIdIndex')
                if isinstance(program_idx, int) and 0 <= program_idx < len(account_keys):
                    instruction['programId'] = account_keys[program_idx]
                    logger.debug(f"Added program ID from index for instruction {idx}")
                    
            # Add account addresses from indexes if needed
            if not instruction['accounts']:
                account_indexes = instr.get('accountIndexes', [])
                if isinstance(account_indexes, list):
                    instruction['accounts'] = [
                        account_keys[idx] 
                        for idx in account_indexes 
                        if isinstance(idx, int) and 0 <= idx < len(account_keys)
                    ]
                    logger.debug(f"Added {len(instruction['accounts'])} accounts from indexes")
                    
            return instruction
            
        # Handle unknown format
        logger.warning(f"Unknown instruction format {type(instr)} for instruction {idx}")
        return {
            'programId': account_keys[0] if account_keys else '',
            'accounts': account_keys[1:] if len(account_keys) > 1 else [],
            'data': {
                'raw': '',
                'parsed': None
            }
        }
        
    except Exception as e:
        logger.error(f"Error transforming instruction {idx}: {str(e)}")
        return {
            'programId': '',
            'accounts': [],
            'data': {
                'raw': '',
                'parsed': None
            }
        }

def build_transaction_structure(tx: Any, meta: Any) -> Dict[str, Any]:
    """Build a standardized transaction structure from raw data."""
    try:
        if not tx:
            logger.debug("Empty transaction data")
            return {}
            
        # Extract message
        message = extract_message(tx)
        if not message:
            logger.debug("Empty message in transaction")
            return {}
            
        # Get account keys
        account_keys = extract_account_keys(message)
        if not account_keys:
            logger.debug("No account keys found in message")
            return {}
            
        # Process instructions
        instructions = []
        raw_instructions = message.get('instructions', [])
        
        if not raw_instructions:
            logger.debug("No instructions found in message")
            return {}
            
        logger.debug(f"Processing {len(raw_instructions)} instructions")
        
        # Transform each instruction
        for idx, instr in enumerate(raw_instructions):
            # Handle string instruction
            if isinstance(instr, str):
                instruction = {
                    'programId': account_keys[0] if account_keys else '',
                    'accounts': account_keys[1:] if len(account_keys) > 1 else [],
                    'data': {
                        'raw': instr,
                        'parsed': None
                    }
                }
            else:
                instruction = transform_instruction(instr, account_keys, idx)
                
            if instruction:
                instructions.append(instruction)
        
        # Build final structure
        result = {
            'transaction': {
                'message': {
                    'accountKeys': account_keys,
                    'instructions': instructions,
                    'recentBlockhash': message.get('recentBlockhash', ''),
                    'header': message.get('header', {})
                },
                'signatures': extract_signatures(tx)
            },
            'meta': meta
        }
        
        logger.debug(f"Built transaction structure with {len(instructions)} instructions")
        return result
        
    except Exception as e:
        logger.error(f"Error building transaction structure: {str(e)}")
        return {}

def transform_transaction_data(tx_data: Union[List, Dict]) -> Dict[str, Any]:
    """Transform raw transaction data into a standardized format."""
    try:
        # Extract transaction and meta data
        if isinstance(tx_data, list):
            tx = tx_data[0] if tx_data else None
            meta = tx_data[1] if len(tx_data) > 1 else None
        else:
            tx = tx_data
            meta = tx_data.get('meta') if isinstance(tx_data, dict) else None
            
        # Handle transaction object
        if isinstance(tx, dict) and 'transaction' in tx:
            tx = tx['transaction']
            
        # Build structure
        return build_transaction_structure(tx, meta)
        
    except Exception as e:
        logger.error(f"Error transforming transaction data: {str(e)}")
        return {}

def get_block_options(commitment: str = DEFAULT_COMMITMENT) -> Dict[str, Any]:
    """Get standardized block options with the given commitment level."""
    return {
        **DEFAULT_BLOCK_OPTIONS,
        "commitment": commitment
    }

def create_slot_batches(start_slot: int, end_slot: int, batch_size: int = DEFAULT_BATCH_SIZE) -> List[List[int]]:
    """Create batches of slots for parallel processing."""
    slots = list(range(start_slot, end_slot + 1))
    return [slots[i:i + batch_size] for i in range(0, len(slots), batch_size)]

# Health monitoring helpers
async def get_endpoints_health() -> List[Dict[str, Any]]:
    """Get health status of all RPC endpoints"""
    from .solana_connection import get_connection_pool
    connection_pool = await get_connection_pool()
    return await connection_pool.get_endpoint_health()

async def get_endpoint_health_detail(endpoint: str) -> Dict[str, Any]:
    """Get detailed health status for specific endpoint"""
    from .solana_connection import get_connection_pool
    connection_pool = await get_connection_pool()
    return await connection_pool.get_endpoint_health_detail(endpoint)

# RPC pool management helpers
async def get_rpc_pool_status() -> Dict[str, Any]:
    """Get current RPC pool status"""
    from .solana_connection import get_connection_pool
    connection_pool = await get_connection_pool()
    return await connection_pool.get_pool_status()

async def rotate_rpc_endpoint() -> Dict[str, Any]:
    """Force rotation to next endpoint"""
    from .solana_connection import get_connection_pool
    connection_pool = await get_connection_pool()
    return await connection_pool.rotate_endpoint()

async def get_rpc_endpoints() -> List[Dict[str, Any]]:
    """List available endpoints"""
    from .solana_connection import get_connection_pool
    connection_pool = await get_connection_pool()
    return connection_pool.get_endpoints()

# Network performance metrics helpers
async def get_tps_metrics() -> Dict[str, Any]:
    """Get current transactions per second"""
    from .solana_query import SolanaQueryHandler
    from .cache.database_cache import get_database_cache
    
    cache = await get_database_cache()
    handler = SolanaQueryHandler(cache=cache)  # Fix: Pass cache as a keyword argument
    return await handler.get_tps()

async def get_block_time_metrics() -> Dict[str, Any]:
    """Get average block time"""
    from .solana_query import SolanaQueryHandler
    from .cache.database_cache import get_database_cache
    
    cache = await get_database_cache()
    handler = SolanaQueryHandler(cache=cache)  # Fix: Pass cache as a keyword argument
    return await handler.get_block_time()

# Advanced analytics helpers
async def get_token_mints_analytics() -> Dict[str, Any]:
    """Get analytics for new token mints"""
    from .solana_query import SolanaQueryHandler
    from .cache.database_cache import get_database_cache
    
    cache = await get_database_cache()
    handler = SolanaQueryHandler(cache=cache)  # Fix: Pass cache as a keyword argument
    return await handler.get_token_mints_analytics()

async def get_pump_token_data() -> Dict[str, Any]:
    """Get pump token tracking data"""
    from .solana_query import SolanaQueryHandler
    from .cache.database_cache import get_database_cache
    
    cache = await get_database_cache()
    handler = SolanaQueryHandler(cache=cache)  # Fix: Pass cache as a keyword argument
    return await handler.get_pump_token_data()

async def get_dex_activity_data() -> Dict[str, Any]:
    """Get DEX trading activity"""
    from .solana_query import SolanaQueryHandler
    from .cache.database_cache import get_database_cache
    
    cache = await get_database_cache()
    handler = SolanaQueryHandler(cache=cache)  # Fix: Pass cache as a keyword argument
    return await handler.get_dex_activity()

def validate_address(address: str) -> bool:
    """
    Validate if a string is a valid Solana address.
    
    Args:
        address: The address to validate
        
    Returns:
        bool: True if the address is valid
    """
    try:
        # Try to create a Pubkey object from the address
        Pubkey.from_string(address)
        return True
    except Exception as e:
        logger.debug(f"Invalid address: {address}, error: {str(e)}")
        return False

def parse_transaction(tx_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a transaction into a standardized format.
    
    Args:
        tx_data: Raw transaction data
        
    Returns:
        Dict: Standardized transaction data
    """
    try:
        result = {
            "transaction_id": tx_data.get("signature", ""),
            "block_time": tx_data.get("blockTime", 0),
            "slot": tx_data.get("slot", 0),
            "fee": tx_data.get("meta", {}).get("fee", 0),
            "status": "success" if tx_data.get("meta", {}).get("err") is None else "error",
            "instructions": []
        }
        
        # Extract instructions
        if "transaction" in tx_data and "message" in tx_data["transaction"]:
            message = tx_data["transaction"]["message"]
            instructions = message.get("instructions", [])
            
            for idx, instr in enumerate(instructions):
                program_idx = instr.get("programIdIndex", 0)
                program_id = message.get("accountKeys", [])[program_idx] if program_idx < len(message.get("accountKeys", [])) else None
                
                instruction_data = {
                    "program_id": program_id,
                    "accounts": [message.get("accountKeys", [])[i] for i in instr.get("accounts", [])],
                    "data": instr.get("data", "")
                }
                
                result["instructions"].append(instruction_data)
        
        return result
    except Exception as e:
        logger.error(f"Error parsing transaction: {str(e)}")
        return {"error": str(e), "raw_data": tx_data}

def calculate_fees(tx_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate fees and other transaction costs.
    
    Args:
        tx_data: Transaction data
        
    Returns:
        Dict: Fee information
    """
    try:
        meta = tx_data.get("meta", {})
        fee = meta.get("fee", 0)
        
        # Calculate compute units if available
        compute_units_consumed = 0
        compute_units_price = 0
        
        # Look for compute budget instructions
        if "transaction" in tx_data and "message" in tx_data["transaction"]:
            message = tx_data["transaction"]["message"]
            instructions = message.get("instructions", [])
            
            for instr in instructions:
                program_idx = instr.get("programIdIndex", 0)
                program_id = message.get("accountKeys", [])[program_idx] if program_idx < len(message.get("accountKeys", [])) else None
                
                # Check if this is a compute budget instruction
                if program_id == "ComputeBudget111111111111111111111111111111":
                    # This is a simplified check - in a real implementation you would decode the instruction data
                    compute_units_price = 1  # Placeholder
        
        return {
            "fee": fee,
            "compute_units_consumed": compute_units_consumed,
            "compute_units_price": compute_units_price,
            "total_cost": fee
        }
    except Exception as e:
        logger.error(f"Error calculating fees: {str(e)}")
        return {"error": str(e), "fee": 0}
