"""
Solana router module for handling Solana blockchain interactions
"""
from typing import Dict, List, Optional, Any, Union
import traceback
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.system_program import ID as SYSTEM_PROGRAM_ID
import time
import logging
import json
import asyncio
from datetime import datetime
import pytz
from collections import defaultdict

from ..utils.solana_rpc import (
    SolanaConnectionPool, 
    get_connection_pool,
    SolanaClient,
    create_robust_client,
    DEFAULT_RPC_ENDPOINTS
)
from ..utils.solana_query import SolanaQueryHandler
from ..utils.solana_errors import RetryableError, RPCError
from ..utils.handlers.rpc_node_extractor import RPCNodeExtractor
from ..database.sqlite import db_cache
from ..constants.cache import (
    NETWORK_STATUS_CACHE_TTL,
    PERFORMANCE_METRICS_CACHE_TTL,
    RPC_NODES_CACHE_TTL,
    TOKEN_INFO_CACHE_TTL
)

# Configure logging
logger = logging.getLogger(__name__)

# Program IDs
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
TOKEN_2022_PROGRAM_ID = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
VOTE_PROGRAM_ID = Pubkey.from_string("Vote111111111111111111111111111111111111111")

# Configuration for RPC connection
RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-api.projectserum.com",
    "https://rpc.ankr.com/solana"
]

def safe_serialize(obj):
    """
    Safely serialize complex Solders objects to JSON-compatible format
    
    Args:
        obj: Any object to be serialized
    
    Returns:
        JSON-serializable representation of the object
    """
    try:
        # Handle specific Solders types
        if hasattr(obj, 'to_json') and callable(obj.to_json):
            return obj.to_json()
        
        if hasattr(obj, '__str__'):
            return str(obj)
        
        # Handle hash and other complex types
        if hasattr(obj, 'bytes'):
            # Convert byte arrays to hex strings for readability
            return obj.bytes.hex()
        
        # Convert byte arrays to hex strings
        if isinstance(obj, bytes):
            return obj.hex()
        
        # Convert byte lists to hex strings
        if isinstance(obj, list) and all(isinstance(x, int) and 0 <= x <= 255 for x in obj):
            return bytes(obj).hex()
        
        # Recursively handle nested objects
        if isinstance(obj, (list, tuple)):
            return [safe_serialize(item) for item in obj]
        
        if isinstance(obj, dict):
            return {k: safe_serialize(v) for k, v in obj.items()}
        
        # Fallback to string representation
        return str(obj)
    
    except Exception as e:
        print(f"Serialization error for {type(obj)}: {e}")
        return str(obj)

def serialize_solana_object(obj):
    """
    Convert Solana-specific objects to JSON-serializable dictionaries
    
    Args:
        obj: Solana response object
    
    Returns:
        Dict or primitive: JSON-serializable representation of the object
    """
    try:
        # Handle coroutines (this should not happen with safe_rpc_call_async, but just in case)
        if asyncio.iscoroutine(obj):
            logger.warning(f"serialize_solana_object received a coroutine: {obj}")
            return {"error": "Received coroutine instead of result. This is likely a bug."}
            
        # Handle None
        if obj is None:
            return None
            
        # Handle primitives
        if isinstance(obj, (str, int, float, bool)):
            return obj
            
        # Handle lists
        if isinstance(obj, (list, tuple)):
            return [serialize_solana_object(item) for item in obj]
            
        # Handle dictionaries
        if isinstance(obj, dict):
            return {k: serialize_solana_object(v) for k, v in obj.items()}
            
        # Handle Pubkey
        if hasattr(obj, 'to_base58'):
            try:
                return obj.to_base58().decode('utf-8')
            except Exception as e:
                logger.error(f"Error converting Pubkey to base58: {str(e)}")
                return str(obj)
                
        # Handle objects with __dict__ attribute (convert to dict)
        if hasattr(obj, '__dict__'):
            # Some objects have circular references, so we need to be careful
            try:
                return {k: serialize_solana_object(v) for k, v in obj.__dict__.items() 
                        if not k.startswith('_') and not callable(v)}
            except Exception as e:
                logger.error(f"Error serializing object with __dict__: {str(e)}")
                return str(obj)
                
        # Handle objects with to_json or to_dict methods
        if hasattr(obj, 'to_json'):
            try:
                return obj.to_json()
            except Exception as e:
                logger.error(f"Error calling to_json: {str(e)}")
                
        if hasattr(obj, 'to_dict'):
            try:
                return obj.to_dict()
            except Exception as e:
                logger.error(f"Error calling to_dict: {str(e)}")
                
        # Handle objects with __str__ method
        return str(obj)
        
    except Exception as e:
        logger.error(f"Error in serialize_solana_object: {str(e)}")
        logger.error(traceback.format_exc())
        return str(obj)

def serialize_cluster_nodes(nodes):
    """
    Convert Solana cluster nodes to a more readable and structured format
    
    Args:
        nodes: List of RpcContactInfo objects
    
    Returns:
        List of dictionaries with parsed node information
    """
    parsed_nodes = []
    for node in nodes:
        try:
            node_info = {
                "pubkey": str(node.pubkey),
                "version": node.version,
                "feature_set": node.feature_set,
                "shred_version": node.shred_version,
                "network_endpoints": {
                    "gossip": node.gossip,
                    "tvu": node.tvu,
                    "tpu": node.tpu,
                    "tpu_quic": node.tpu_quic,
                    "tpu_forwards": node.tpu_forwards,
                    "tpu_forwards_quic": node.tpu_forwards_quic,
                    "tpu_vote": node.tpu_vote,
                    "serve_repair": node.serve_repair,
                    "rpc": node.rpc,
                    "pubsub": node.pubsub
                }
            }
            parsed_nodes.append(node_info)
        except Exception as e:
            # Fallback to string representation if parsing fails
            parsed_nodes.append(str(node))
    
    return parsed_nodes

def convert_block_to_dict(block_response):
    """
    Convert Solders block response to a concise, JSON-serializable dictionary
    
    Args:
        block_response: Solana block response object
    
    Returns:
        Compact serializable block dictionary
    """
    try:
        # Handle different response types
        if hasattr(block_response, 'value'):
            block_data = block_response.value
        elif hasattr(block_response, 'result'):
            block_data = block_response.result
        else:
            block_data = block_response
        
        # Safely get block time, use current time as fallback
        block_time = getattr(block_data, 'block_time', None)
        if block_time is None:
            block_time = int(time.time())
        
        # Ensure block time is a reasonable timestamp
        if block_time > int(time.time()) * 2:  # If timestamp seems unrealistic
            block_time = int(time.time())
        
        # Extract key block information
        serializable_block = {
            'block_number': getattr(block_data, 'block_height', 'N/A'),
            'block_hash': safe_serialize(getattr(block_data, 'blockhash', 'N/A')),
            'timestamp': block_time,
            'transaction_count': 0,
            'summary': {
                'total_transactions': 0,
                'success_transactions': 0,
                'failed_transactions': 0
            }
        }
        
        # Try to extract transactions
        try:
            transactions = getattr(block_data, 'transactions', [])
            serializable_block['transaction_count'] = len(transactions)
            
            # More robust transaction status checking
            def check_transaction_status(tx):
                try:
                    status = safe_serialize(getattr(tx, 'status', 'Unknown'))
                    # Add more specific status checks if needed
                    return status.lower() in ['success', 'ok', 'confirmed']
                except:
                    return False
            
            # Summarize transaction status
            transaction_summary = {
                'total_transactions': len(transactions),
                'success_transactions': sum(1 for tx in transactions if check_transaction_status(tx)),
                'failed_transactions': sum(1 for tx in transactions if not check_transaction_status(tx))
            }
            
            serializable_block['summary'] = transaction_summary
            
            # Optionally, include first few transaction signatures for reference
            serializable_block['sample_transactions'] = [
                safe_serialize(tx.transaction.signatures[0]) 
                for tx in transactions[:3] 
                if hasattr(tx, 'transaction')
            ]
        
        except Exception as tx_error:
            print(f"Error extracting transactions: {tx_error}")
        
        return serializable_block
    
    except Exception as conversion_error:
        print(f"Error converting block to dict: {conversion_error}")
        return {
            'block_number': 'N/A',
            'error': str(conversion_error)
        }

