"""
Solana router module for handling Solana blockchain interactions
"""
from typing import Dict, List, Optional, Any, Union
import traceback
from fastapi import APIRouter, HTTPException, Query, Path
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.system_program import ID as SYSTEM_PROGRAM_ID
import time
import logging
import json
from datetime import datetime, timezone
from collections import defaultdict
import asyncio

from ..utils.solana_rpc import (
    SolanaConnectionPool, 
    get_connection_pool,
    SolanaClient,
    create_robust_client
)
from ..utils.solana_errors import RetryableError, RPCError
from ..utils.solana_query import SolanaQueryHandler
from ..utils.solana_response import (
    MintHandler,
    ResponseHandler,
    SolanaResponseManager
)
from ..utils.handlers.network_status_handler import NetworkStatusHandler
from ..utils.handlers.rpc_node_extractor import RPCNodeExtractor
from ..utils.solana_connection_pool import performance_cache

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
            'traceback': traceback.format_exc(),
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
    prefix="/solana",
    tags=["Soleco"],
    responses={404: {"description": "Not found"}}
)

# Initialize handlers
solana_query_handler = None
response_handler = None
network_handler = None
rpc_node_extractor = None

async def initialize_handlers():
    """Initialize connection pool and handlers."""
    global solana_query_handler, response_handler, network_handler, rpc_node_extractor
    if solana_query_handler is None:
        connection_pool = await get_connection_pool()
        solana_query_handler = SolanaQueryHandler(connection_pool)
        
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
        response_manager = SolanaResponseManager(default_endpoint_config)
        
        # Initialize the ResponseHandler with the manager
        response_handler = ResponseHandler(response_manager)
        
        network_handler = NetworkStatusHandler(solana_query_handler)
        rpc_node_extractor = RPCNodeExtractor(solana_query_handler)
        logger.info("Initialized Solana handlers")