async def create_robust_client() -> SolanaClient:
    """
    Create a Solana RPC client with robust configuration and full method support
    
    Returns:
        SolanaClient: Our custom Solana RPC client
    """
    try:
        # Get the connection pool
        pool = await get_connection_pool()
        
        # Get a client from the pool
        client = await pool.get_client()
        if not client:
            raise ConnectionError("No healthy Solana RPC clients available")
            
        logger.info(f"Successfully connected to Solana RPC at {client.endpoint}")
        return client
        
    except Exception as e:
        logger.error(f"Error creating Solana client: {str(e)}")
        raise

def safe_rpc_call(client, method, *args, **kwargs):
    """
    Safely execute RPC calls with comprehensive error handling and serialization.
    Note: This function is not async-safe. For async methods, use safe_rpc_call_async instead.
    
    Args:
        client: Solana RPC client
        method: RPC method to call
        *args: Positional arguments for the method
        **kwargs: Keyword arguments for the method
    
    Returns:
        Dict: Comprehensive result or error information
    """
    try:
        # Convert string arguments to Pubkey
        converted_args = []
        for arg in args:
            if isinstance(arg, str):
                try:
                    # Attempt to convert string to Pubkey
                    converted_args.append(Pubkey.from_string(arg))
                except Exception as conversion_error:
                    # If conversion fails, log the error and use original argument
                    logger.warning(f"Pubkey conversion error: {conversion_error}")
                    converted_args.append(arg)
            else:
                converted_args.append(arg)
        
        # Dynamically call the method
        method_func = getattr(client, method)
        
        # Check if the method is a coroutine function (async)
        if asyncio.iscoroutinefunction(method_func):
            # This is an async method that needs to be awaited
            logger.warning(f"Method {method} is async but called with safe_rpc_call. Use safe_rpc_call_async instead.")
            return {
                'success': False,
                'error': f"Method {method} is async but called with safe_rpc_call. Use safe_rpc_call_async instead.",
                'method': method
            }
        else:
            # Regular synchronous method
            result = method_func(*converted_args, **kwargs)
            
            # Check if the result is a coroutine (some methods might return coroutines even if not marked as async)
            if asyncio.iscoroutine(result):
                logger.warning(f"Method {method} returned a coroutine but was called with safe_rpc_call. Use safe_rpc_call_async instead.")
                return {
                    'success': False,
                    'error': f"Method {method} returned a coroutine but was called with safe_rpc_call. Use safe_rpc_call_async instead.",
                    'method': method
                }
            
            # Serialize the result
            serialized_result = serialize_solana_object(result)
            
            return {
                'success': True,
                'result': serialized_result,
                'method': method,
                'args': str(args),
                'kwargs': str(kwargs)
            }
    except Exception as e:
        logger.error(f"Error in safe_rpc_call for method {method}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'method': method,
            'args': str(args),
            'kwargs': str(kwargs)
        }

async def safe_rpc_call_async(client, method, *args, **kwargs):
    """
    Safely execute async RPC calls with comprehensive error handling and serialization.
    This version properly awaits coroutines.
    
    Args:
        client: Solana RPC client
        method: RPC method to call
        *args: Positional arguments for the method
        **kwargs: Keyword arguments for the method
    
    Returns:
        Dict: Comprehensive result or error information
    """
    start_time = time.time()
    try:
        # Convert string arguments to Pubkey
        processed_args = []
        for arg in args:
            if isinstance(arg, str) and len(arg) == 44 and arg[0] in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                try:
                    processed_args.append(Pubkey.from_string(arg))
                except Exception:
                    processed_args.append(arg)
            else:
                processed_args.append(arg)
        
        # Get the method from the client
        method_to_call = getattr(client, method, None)
        if not method_to_call:
            logger.error(f"Method {method} not found on client")
            return {
                'success': False,
                'error': f"Method {method} not found on client",
                'method': method
            }
        
        # Call the method and await the result
        logger.debug(f"Calling {method} with args: {processed_args}, kwargs: {kwargs}")
        result = await method_to_call(*processed_args, **kwargs)
        
        # Log the response type and structure for debugging
        logger.debug(f"Response from {method} is of type {type(result)}")
        if isinstance(result, dict):
            logger.debug(f"Keys in response: {list(result.keys())}")
        
        # Serialize the result
        serialized_result = serialize_solana_object(result)
        
        # Calculate and log execution time
        execution_time = time.time() - start_time
        logger.debug(f"RPC call {method} completed in {execution_time:.2f}s")
        
        return {
            'success': True,
            'result': serialized_result,
            'execution_time': execution_time
        }
    except Exception as e:
        # Log detailed error information
        execution_time = time.time() - start_time
        error_msg = f"Error in safe_rpc_call_async for method {method}: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # Return structured error information
        return {
            'success': False,
            'error': str(e),
            'method': method,
            'args': str(args),
            'kwargs': str(kwargs),
            'execution_time': execution_time
        }

def patch_proxy_initialization():
    """
    Globally patch initialization methods to remove proxy arguments
    """
    try:
        import solana.rpc.api
        import solana.rpc.providers.http
        import httpx
        import functools
        
        def strip_proxy_kwargs(func):
            """
            Decorator to remove proxy-related arguments from any method
            """
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Remove common proxy-related arguments
                kwargs.pop('proxy', None)
                kwargs.pop('proxies', None)
                kwargs.pop('http_proxy', None)
                kwargs.pop('https_proxy', None)
                
                # Remove any other potential proxy arguments
                kwargs = {k: v for k, v in kwargs.items() 
                          if not any(proxy_key in k.lower() for proxy_key in ['proxy', 'proxies'])}
                
                return func(*args, **kwargs)
            return wrapper
        
        # Patch Client initialization methods
        original_client_init = httpx.Client.__init__
        httpx.Client.__init__ = strip_proxy_kwargs(original_client_init)
        
        # Patch Solana HTTP Provider initialization
        original_http_provider_init = solana.rpc.providers.http.HTTPProvider.__init__
        solana.rpc.providers.http.HTTPProvider.__init__ = strip_proxy_kwargs(original_http_provider_init)
        
        # Patch Solana Client initialization
        original_solana_client_init = solana.rpc.api.Client.__init__
        solana.rpc.api.Client.__init__ = strip_proxy_kwargs(original_solana_client_init)
        
        print("Successfully applied comprehensive proxy removal monkey patch")
        return True
    
    except Exception as e:
        print(f"Error applying proxy removal monkey patch: {e}")
        return False

def safe_get_block(client, block_number):
    """
    Safely retrieve a block with multiple fallback strategies
    
    Args:
        client: Solana RPC client
        block_number: Block number to retrieve
    
    Returns:
        Serializable block data or None
    """
    # List of possible retrieval strategies
    retrieval_strategies = [
        # Strategy 1: Basic block retrieval with max supported version
        lambda: client.get_block(
            block_number, 
            max_supported_transaction_version=0
        ),
        
        # Strategy 2: Remove transaction_details argument
        lambda: client.get_block(block_number, transaction_details=None)
    ]
    
    # Try each strategy
    for strategy in retrieval_strategies:
        try:
            block_resp = strategy()
            
            # Convert Solders response to serializable dict
            block = convert_block_to_dict(block_resp)
            
            # Validate block
            if block:
                print(f"Successfully retrieved block {block_number}")
                return block
        
        except Exception as e:
            print(f"Block retrieval strategy failed: {e}")
    
    # Final fallback
    print(f"All block retrieval strategies failed for block {block_number}")
    return None

def get_recent_blocks(client=None, **kwargs):
    """
    Retrieve recent blocks with robust error handling and data optimization
    
    Args:
        client: Solana RPC client
        **kwargs: Additional keyword arguments including 'limit'
    
    Returns:
        List of recent blocks with minimal, essential information
    """
    try:
        # Extract client and limit from kwargs
        if client is None:
            client = kwargs.get('client')
        
        # Default limit to 10 if not provided
        limit = kwargs.get('limit', 10)
        
        # Validate client
        if client is None:
            raise ValueError("No Solana RPC client provided")
        
        # Get current slot to determine block range
        current_slot = client.get_slot()
        
        # Calculate block range
        blocks = []
        for offset in range(limit):
            block_number = current_slot - offset
            
            # Attempt to retrieve block
            block = safe_get_block(client, block_number)
            
            if block is not None:
                blocks.append(block)
            
            # Stop if we've reached the desired limit
            if len(blocks) >= limit:
                break
        
        return blocks
    
    except Exception as e:
        print(f"Error retrieving recent blocks: {e}")
        return []

# Create FastAPI router
router = APIRouter(
    tags=["Soleco"],
    responses={404: {"description": "Not found"}},
)

# Initialize handlers
solana_query_handler = None
response_handler = None
network_handler = None
rpc_node_extractor = None

async def initialize_handlers():
    """Initialize connection pool and handlers."""
    global solana_query_handler, response_handler, network_handler, rpc_node_extractor
    
    try:
        logger.info("Initializing Solana handlers")
        
        # Get connection pool with error handling
        try:
            connection_pool = await get_connection_pool()
            if connection_pool is None:
                logger.error("Failed to get connection pool")
                return False
        except Exception as pool_error:
            logger.error(f"Error getting connection pool: {str(pool_error)}", exc_info=True)
            return False
        
        # Initialize the SolanaQueryHandler
        try:
            solana_query_handler = SolanaQueryHandler(connection_pool)
            # Ensure the handler is properly initialized
            if hasattr(solana_query_handler, 'ensure_initialized'):
                await solana_query_handler.ensure_initialized()
            logger.info("SolanaQueryHandler initialized successfully")
        except Exception as query_error:
            logger.error(f"Error initializing SolanaQueryHandler: {str(query_error)}", exc_info=True)
            return False
        
        # Create an EndpointConfig for the response manager
        from ..utils.solana_types import EndpointConfig
        default_endpoint_config = EndpointConfig(
            url="https://api.mainnet-beta.solana.com",
            requests_per_second=40.0,
            burst_limit=80,
            max_retries=3,
            retry_delay=1.0
        )
        
        # Create a SolanaResponseManager with the config
        try:
            response_manager = SolanaResponseManager(default_endpoint_config)
            # Initialize the ResponseHandler with the manager
            response_handler = ResponseHandler(response_manager)
            logger.info("ResponseHandler initialized successfully")
        except Exception as response_error:
            logger.error(f"Error initializing ResponseHandler: {str(response_error)}", exc_info=True)
            return False
        
        # Initialize the NetworkStatusHandler
        try:
            network_handler = NetworkStatusHandler(solana_query_handler)
            logger.info("NetworkStatusHandler initialized successfully")
        except Exception as network_error:
            logger.error(f"Error initializing NetworkStatusHandler: {str(network_error)}", exc_info=True)
            return False
        
        # Initialize the RPCNodeExtractor
        try:
            rpc_node_extractor = RPCNodeExtractor(solana_query_handler)
            logger.info("RPCNodeExtractor initialized successfully")
        except Exception as extractor_error:
            logger.error(f"Error initializing RPCNodeExtractor: {str(extractor_error)}", exc_info=True)
            return False
        
        logger.info("All Solana handlers initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Unexpected error during handler initialization: {str(e)}", exc_info=True)
        return False

from fastapi import Depends
from app.utils.cache.database_cache import DatabaseCache

def get_db_cache() -> DatabaseCache:
    return DatabaseCache()

@router.get("/network/status", summary="Solana Network Status")
async def get_network_status(
    summary_only: bool = Query(False, description="Return only the network summary without detailed node information"),
    refresh: bool = Query(False, description="Force refresh from Solana RPC"),
    db_cache: DatabaseCache = Depends(get_db_cache)
):
    """
    Retrieve comprehensive Solana network status with robust error handling.
    
    This endpoint provides a detailed overview of the current Solana network status,
    including health, node information, version distribution, and performance metrics.
    
    - **summary_only**: When true, returns only summary information without the detailed node list
    - **refresh**: When true, forces a refresh from the Solana RPC instead of using cached data
    """
    try:
        # Create cache key based on parameters
        params = {
            "summary_only": summary_only
        }
        
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data("network-status", params, NETWORK_STATUS_CACHE_TTL)
            if cached_data:
                logging.info("Retrieved network status from cache")
                return cached_data
        
        # Initialize handlers if needed
        if network_handler is None:
            initialization_success = await initialize_handlers()
            if not initialization_success or network_handler is None:
                return {
                    "status": "error",
                    "error": "Failed to initialize network status handler",
                    "timestamp": datetime.now(pytz.utc).isoformat()
                }
        
        # Get comprehensive network status
        result = await network_handler.get_comprehensive_status(summary_only=summary_only)
        
        # Cache the response
        db_cache.cache_data("network-status", result, params, NETWORK_STATUS_CACHE_TTL)
        
        return result
    except Exception as e:
        logger.error(f"Error retrieving network status: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(pytz.utc).isoformat(),
            "traceback": traceback.format_exc()
        }

@router.get("/token/{token_address}", response_model=Dict[str, Any])
async def get_token_info(
    token_address: str,
    refresh: bool = Query(False, description="Force refresh from Solana RPC"),
    db_cache: DatabaseCache = Depends(get_db_cache)
):
    params = {"token_address": token_address}
    cache_key = f"token_info:{token_address}"
    
    if not refresh:
        cached = await db_cache.get(cache_key)
        if cached:
            return cached
    
    try:
        if solana_query_handler is None:
            await initialize_handlers()
        token_info = await solana_query_handler.get_token_info(token_address)
        response = {
            "token_info": token_info,
            "timestamp": datetime.now(pytz.utc).isoformat()
        }
        await db_cache.set(cache_key, response)
        return response
    except Exception as e:
        logger.error(f"Error getting token info for {token_address}: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.get("/transaction/simulate", summary="Simulate Solana Transaction")
async def simulate_transaction(
    from_address: str = Query(..., description="Transaction sender's address"),
    to_address: str = Query(..., description="Transaction recipient's address"),
    amount: float = Query(..., description="Transaction amount"),
    token_address: Optional[str] = Query(None, description="Token contract address for token transfer")
):
    """
    Simulate a Solana transaction without actually executing it
    - Estimate transaction fees
    - Check transaction validity
    """
    try:
        # Get client from connection pool
        pool = await get_connection_pool()
        async with await pool.acquire() as client:
            from_pubkey = Pubkey.from_string(from_address)
            to_pubkey = Pubkey.from_string(to_address)
            
            # Create a mock transaction for simulation
            transaction = Transaction()
            # Add transaction instructions (simplified example)
            
            simulation_result = await safe_rpc_call_async(client, 'simulate_transaction', transaction)
        
            return {
                "from": from_address,
                "to": to_address,
                "amount": amount,
                "token_address": token_address,
                "simulation_result": simulation_result
            }
    except Exception as e:
        return {
            'error': 'Transaction simulation failed',
            'details': str(e),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now(pytz.utc).isoformat()
        }

@router.get("/wallet/{wallet_address}", summary="Analyze Solana Wallet")
async def analyze_wallet(
    wallet_address: str = Path(..., description="Wallet address to analyze")
) -> Dict[str, Any]:
    """
    Perform a comprehensive analysis of a Solana wallet
    - Token balances
    - Transaction history
    - Account health
    """
    try:
        # Get connection pool
        pool = await get_connection_pool()
        
        # Create query handler
        query_handler = solana_query_handler or SolanaQueryHandler(pool)
        
        # Get wallet transactions
        transactions = await query_handler.get_signatures_for_address(
            address=wallet_address,
            limit=100
        )
        
        # Get token program transactions
        token_txs = await query_handler.get_program_transactions(
            program_id=TOKEN_PROGRAM_ID,
            address=wallet_address,
            limit=100
        )
        
        # Get Token2022 program transactions
        token2022_txs = await query_handler.get_program_transactions(
            program_id=TOKEN_2022_PROGRAM_ID,
            address=wallet_address,
            limit=100
        )
        
        # Process wallet info
        wallet_info = {
            'address': wallet_address,
            'transactions': [],
            'token_holdings': {},
            'last_activity': None,
            'program_interactions': defaultdict(int)
        }
        
        # Process regular transactions
        for tx in transactions:
            signature = tx.get('signature', '')
            block_time = tx.get('blockTime', 0)
            
            wallet_info['transactions'].append({
                'signature': signature,
                'block_time': block_time,
                'type': 'regular'
            })
            
            # Update last activity
            if not wallet_info['last_activity'] or block_time > wallet_info['last_activity']:
                wallet_info['last_activity'] = block_time
                
        # Process token transactions
        for tx in token_txs:
            signature = tx.get('transaction', {}).get('signatures', [''])[0]
            block_time = tx.get('blockTime', 0)
            
            wallet_info['transactions'].append({
                'signature': signature,
                'block_time': block_time,
                'type': 'token'
            })
            wallet_info['program_interactions']['token'] += 1
            
        # Process Token2022 transactions
        for tx in token2022_txs:
            signature = tx.get('transaction', {}).get('signatures', [''])[0]
            block_time = tx.get('blockTime', 0)
            
            wallet_info['transactions'].append({
                'signature': signature,
                'block_time': block_time,
                'type': 'token2022'
            })
            wallet_info['program_interactions']['token2022'] += 1
            
        # Get SOL balance
        try:
            balance = await pool.get_client().get_balance(wallet_address)
            wallet_info['sol_balance'] = balance.value if balance else 0
        except Exception as e:
            logger.warning(f"Failed to get SOL balance: {str(e)}")
            wallet_info['sol_balance'] = None
            
        # Sort transactions by block time
        wallet_info['transactions'].sort(key=lambda x: x['block_time'], reverse=True)
        
        # Log query stats
        query_handler.stats.log_summary()
        
        return {
            'wallet_info': wallet_info,
            'query_stats': {
                'total_queries': query_handler.stats.total_queries,
                'error_queries': query_handler.stats.error_queries,
                'error_breakdown': dict(query_handler.stats.error_counts)
            }
        }
        
    except Exception as e:
        logger.error(f"Error analyzing wallet: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to analyze wallet',
                'message': str(e),
                'timestamp': datetime.now(pytz.utc).isoformat()
            }
        )