@router.get("/network/status", summary="Get Comprehensive Solana Network Status", tags=["Soleco"])
async def get_network_status(
    summary_only: bool = Query(False, description="Return only the network summary without detailed node information")
) -> Dict[str, Any]:
    """
    Retrieve comprehensive Solana network status with robust error handling.
    
    This endpoint provides a detailed overview of the current Solana network status,
    including health, node information, version distribution, and performance metrics.
    
    - **summary_only**: When true, returns only summary information without the detailed node list
    
    Returns a JSON object containing:
    
    - **status**: Overall network health status (healthy, degraded, error)
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
        # Initialize handlers if needed
        await initialize_handlers()

        # Get comprehensive status
        status_data = await network_handler.get_comprehensive_status()
        
        # If summary_only is True, remove the detailed node list
        if summary_only and 'cluster_nodes' in status_data and 'nodes' in status_data['cluster_nodes']:
            # Save the total nodes count
            total_nodes = status_data['cluster_nodes']['total_nodes']
            # Remove the detailed node list
            status_data['cluster_nodes'].pop('nodes', None)
            # Ensure total_nodes is still present
            status_data['cluster_nodes']['total_nodes'] = total_nodes
            
        return status_data
    
    except Exception as e:
        logger.error(f"Error retrieving network status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to retrieve network status',
                'message': str(e)
            }
        )

@router.get("/token/{token_address}", summary="Get SPL Token Information")
async def get_token_info(
    token_address: str = Path(..., description="SPL Token contract address"),
    wallet_address: Optional[str] = Query(None, description="Wallet address to check token balance")
) -> Dict[str, Any]:
    """
    Retrieve comprehensive SPL Token information with robust error handling
    
    Args:
        token_address: Contract address of the token
        wallet_address: Optional wallet address to check balance
    
    Returns:
        Dict: Detailed token information
    """
    try:
        # Get connection pool
        pool = await get_connection_pool()
        
        # Create query handler
        query_handler = SolanaQueryHandler(pool)
        
        # Get token transactions
        token_txs = await query_handler.get_program_transactions(
            program_id=TOKEN_PROGRAM_ID,
            address=token_address,
            limit=100
        )
        
        # Process token info
        token_info = {
            'address': token_address,
            'transactions': [],
            'holders': set(),
            'total_volume': 0,
            'last_activity': None
        }
        
        for tx in token_txs:
            # Extract transaction info
            signature = tx.get('transaction', {}).get('signatures', [''])[0]
            block_time = tx.get('blockTime', 0)
            
            # Update token info
            token_info['transactions'].append({
                'signature': signature,
                'block_time': block_time,
                'type': tx.get('type', 'unknown')
            })
            
            # Update last activity
            if not token_info['last_activity'] or block_time > token_info['last_activity']:
                token_info['last_activity'] = block_time
                
        # Get wallet balance if requested
        if wallet_address:
            try:
                balance = await pool.get_client().get_token_account_balance(wallet_address)
                token_info['wallet_balance'] = balance.value.amount if balance else 0
            except Exception as e:
                logger.warning(f"Failed to get wallet balance: {str(e)}")
                token_info['wallet_balance'] = None
                
        # Log query stats
        query_handler.stats.log_summary()
        
        return {
            'token_info': token_info,
            'query_stats': {
                'total_queries': query_handler.stats.total_queries,
                'error_queries': query_handler.stats.error_queries,
                'error_breakdown': dict(query_handler.stats.error_counts)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting token info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get token info: {str(e)}"
        )

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
            'traceback': traceback.format_exc()
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
        query_handler = SolanaQueryHandler(pool)
        
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
            detail=f"Failed to analyze wallet: {str(e)}"
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
            'traceback': traceback.format_exc()
        }

@router.get("/validators/analysis", summary="Analyze Solana Validator Network")
async def analyze_validator_network():
    """
    Perform comprehensive analysis of the Solana validator network
    
    Returns:
        Dict: Detailed validator network insights
    """
    try:
        # Get client from connection pool
        pool = await get_connection_pool()
        async with await pool.acquire() as client:
            # Retrieve validator information
            cluster_nodes_result = await safe_rpc_call_async(client, 'get_cluster_nodes')
            
            # Validate and process cluster nodes
            if not cluster_nodes_result.get('success', False):
                raise ValueError("Failed to retrieve cluster nodes")
            
            # Analyze validator network
            validator_analysis = {
                'total_nodes': len(cluster_nodes_result.get('result', [])),
                'node_details': cluster_nodes_result.get('result', []),
                'epoch_info': await safe_rpc_call_async(client, 'get_epoch_info')
            }
            
            return validator_analysis
    
    except Exception as e:
        logger.error(f"Validator network analysis failed: {str(e)}")
        return {
            'error': 'Validator network analysis failed',
            'details': str(e),
            'traceback': traceback.format_exc()
        }

@router.get("/program/registry", summary="Get Solana Program Registry")
async def get_program_registry():
    """
    Get a registry of core Solana programs
    
    Returns:
        Dict: Program registry with account information
    """
    try:
        # Get client from connection pool
        pool = await get_connection_pool()
        async with await pool.acquire() as client:
            system_program_id = "11111111111111111111111111111111"
            stake_program_id = "Stake11111111111111111111111111111111111111"
            vote_program_id = "Vote111111111111111111111111111111111111111"
            
            # Retrieve program information
            program_registry = {
                "system_program": {
                    "id": system_program_id,
                    "account_info": await safe_rpc_call_async(client, 'get_account_info', system_program_id)
                },
                "stake_program": {
                    "id": stake_program_id,
                    "account_info": await safe_rpc_call_async(client, 'get_account_info', stake_program_id)
                },
                "vote_program": {
                    "id": vote_program_id,
                    "account_info": await safe_rpc_call_async(client, 'get_account_info', vote_program_id)
                }
            }
            
            return program_registry
        
    except Exception as e:
        logger.error(f"Program registry retrieval failed: {str(e)}")
        return {
            'error': 'Program registry retrieval failed',
            'details': str(e),
            'traceback': traceback.format_exc()
        }

@router.get("/performance/metrics", summary="Solana Performance Metrics")
async def get_performance_metrics():
    """
    Retrieve current Solana network performance metrics
    - Transaction processing speed
    - Block production rate
    - Network congestion indicators
    - Summary statistics for both performance samples and block production
    """
    try:
        # Check cache first
        cached_result = performance_cache.get("performance_metrics")
        if cached_result:
            logger.info("Returning cached performance metrics")
            return cached_result
            
        # Create a robust client
        client = await create_robust_client()
        
        # Get recent performance samples
        try:
            performance_samples = await client.get_recent_performance_samples(20)
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        if not performance_samples or isinstance(performance_samples, dict) and "error" in performance_samples:
            return {
                "status": "error",
                "error": "Failed to retrieve performance samples",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        samples = performance_samples.get("result", [])
        
        # Calculate TPS statistics
        tps_stats = calculate_tps_statistics(samples)
        
        # Get recent block production info
        block_production = await safe_rpc_call_async(
            client,
            "get_block_production"
        )
        
        # Process block production data
        block_stats = process_block_production(block_production)
        
        # Combine all metrics
        result = {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "performance_samples": samples[:5],  # Only return the 5 most recent samples
            "tps_statistics": tps_stats,
            "block_production_statistics": block_stats
        }
        
        # Cache the result
        performance_cache.set("performance_metrics", result)
        
        return result
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
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

@router.get("/network/rpc-nodes", summary="Get Available Solana RPC Nodes", tags=["Soleco"])
async def get_rpc_nodes(
    include_details: bool = Query(False, description="Include detailed information for each RPC node"),
    health_check: bool = Query(False, description="Perform health checks on a sample of RPC nodes")
):
    """
    Extract and analyze available RPC nodes from the Solana network.
    
    This endpoint provides information about RPC nodes available on the Solana network,
    including their count, version distribution, and optionally their health status.
    
    - **include_details**: When true, includes the full list of RPC nodes with their details
    - **health_check**: When true, performs health checks on a sample of RPC nodes
    
    Returns a JSON object containing:
    
    - **status**: Success or error status
    - **timestamp**: When the data was retrieved
    - **total_rpc_nodes**: Total number of RPC nodes found
    - **version_distribution**: Distribution of node versions (top 5)
    - **health_sample_size**: Number of nodes sampled for health check (if requested)
    - **estimated_health_percentage**: Percentage of healthy nodes in sample (if requested)
    - **rpc_nodes**: Array of RPC node details (if requested)
    
    Each RPC node object contains:
    - **pubkey**: The node's public key
    - **rpc_endpoint**: The RPC endpoint URL/address
    - **version**: The node's Solana version
    - **feature_set**: The node's feature set
    """
    try:
        # Initialize handlers if needed
        await initialize_handlers()
        
        # Get RPC nodes
        result = await rpc_node_extractor.get_all_rpc_nodes()
        
        # If details are not requested, remove the full node list
        if not include_details and 'rpc_nodes' in result:
            result.pop('rpc_nodes', None)
            
        # If health check is not requested, remove health-related fields
        if not health_check:
            result.pop('health_sample_size', None)
            result.pop('estimated_health_percentage', None)
            
        return result
    except Exception as e:
        logger.error(f"Error retrieving RPC nodes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to retrieve RPC nodes',
                'message': str(e)
            }
        )

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
                'message': str(e)
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
        await pool.initialize()
        
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
    from app.utils.solana_rpc import get_connection_pool
    import logging
    
    # Get or create the connection pool
    pool = await get_connection_pool()
    
    # Initialize the pool if not already initialized
    if not pool._initialized:
        await pool.initialize()
        
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
        await pool.initialize()
    
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
            "latency": client.average_latency()
        }
    except Exception as e:
        # Update the stats for this endpoint
        pool._update_endpoint_stats(endpoint, success=False)
        
        return {
            "endpoint": endpoint,
            "error": str(e)
        }
    finally:
        # Close the client
        await client.close()

@router.get("/network/rpc-nodes", summary="Get Available Solana RPC Nodes", tags=["Soleco"])
async def get_rpc_nodes(
    include_details: bool = Query(False, description="Include detailed information for each RPC node"),
    health_check: bool = Query(False, description="Perform health checks on a sample of RPC nodes"),
    include_all: bool = Query(False, description="Include all discovered RPC nodes, even those that may be unreliable")
):
    """
    Get a list of available Solana RPC nodes
    - Optionally includes detailed information about each node
    - Can perform health checks on a sample of nodes
    - Provides version distribution statistics
    """
    try:
        # Check cache first
        cache_key = f"rpc_nodes_{include_details}_{health_check}_{include_all}"
        cached_result = rpc_nodes_cache.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached RPC nodes data for key: {cache_key}")
            return cached_result
            
        # Create RPC node extractor
        rpc_node_extractor = RPCNodeExtractor()
        
        # Get RPC nodes
        result = await rpc_node_extractor.get_all_rpc_nodes(
            include_details=include_details,
            health_check=health_check,
            include_all=include_all
        )
        
        # Cache the result
        rpc_nodes_cache.set(cache_key, result)
        
        return result
    except Exception as e:
        logger.error(f"Error retrieving RPC nodes: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@router.get("/network/status")
async def get_network_status(
    summary_only: bool = Query(False, description="Return only the network summary without detailed node information")
):
    """
    Retrieve comprehensive Solana network status with robust error handling.
    
    This endpoint provides a detailed overview of the current Solana network status,
    including health, node information, version distribution, and performance metrics.
    
    - **summary_only**: When true, returns only summary information without the detailed node list
    
    Returns a JSON object containing:
    
    - **status**: Overall network health status (healthy, degraded, error)
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
        # Initialize network status handler
        handler = NetworkStatusHandler()
        
        # Get network status
        status_data = await handler.get_network_status(summary_only=summary_only)
        
        return status_data
    except Exception as e:
        logger.error(f"Error retrieving network status: {str(e)}")
        return {
            "status": "error",
            "errors": [str(e)],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Failed to retrieve network status"
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