@router.get("/system/resources", summary="Get Solana System Resources")
async def get_system_resources():
    """
    Retrieve detailed Solana system resources and configuration
    - System program details
    - Sysvar information
    - Clock and epoch details
    """
    try:
        # Get client from connection pool
        pool = await get_connection_pool()
        async with await pool.acquire() as client:
            # Hardcoded system and sysvar addresses
            system_program_id = "11111111111111111111111111111111"
            clock_sysvar = "SysvarC1ock11111111111111111111111111111111"
            epoch_schedule_sysvar = "SysvarEpochSchedu1e111111111111111111111111"
            rent_sysvar = "SysvarRent111111111111111111111111111111111"
            
            # Retrieve Sysvar account info
            system_resources = {
                "system_program_id": system_program_id,
                "sysvars": {
                    "clock": await safe_rpc_call_async(client, 'get_account_info', clock_sysvar),
                    "epoch_schedule": await safe_rpc_call_async(client, 'get_account_info', epoch_schedule_sysvar),
                    "rent": await safe_rpc_call_async(client, 'get_account_info', rent_sysvar)
                },
                "epoch_info": await safe_rpc_call_async(client, 'get_epoch_info')
            }
            
            return system_resources
    
    except Exception as e:
        logger.error(f"System resources retrieval failed: {str(e)}")
        return {
            'error': 'System resources retrieval failed',
            'details': str(e),
            'timestamp': datetime.now(pytz.utc).isoformat(),
            'traceback': traceback.format_exc()
        }

@router.get("/performance/metrics", summary="Solana Performance Metrics")
async def get_performance_metrics(
    refresh: bool = Query(False, description="Force refresh from Solana RPC")
):
    """
    Retrieve current Solana network performance metrics
    - Transaction processing speed
    - Block production rate
    - Network congestion indicators
    - Summary statistics for both performance samples and block production
    """
    try:
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data("performance-metrics", None, PERFORMANCE_METRICS_CACHE_TTL)
            if cached_data:
                logging.info("Retrieved performance metrics from cache")
                return cached_data

        # Initialize handlers if needed
        if solana_query_handler is None:
            initialization_success = await initialize_handlers()
            if not initialization_success or solana_query_handler is None:
                return {
                    "status": "error",
                    "error": "Failed to initialize Solana query handler",
                    "timestamp": datetime.now(pytz.utc).isoformat()
                }
        
        # Get performance samples using the handler's method
        try:
            performance_samples = await solana_query_handler.get_recent_performance()
            logger.info(f"Retrieved {len(performance_samples) if performance_samples else 0} performance samples")
        except Exception as e:
            logger.error(f"Error getting performance samples: {str(e)}", exc_info=True)
            performance_samples = []
        
        # Get block production data
        block_production_response = None
        try:
            # Use the new get_block_production method that prioritizes Helius
            block_production_response = await solana_query_handler.get_block_production()
            logger.info(f"Retrieved block production data: {bool(block_production_response)}")
        except Exception as e:
            logger.error(f"Error getting block production: {str(e)}")
            block_production_response = {
                "error": str(e)
            }
        
        # Process performance samples
        performance_stats = {}
        if performance_samples and len(performance_samples) > 0:
            try:
                performance_stats = calculate_tps_statistics(performance_samples)
            except Exception as e:
                logger.error(f"Error processing performance samples: {str(e)}", exc_info=True)
                performance_stats = {
                    "error": str(e),
                    "samples_analyzed": len(performance_samples) if isinstance(performance_samples, list) else 0
                }
        else:
            # Try to get performance metrics from network status handler directly
            try:
                if network_handler:
                    metrics = await network_handler.get_performance_metrics()
                    if metrics and metrics.get('status') in ['success', 'cached'] and metrics.get('data_available', False):
                        logger.info("Using performance metrics from network status handler")
                        performance_stats = {
                            "current_tps": metrics.get('transactions_per_second', 0),
                            "max_tps": metrics.get('transactions_per_second', 0) * 1.1,  # Estimate
                            "min_tps": metrics.get('transactions_per_second', 0) * 0.9,  # Estimate
                            "average_tps": metrics.get('transactions_per_second', 0)
                        }
                    else:
                        logger.warning("No valid performance metrics from network status handler")
                        performance_stats = {
                            "error": "No performance samples available",
                            "samples_analyzed": 0,
                            "message": "Performance data not available from any RPC endpoint"
                        }
                else:
                    logger.warning("Network status handler not initialized")
                    performance_stats = {
                        "error": "No performance samples available",
                        "samples_analyzed": 0
                    }
            except Exception as e:
                logger.error(f"Error getting performance metrics from network status handler: {str(e)}", exc_info=True)
                performance_stats = {
                    "error": "No performance samples available",
                    "samples_analyzed": 0,
                    "exception": str(e)
                }
        
        # Process block production
        block_stats = {}
        try:
            if block_production_response and isinstance(block_production_response, dict):
                # Check if there's an error indicating method not supported
                if 'error' in block_production_response and isinstance(block_production_response['error'], dict):
                    error = block_production_response['error']
                    if error.get('code') == -32601 or "not supported" in error.get('message', '').lower():
                        logger.warning(f"Block production not supported by endpoint")
                        block_stats = {
                            "error": "Method not supported by endpoint",
                            "details": error.get('message', 'Unknown error')
                        }
                    else:
                        block_stats = {
                            "error": error.get('message', 'Unknown error'),
                            "details": str(error)
                        }
                elif 'result' in block_production_response and isinstance(block_production_response['result'], dict):
                    value = block_production_response.get('result', {}).get('value', {})
                    
                    if value:
                        # Extract block production stats
                        block_stats = {
                            "total_slots": value.get('total', 0),
                            "leader_slots": value.get('total', 0),
                            "blocks_produced": value.get('total', 0) - value.get('skippedSlots', 0),
                            "skipped_slots": value.get('skippedSlots', 0),
                            "skip_rate": value.get('skippedSlots', 0) / value.get('total', 1) if value.get('total', 0) > 0 else 0
                        }
                    else:
                        block_stats = {
                            "error": "Empty block production value",
                            "details": str(block_production_response)
                        }
                else:
                    block_stats = {
                        "error": "Invalid block production response format",
                        "details": str(block_production_response)
                    }
            else:
                block_stats = {
                    "error": "Invalid block production response",
                    "details": str(block_production_response)
                }
        except Exception as e:
            logger.error(f"Error processing block production: {str(e)}", exc_info=True)
            block_stats = {
                "error": str(e)
            }
        
        # Prepare response
        response = {
            "status": "success",
            "timestamp": datetime.now(pytz.utc).isoformat(),
            "performance_samples": performance_stats,
            "block_production": block_stats
        }
        
        # Add a status message if both performance samples and block production have errors
        if (isinstance(performance_stats, dict) and 'error' in performance_stats and 
            isinstance(block_stats, dict) and 'error' in block_stats):
            response["status_message"] = "Limited data available: Some Solana RPC methods are not supported by the available endpoints"
            
            # Log this situation for monitoring
            logger.warning(
                f"Limited performance data available: Performance samples error: {performance_stats.get('error')}, "
                f"Block production error: {block_stats.get('error')}"
            )
        
        # Cache the response
        try:
            db_cache.cache_data("performance-metrics", response, None, PERFORMANCE_METRICS_CACHE_TTL)
        except Exception as e:
            logger.error(f"Error caching performance metrics: {str(e)}", exc_info=True)
        
        return response
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(pytz.utc).isoformat(),
            "traceback": traceback.format_exc()
        }

@router.get("/network/rpc-nodes", summary="Get Available Solana RPC Nodes")
async def get_rpc_nodes(
    include_details: bool = Query(False, description="Include detailed information for each RPC node"),
    health_check: bool = Query(False, description="Perform health checks on a sample of RPC nodes"),
    include_all: bool = Query(False, description="Include all discovered RPC nodes, even those that may be unreliable"),
    refresh: bool = Query(False, description="Force refresh from Solana RPC")
):
    """
    Get a list of available Solana RPC nodes
    - Optionally includes detailed information about each node
    - Can perform health checks on a sample of nodes
    - Provides version distribution statistics
    """
    try:
        # Create cache key based on parameters
        params = {
            "include_details": include_details,
            "health_check": health_check,
            "include_all": include_all
        }
        
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data("rpc-nodes", params, RPC_NODES_CACHE_TTL)
            if cached_data:
                logging.info("Retrieved RPC nodes from cache")
                return cached_data
        
        # Initialize handlers if needed
        if solana_query_handler is None:
            initialization_success = await initialize_handlers()
            if not initialization_success or solana_query_handler is None:
                return {
                    "status": "error",
                    "error": "Failed to initialize Solana query handler",
                    "timestamp": datetime.now(pytz.utc).isoformat()
                }
        
        # Extract RPC nodes
        logger.info(f"Creating RPCNodeExtractor and extracting RPC nodes")
        start_time = time.time()
        
        try:
            extractor = RPCNodeExtractor(solana_query_handler)
            
            # Configure health check setting
            extractor.check_health = health_check
            
            # Get all RPC nodes first to check for errors
            all_nodes_result = await extractor.get_all_rpc_nodes()
            
            # In enhanced mode, we continue even if there are errors
            if not all_nodes_result.get("status") == "success":
                error_msg = all_nodes_result.get("error", "Unknown error retrieving cluster nodes")
                logger.error(f"Failed to get RPC nodes: {error_msg}")
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "status": "error",
                    "error": error_msg,
                    "timestamp": datetime.now(pytz.utc).isoformat(),
                    "execution_time_ms": execution_time_ms
                }
            
            # Extract RPC nodes
            rpc_nodes = await extractor.extract_rpc_nodes(include_all=include_all)
            extraction_time = time.time() - start_time
            logger.info(f"Extracted {len(rpc_nodes)} RPC nodes in {extraction_time:.2f} seconds")
            
            # Get any errors that were collected during extraction
            extraction_errors = extractor.get_errors()
            
        except Exception as extract_error:
            logger.error(f"Error during RPC node extraction: {str(extract_error)}", exc_info=True)
            execution_time_ms = int((time.time() - (start_time if 'start_time' in locals() else time.time())) * 1000)
            
            return {
                "status": "error",
                "error": f"Error extracting RPC nodes: {str(extract_error)}",
                "timestamp": datetime.now(pytz.utc).isoformat(),
                "execution_time_ms": execution_time_ms
            }
        
        # Check if we got any nodes
        if not rpc_nodes:
            logger.warning("No RPC nodes were extracted")
            execution_time_ms = int((time.time() - (start_time if 'start_time' in locals() else time.time())) * 1000)
            
            return {
                "status": "warning",
                "message": "No RPC nodes were found",
                "timestamp": datetime.now(pytz.utc).isoformat(),
                "execution_time_ms": execution_time_ms
            }
        
        # Count version distribution
        version_counts = {}
        for node in rpc_nodes:
            version = node.get("version", "unknown")
            version_counts[version] = version_counts.get(version, 0) + 1
        
        # Sort versions by count
        sorted_versions = sorted(version_counts.items(), key=lambda x: x[1], reverse=True)
        top_versions = sorted_versions[:5]  # Top 5 versions
        
        # Calculate version percentages
        total_nodes = len(rpc_nodes)
        version_distribution = [
            {
                "version": version,
                "count": count,
                "percentage": round((count / total_nodes) * 100, 2)
            }
            for version, count in top_versions
        ]
        
        # Calculate health statistics if health check was performed
        health_stats = {}
        if health_check:
            healthy_nodes = sum(1 for node in rpc_nodes if node.get("health", False))
            health_sample_size = sum(1 for node in rpc_nodes if "health" in node)
            if health_sample_size > 0:
                estimated_health_percentage = (healthy_nodes / health_sample_size) * 100
                health_stats = {
                    "healthy_nodes": healthy_nodes,
                    "health_sample_size": health_sample_size,
                    "estimated_health_percentage": estimated_health_percentage
                }
        
        # Prepare result
        result = {
            "status": "success",
            "timestamp": datetime.now(pytz.utc).isoformat(),
            "total_rpc_nodes": total_nodes,
            "version_distribution": version_distribution,
            "execution_time_ms": int(extraction_time * 1000)
        }
        
        # Add health statistics if available
        if health_stats:
            result.update(health_stats)
        
        # Add errors if there were any during extraction
        if extraction_errors:
            result["errors"] = extraction_errors
        
        # Add detailed node info if requested
        if include_details:
            # Sanitize node information to ensure it's JSON serializable
            sanitized_nodes = []
            for node in rpc_nodes:
                sanitized_node = {
                    "pubkey": node.get("pubkey", ""),
                    "rpc_endpoint": node.get("rpc_endpoint", ""),
                    "version": node.get("version", "unknown"),
                    "feature_set": node.get("feature_set", 0),
                    "gossip": node.get("gossip", ""),
                    "shred_version": node.get("shred_version", 0)
                }
                
                # Add health information if available
                if "health" in node:
                    sanitized_node["health"] = node["health"]
                    if not node["health"] and "health_error" in node:
                        sanitized_node["health_error"] = node["health_error"]
                
                sanitized_nodes.append(sanitized_node)
            
            result["rpc_nodes"] = sanitized_nodes
        
        # Cache the response
        try:
            # Make sure we're storing a JSON serializable object
            db_cache.cache_data("rpc-nodes", result, params, RPC_NODES_CACHE_TTL)
            logger.info("Cached RPC nodes data")
        except Exception as cache_error:
            logger.error(f"Error caching RPC nodes data: {str(cache_error)}")
        
        return result
    except Exception as e:
        logger.error(f"Error retrieving RPC nodes: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": f"Failed to retrieve cluster nodes: {str(e)}",
            "timestamp": datetime.now(pytz.utc).isoformat(),
            "execution_time_ms": int((time.time() - (start_time if 'start_time' in locals() else time.time())) * 1000)
        }

@router.get("/blocks/recent", summary="Retrieve Recent Solana Blocks")
async def retrieve_recent_blocks(limit: int = 10) -> Dict[str, Any]:
    """
    Retrieve recent Solana blocks
    
    Args:
        limit: Number of recent blocks to retrieve (default: 10)
    
    Returns:
        List of recent blocks with minimal, essential information
    """
    try:
        # Get connection pool
        connection_pool = await get_connection_pool()
        
        # Create a temporary query handler if needed
        query_handler = solana_query_handler or SolanaQueryHandler(connection_pool)
        
        # Get recent blocks
        blocks = await query_handler.get_recent_blocks(limit)
        
        # Process response
        resp_handler = response_handler or ResponseHandler()
        return resp_handler.process_blocks_response(blocks)
    except Exception as e:
        logger.error(f"Error retrieving recent blocks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to retrieve recent blocks',
                'message': str(e),
                'timestamp': datetime.now(pytz.utc).isoformat()
            }
        )

@router.get("/rpc/stats", response_model=Dict[str, Any], tags=["solana"])
async def get_rpc_stats():
    """
    Get detailed statistics about RPC endpoint performance.
    
    This endpoint provides detailed statistics about all RPC endpoints, including private endpoints with API keys.
    For a filtered view that excludes private endpoints, use the /network/solana/rpc/filtered-stats endpoint.
    
    Returns:
        Dict: Detailed statistics about each endpoint and summary metrics
    """
    from app.utils.solana_connection_pool import SolanaConnectionPool
    
    # Get or create the connection pool
    pool = SolanaConnectionPool()
    
    # Initialize the pool if not already initialized
    if not pool._initialized:
        await pool.initialize(DEFAULT_RPC_ENDPOINTS)
        
    # Get the stats
    stats = pool.get_rpc_stats()
    
    return stats

@router.get("/network/solana/rpc/filtered-stats", response_model=Dict[str, Any], tags=["solana"])
async def get_filtered_rpc_stats():
    """
    Get detailed statistics about RPC endpoint performance, excluding Helius endpoints and private endpoints with API keys.
    
    This endpoint provides the same information as the /rpc/stats endpoint but filters out
    any private endpoints with API keys for security reasons.
    
    Returns:
        Dict: Detailed statistics about each endpoint and summary metrics, with Helius endpoints and private endpoints filtered out
    """
    from ..utils.solana_rpc import get_connection_pool
    import logging
    
    # Get or create the connection pool
    pool = await get_connection_pool()
    
    # Initialize the pool if not already initialized
    if not pool._initialized:
        await pool.initialize(DEFAULT_RPC_ENDPOINTS)
        
    # Get the filtered stats directly from the connection pool
    stats = pool.get_filtered_rpc_stats()
    
    return stats

@router.get("/network/solana/rpc/test-fallback", response_model=Dict[str, Any], tags=["solana"])
async def test_fallback_endpoint():
    """
    Test endpoint that forces the use of a non-Helius fallback endpoint.
    
    This is for testing purposes only, to ensure that non-Helius endpoints are working correctly.
    
    Returns:
        Dict: Result of the RPC call using a non-Helius endpoint
    """
    from app.utils.solana_rpc import get_connection_pool, SolanaClient
    import logging
    import random
    
    # Get or create the connection pool
    pool = await get_connection_pool()
    
    # Initialize the pool if not already initialized
    if not pool._initialized:
        await pool.initialize(DEFAULT_RPC_ENDPOINTS)
    
    # Get a list of non-Helius endpoints
    non_helius_endpoints = [ep for ep in pool.endpoints if "helius" not in ep.lower()]
    
    if not non_helius_endpoints:
        return {"error": "No non-Helius endpoints available"}
    
    # Choose a random non-Helius endpoint
    endpoint = random.choice(non_helius_endpoints)
    
    # Create a client for this endpoint
    client = SolanaClient(
        endpoint=endpoint,
        timeout=pool.timeout,
        max_retries=pool.max_retries,
        retry_delay=pool.retry_delay
    )
    
    try:
        # Connect to the endpoint
        await client.connect()
        
        # Make a simple RPC call
        result = await client.get_version()
        
        # Update the stats for this endpoint
        pool._update_endpoint_stats(endpoint, success=True, latency=client.average_latency())
        
        return {
            "endpoint": endpoint,
            "result": result,
            "latency": client.average_latency(),
            "timestamp": datetime.now(pytz.utc).isoformat()
        }
    except Exception as e:
        # Update the stats for this endpoint
        pool._update_endpoint_stats(endpoint, success=False)
        
        return {
            "endpoint": endpoint,
            "error": str(e),
            "timestamp": datetime.now(pytz.utc).isoformat()
        }
    finally:
        # Close the client
        await client.close()

@router.get("/network/status-v2", response_model=Dict[str, Any])
async def get_network_status_v2(
    summary_only: bool = Query(False, description="Return only the network summary without detailed node information"),
    refresh: bool = Query(False, description="Force refresh from Solana RPC")
):
    """
    Retrieve comprehensive Solana network status with robust error handling.
    
    This endpoint provides a detailed overview of the current Solana network status,
    including health, node information, version distribution, and performance metrics.
    
    - **summary_only**: When true, returns only summary information without the detailed node list
    - **refresh**: When true, forces a refresh from the Solana RPC instead of using cached data
    
    Returns a JSON object containing:
    
    - **status**: Overall network health status (healthy, degraded, or unhealthy)
    - **errors**: Any errors encountered during data collection
    - **timestamp**: When the data was retrieved
    - **network_summary**: Summary statistics including:
      - **total_nodes**: Total number of nodes in the network
      - **rpc_nodes_available**: Number of nodes providing RPC services
      - **rpc_availability_percentage**: Percentage of nodes providing RPC services
      - **latest_version**: Latest Solana version detected in the network
      - **nodes_on_latest_version_percentage**: Percentage of nodes on the latest version
      - **version_distribution**: Distribution of node versions (top 5)
      - **total_versions_in_use**: Total number of different versions in use
      - **total_feature_sets_in_use**: Total number of different feature sets in use
    - **cluster_nodes**: Information about cluster nodes
    - **network_version**: Current network version information
    - **epoch_info**: Current epoch information
    - **performance_metrics**: Network performance metrics
    """
    try:
        # Check if we have cached data and refresh is not requested
        cache_key = f"network_status_{summary_only}"
        if not refresh:
            cached_data = db_cache.get(cache_key)
            if cached_data:
                logger.info(f"Using cached network status data (cache key: {cache_key})")
                return json.loads(cached_data)
        
        # Get network status
        status_handler = NetworkStatusHandler()
        initialization_success = await initialize_handlers()
        if not initialization_success or network_handler is None:
            return {
                "status": "error",
                "error": "Failed to initialize network status handler",
                "timestamp": datetime.now(pytz.utc).isoformat()
            }
        network_status = await network_handler.get_network_status(summary_only=summary_only)
        
        # Cache the result
        db_cache.set(cache_key, json.dumps(network_status), NETWORK_STATUS_CACHE_TTL)
        
        return network_status
    except Exception as e:
        logger.error(f"Error getting network status: {str(e)}")
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(pytz.utc).isoformat(),
            "traceback": traceback.format_exc()
        }

@router.get("/network/rpc-nodes-v2", response_model=Dict[str, Any])
async def get_rpc_nodes_v2(
    include_details: bool = Query(False, description="Include detailed information for each RPC node"),
    health_check: bool = Query(False, description="Perform health checks on a sample of RPC nodes"),
    include_all: bool = Query(False, description="Include all discovered RPC nodes, even those that may be unreliable"),
    refresh: bool = Query(False, description="Force refresh from Solana RPC")
):
    """
    Get a list of available Solana RPC nodes
    - Optionally includes detailed information about each node
    - Can perform health checks on a sample of nodes
    - Provides version distribution statistics
    """
    try:
        # Check if we have cached data and refresh is not requested
        cache_key = f"rpc_nodes_{include_details}_{health_check}_{include_all}"
        if not refresh:
            cached_data = db_cache.get(cache_key)
            if cached_data:
                logger.info(f"Using cached RPC nodes data (cache key: {cache_key})")
                try:
                    # Check if the cached data is a coroutine
                    if asyncio.iscoroutine(cached_data):
                        logger.warning("Cached data is a coroutine, awaiting it")
                        cached_data = await cached_data
                    
                    # Try to parse the cached data
                    if isinstance(cached_data, str):
                        return json.loads(cached_data)
                    elif isinstance(cached_data, dict):
                        return cached_data
                    else:
                        logger.warning(f"Unexpected cached data type: {type(cached_data)}, ignoring cache")
                except Exception as cache_error:
                    logger.error(f"Error processing cached data: {str(cache_error)}")
                    logger.warning("Ignoring cache due to error")
        
        # Initialize SolanaQueryHandler
        from app.utils.solana_query import SolanaQueryHandler
        query_handler = SolanaQueryHandler()
        initialization_success = await initialize_handlers()
        if not initialization_success or solana_query_handler is None:
            return {
                "status": "error",
                "error": "Failed to initialize Solana query handler",
                "timestamp": datetime.now(pytz.utc).isoformat()
            }
        
        # Extract RPC nodes
        from app.utils.handlers.rpc_node_extractor import RPCNodeExtractor
        extractor = RPCNodeExtractor(query_handler)
        rpc_nodes_data = await extractor.get_all_rpc_nodes()
        
        # Check if we got valid data
        if not rpc_nodes_data or not isinstance(rpc_nodes_data, dict) or 'rpc_nodes' not in rpc_nodes_data or not rpc_nodes_data['rpc_nodes']:
            logger.warning("No RPC nodes data returned from extractor")
            # Return default endpoints as a fallback
            from app.utils.solana_rpc_constants import DEFAULT_RPC_ENDPOINTS
            rpc_nodes_data = {
                "status": "warning",
                "message": "No cluster nodes returned from Solana network. Using default endpoints.",
                "timestamp": datetime.now(pytz.utc).isoformat(),
                "rpc_nodes": [{"endpoint": url, "is_default": True} for url in DEFAULT_RPC_ENDPOINTS]
            }
        
        # Ensure proper serialization of the response data
        from app.utils.solana_helpers import serialize_solana_object
        rpc_nodes_data = serialize_solana_object(rpc_nodes_data)
        
        # If include_all is False, filter out potentially unreliable nodes
        if not include_all and 'rpc_nodes' in rpc_nodes_data:
            # Filter to only include nodes with specific criteria
            filtered_nodes = [
                node for node in rpc_nodes_data['rpc_nodes']
                if node.get('feature_set', 0) > 0  # Must have a valid feature set
            ]
            rpc_nodes_data['rpc_nodes'] = filtered_nodes
            rpc_nodes_data['total_nodes'] = len(filtered_nodes)
        
        # Perform health checks if requested
        if health_check and 'rpc_nodes' in rpc_nodes_data:
            # Only check a sample of nodes to avoid overloading
            sample_size = min(5, len(rpc_nodes_data['rpc_nodes']))
            sample_nodes = random.sample(rpc_nodes_data['rpc_nodes'], sample_size) if rpc_nodes_data['rpc_nodes'] else []
            
            # Check health of sample nodes
            for node in sample_nodes:
                try:
                    endpoint = node['rpc_endpoint']
                    # Create a temporary client for this endpoint
                    temp_client = SolanaClient(endpoint=endpoint, timeout=5)
                    # Simple health check - get slot
                    start_time = time.time()
                    slot_response = await temp_client.get_slot()
                    response_time = time.time() - start_time
                    
                    # Update node with health info
                    node['health_check'] = {
                        'status': 'healthy' if 'result' in slot_response else 'error',
                        'response_time_ms': round(response_time * 1000, 2),
                        'timestamp': datetime.now(pytz.utc).isoformat()
                    }
                    
                    # Close the temporary client
                    await temp_client.close()
                except Exception as e:
                    # Mark node as unhealthy
                    node['health_check'] = {
                        'status': 'error',
                        'error': str(e),
                        'timestamp': datetime.now(pytz.utc).isoformat()
                    }
        
        # Include detailed information if requested
        if not include_details and 'rpc_nodes' in rpc_nodes_data:
            # Simplify the response by only including essential fields
            simplified_nodes = []
            for node in rpc_nodes_data['rpc_nodes']:
                simplified_node = {
                    'rpc_endpoint': node['rpc_endpoint'],
                    'version': node.get('version', 'unknown')
                }
                if health_check and 'health_check' in node:
                    simplified_node['health_check'] = node['health_check']
                simplified_nodes.append(simplified_node)
            rpc_nodes_data['rpc_nodes'] = simplified_nodes
        
        # Cache the result
        try:
            # Make sure we're storing a JSON serializable object
            if isinstance(rpc_nodes_data, dict):
                cache_data = json.dumps(rpc_nodes_data)
                await db_cache.set(cache_key, cache_data, RPC_NODES_CACHE_TTL)
                logger.info(f"Cached RPC nodes data (cache key: {cache_key})")
            else:
                logger.warning(f"Cannot cache data of type {type(rpc_nodes_data)}")
        except Exception as cache_error:
            logger.error(f"Error caching RPC nodes data: {str(cache_error)}")
        
        return rpc_nodes_data
    except Exception as e:
        logger.error(f"Error getting RPC nodes: {str(e)}")
        traceback.print_exc()
        error_msg = str(e)
        if "coroutine" in error_msg:
            logger.error("Detected coroutine error. Ensure all async functions are properly awaited.")
            return {
                "status": "error",
                "error": "Coroutine error detected. This is likely due to an async function not being properly awaited.",
                "details": error_msg,
                "timestamp": datetime.now(pytz.utc).isoformat(),
                "rpc_nodes": []
            }
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(pytz.utc).isoformat(),
            "traceback": traceback.format_exc(),
            "rpc_nodes": []
        }

def calculate_tps_statistics(samples):
    """Calculate TPS statistics from performance samples"""
    if not samples:
        return {
            "current_tps": 0,
            "max_tps": 0,
            "min_tps": 0,
            "average_tps": 0
        }
    
    # Check if the first sample contains an error message
    if len(samples) == 1 and 'error' in samples[0]:
        logger.warning(f"Performance samples contain error: {samples[0]['error']}")
        return {
            "current_tps": 0,
            "max_tps": 0,
            "min_tps": 0,
            "average_tps": 0,
            "error": samples[0]['error'],
            "endpoints_tried": samples[0].get('endpoints_tried', 0),
            "timestamp": samples[0].get('timestamp', 0)
        }
    
    # Extract TPS values
    tps_values = []
    for sample in samples:
        num_transactions = sample.get("numTransactions", 0)
        sample_period_secs = sample.get("samplePeriodSecs", 1)
        if sample_period_secs > 0:
            tps = num_transactions / sample_period_secs
            tps_values.append(tps)
    
    if not tps_values:
        return {
            "current_tps": 0,
            "max_tps": 0,
            "min_tps": 0,
            "average_tps": 0
        }
    
    return {
        "current_tps": round(tps_values[0], 2),
        "max_tps": round(max(tps_values), 2),
        "min_tps": round(min(tps_values), 2),
        "average_tps": round(sum(tps_values) / len(tps_values), 2)
    }

def process_block_production(block_production):
    """Process block production data"""
    if "error" in block_production or "result" not in block_production:
        return {
            "total_blocks": 0,
            "total_slots": 0,
            "current_slot": 0,
            "leader_slots": 0,
            "blocks_produced": 0,
            "skipped_slots": 0,
            "skipped_slot_percentage": 0
        }
    
    result = block_production.get("result", {})
    value = result.get("value", {})
    
    # Extract statistics
    total_slots = 0
    leader_slots = 0
    blocks_produced = 0
    
    by_identity = value.get("byIdentity", {})
    for identity, stats in by_identity.items():
        leader_slots += stats[0]
        blocks_produced += stats[1]
    
    total_slots = value.get("range", {}).get("totalSlots", 0)
    skipped_slots = leader_slots - blocks_produced
    skipped_slot_percentage = (skipped_slots / leader_slots * 100) if leader_slots > 0 else 0
    
    return {
        "total_blocks": blocks_produced,
        "total_slots": total_slots,
        "current_slot": value.get("range", {}).get("lastSlot", 0),
        "leader_slots": leader_slots,
        "blocks_produced": blocks_produced,
        "skipped_slots": skipped_slots,
        "skipped_slot_percentage": round(skipped_slot_percentage, 2)
    }

@router.get("/network-status", response_model=Dict[str, Any])
async def get_network_status():
    """
    Get comprehensive information about the Solana network status.
    
    Returns:
        Dict with network status information including:
        - node_count: Total number of nodes
        - active_nodes: Number of active nodes
        - delinquent_nodes: Number of delinquent nodes
        - version_distribution: Distribution of node versions
        - feature_set_distribution: Distribution of feature sets
        - stake_distribution: Distribution of stake among validators
        - errors: Any errors encountered during data collection
        - status: Overall network status (healthy, degraded, or unhealthy)
    """
    try:
        solana_query = SolanaQuery()
        network_status = await solana_query.get_network_status()
        return network_status
    except Exception as e:
        logging.error(f"Error in network status endpoint: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to retrieve network status: {str(e)}",
            "timestamp": datetime.now(pytz.utc).isoformat()
        }

@router.get("/enhanced-network-status", response_model=Dict[str, Any], tags=["solana"])
async def get_enhanced_network_status(
    refresh: bool = False,
):
    """
    Get enhanced network status with robust error handling and comprehensive metrics.
    
    This endpoint provides detailed information about the Solana network status,
    including node counts, version distribution, feature set distribution, and stake distribution.
    It includes robust error handling and will attempt multiple fallback mechanisms to ensure
    that some data is always returned, even in error conditions.
    
    Args:
        refresh: Whether to force a refresh of the cached data
        
    Returns:
        Dict with network status information
    """
    # Initialize result structure
    result = {
        "status": "unknown",
        "data_source": "unknown",
        "timestamp": datetime.now(pytz.utc).isoformat(),
        "execution_time_ms": 0,
        "errors": [],
        "node_count": 0,
        "active_nodes": 0,
        "delinquent_nodes": 0,
        "version_distribution": {},
        "feature_set_distribution": {},
        "stake_distribution": {}
    }
    
    # Track all errors for comprehensive error reporting
    all_errors = []
    
    # Track execution time
    start_time = time.time()
    logging.info("Retrieving enhanced network status")
    
    # Define fallback function
    async def _try_fallback_network_status(result_dict, errors_list):
        try:
            logger.info("Attempting fallback network status retrieval using RPCNodeExtractor")
            extractor = RPCNodeExtractor()
            fallback_data = await extractor.get_network_status()
            
            # Update result with fallback data
            result_dict.update(fallback_data)
            result_dict["data_source"] = "fallback_rpc_node_extractor"
            
            # Add a note about using fallback
            if "notes" not in result_dict:
                result_dict["notes"] = []
            result_dict["notes"].append("Used fallback mechanism due to primary method failure")
            
            logger.info("Successfully retrieved network status using fallback method")
        except Exception as e:
            logger.error(f"Error in fallback network status method: {str(e)}", exc_info=True)
            errors_list.append({
                'source': 'fallback_method',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
    
    # Try primary method first
    try:
        # Use cached connection pool if available
        pool = await get_connection_pool()
        query_handler = SolanaQueryHandler(connection_pool=pool)
        
        # Get network status
        network_status = await query_handler.get_network_status()
        
        # Update result with network status data
        if network_status:
            result.update(network_status)
            result["data_source"] = "primary_solana_query_handler"
        else:
            # If primary method returns None or empty data, try fallback
            await _try_fallback_network_status(result, all_errors)
    except Exception as e:
        logger.error(f"Error in primary network status method: {str(e)}", exc_info=True)
        all_errors.append({
            'source': 'primary_method',
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        
        # Try fallback method
        await _try_fallback_network_status(result, all_errors)
    
    # Calculate execution time
    end_time = time.time()
    execution_time_ms = int((end_time - start_time) * 1000)
    result["execution_time_ms"] = execution_time_ms
    
    # Add all collected errors to the result
    if all_errors:
        result["errors"] = all_errors
    
    # Cache the result
    cache_data("enhanced_network_status", result, NETWORK_STATUS_CACHE_TTL)
    
    return result

@router.get("/token/{token_address}", response_model=Dict[str, Any])
async def get_token_info(
    token_address: str,
    refresh: bool = Query(False, description="Force refresh from Solana RPC"),
    db_cache: DatabaseCache = Depends(get_db_cache)
):
    params = {"token_address": token_address}
    cache_key = f"token_info:{token_address}"
    
    if not refresh:
        cached = await db_cache.get(cache_key)
        if cached:
            return cached
    
    token_info = await get_token_info_from_rpc(token_address)
    response = {
        "token_info": token_info,
        "timestamp": datetime.now(pytz.utc).isoformat()
    }
    await db_cache.set(cache_key, response)
    return response

@router.get("/token/{token_address}", response_model=Dict[str, Any])
async def get_token_info(
    token_address: str,
    refresh: bool = Query(False, description="Force refresh from Solana RPC"),
    db_cache: DatabaseCache = Depends(get_db_cache)
):
    params = {"token_address": token_address}

    if not refresh:
        cached_data = await db_cache.get_cached_data("token-info", params, TOKEN_INFO_CACHE_TTL)
        if cached_data:
            return cached_data

    try:
        if solana_query_handler is None:
            await initialize_handlers()
        token_info = await solana_query_handler.get_token_info(token_address)
        response = {
            "token_info": token_info,
            "timestamp": datetime.now(pytz.utc).isoformat()
        }
        await db_cache.set_cached_data("token-info", params, response)
        return response
    except Exception as e:
        logger.error(f"Error getting token info for {token_address}: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.get("/token/{token_address}", response_model=Dict[str, Any])
async def get_token_info(
    token_address: str,
    refresh: bool = Query(False, description="Force refresh from Solana RPC"),
    db_cache: DatabaseCache = Depends(get_db_cache)
):
    params = {"token_address": token_address}

    if not refresh:
        cached_data = await db_cache.get_cached_data("token-info", params, TOKEN_INFO_CACHE_TTL)
        if cached_data:
            return cached_data

    try:
        if solana_query_handler is None:
            await initialize_handlers()
        token_info = await solana_query_handler.get_token_info(token_address)
        response = {
            "token_info": token_info,
            "timestamp": datetime.now(pytz.utc).isoformat()
        }
        await db_cache.set_cached_data("token-info", params, response)
        return response
    except Exception as e:
        logger.error(f"Error getting token info for {token_address}: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.get('/health/endpoints', response_model=List[Dict[str, Any]], tags=["solana", "health"])
async def get_endpoints_health_status():
    """Get health status of all RPC endpoints"""
    from ..utils.solana_helpers import get_endpoints_health
    return await get_endpoints_health()

@router.get('/health/endpoints/{endpoint}', response_model=Dict[str, Any], tags=["solana", "health"])
async def get_endpoint_health_detail(endpoint: str):
    """Get detailed health status for specific endpoint"""
    from ..utils.solana_helpers import get_endpoint_health_detail
    return await get_endpoint_health_detail(endpoint)

# RPC pool management endpoints
@router.get("/rpc-pool/status", response_model=Dict[str, Any], tags=["solana", "rpc"])
async def get_rpc_pool_status_endpoint():
    """Get current RPC pool status"""
    from ..utils.solana_helpers import get_rpc_pool_status
    return await get_rpc_pool_status()

@router.post("/rpc-pool/rotate", response_model=Dict[str, Any], tags=["solana", "rpc"])
async def rotate_rpc_endpoint_endpoint():
    """Force rotation to next endpoint"""
    from ..utils.solana_helpers import rotate_rpc_endpoint
    return await rotate_rpc_endpoint()

@router.get("/rpc-pool/endpoints", response_model=List[Dict[str, Any]], tags=["solana", "rpc"])
async def get_available_endpoints_endpoint():
    """List available endpoints"""
    from ..utils.solana_helpers import get_rpc_endpoints
    return await get_rpc_endpoints()

# Network performance metrics endpoints
@router.get("/metrics/tps", response_model=Dict[str, Any], tags=["solana", "metrics"])
async def get_tps_metrics_endpoint():
    """Get current transactions per second"""
    from ..utils.solana_helpers import get_tps_metrics
    return await get_tps_metrics()

@router.get("/metrics/blocktime", response_model=Dict[str, Any], tags=["solana", "metrics"])
async def get_block_time_metrics_endpoint():
    """Get average block time"""
    from ..utils.solana_helpers import get_block_time_metrics
    return await get_block_time_metrics()

# Advanced analytics endpoints
@router.get("/analytics/token-mints", response_model=Dict[str, Any], tags=["solana", "analytics"])
async def get_token_mints_analytics_endpoint():
    """Get analytics for new token mints"""
    from ..utils.solana_helpers import get_token_mints_analytics
    return await get_token_mints_analytics()

@router.get("/analytics/pump-tokens", response_model=Dict[str, Any], tags=["solana", "analytics"])
async def get_pump_token_data_endpoint():
    """Get pump token tracking data"""
    from ..utils.solana_helpers import get_pump_token_data
    return await get_pump_token_data()

@router.get("/analytics/dex-activity", response_model=Dict[str, Any], tags=["solana", "analytics"])
async def get_dex_activity_data_endpoint():
    """Get DEX trading activity"""
    from ..utils.solana_helpers import get_dex_activity_data
    return await get_dex_activity_data()
