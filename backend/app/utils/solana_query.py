"""
Solana query module for handling blockchain data queries.
This module provides query handlers and utilities for fetching and processing Solana blockchain data.
"""

from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import asyncio
import time
import json
import logging
import traceback

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.rpc.responses import *
from solders.commitment_config import CommitmentConfig

from .solana_rpc import SolanaConnectionPool, get_connection_pool, SolanaClient
from .solana_helpers import (
    transform_transaction_data,
    get_block_options,
    handle_rpc_error,
    DEFAULT_COMMITMENT,
    safe_rpc_call_async
)
from .solana_error import (
    SolanaError,
    RPCError,
    NodeBehindError,
    SlotSkippedError,
    MissingBlocksError,
    NodeUnhealthyError,
    RateLimitError,
    TransactionError,
    MissingTransactionDataError,
    InvalidInstructionError,
    RetryableError,
    MethodNotSupportedError
)
from .handlers.base_handler import BaseHandler
from .handlers.mint_handler import MintHandler
from .handlers.pump_handler import PumpHandler
from .handlers.nft_handler import NFTHandler
from .handlers.instruction_handler import InstructionHandler
from .handlers.block_handler import BlockHandler

logger = logging.getLogger(__name__)

class SolanaQueryHandler:
    """Handles Solana blockchain queries with connection pooling and error handling."""
    
    def __init__(self, connection_pool=None):
        """
        Initialize the query handler.
        
        Args:
            connection_pool: Optional connection pool, will create new one if not provided
        """
        self.connection_pool = connection_pool
        self.initialized = False
        
    async def ensure_initialized(self):
        """Ensure the handler is initialized."""
        if not self.initialized:
            if not self.connection_pool:
                self.connection_pool = await get_connection_pool()
            
            # Check if the connection pool is already initialized
            if hasattr(self.connection_pool, '_initialized') and self.connection_pool._initialized:
                self.initialized = True
                return
                
            # Initialize the connection pool
            try:
                # First try without arguments (newer implementation)
                await self.connection_pool.initialize()
            except TypeError as e:
                # If it fails with TypeError, it might be the older implementation that requires endpoints
                if "missing 1 required positional argument: 'endpoints'" in str(e):
                    logger.info("Connection pool requires endpoints argument, using alternative initialization")
                    # Get endpoints from the pool or use defaults
                    if hasattr(self.connection_pool, 'endpoints') and self.connection_pool.endpoints:
                        await self.connection_pool.initialize(self.connection_pool.endpoints)
                    else:
                        from app.utils.solana_rpc import DEFAULT_RPC_ENDPOINTS
                        await self.connection_pool.initialize(DEFAULT_RPC_ENDPOINTS)
                else:
                    # If it's a different TypeError, re-raise it
                    raise
            
            self.initialized = True
            
    async def initialize(self):
        """Initialize the handler and its components."""
        await self.ensure_initialized()
        try:
            # Initialize handlers
            self.handlers = {
                'base': BaseHandler(),
                'mint': MintHandler(),
                'pump': PumpHandler(),
                'nft': NFTHandler(),
                'instruction': InstructionHandler(),
                'block': BlockHandler()
            }
            
            logger.info("SolanaQueryHandler initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing SolanaQueryHandler: {str(e)}")
            raise
            
    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute a function with exponential backoff retry."""
        max_retries = kwargs.pop('max_retries', 3)
        base_delay = kwargs.pop('base_delay', 1.0)
        
        last_error = None
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except RateLimitError as e:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Rate limit hit, backing off for {delay}s...")
                await asyncio.sleep(delay)
                last_error = e
            except RetryableError as e:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Retryable error: {str(e)}, backing off for {delay}s...")
                await asyncio.sleep(delay)
                last_error = e
            except Exception as e:
                # Non-retryable error
                logger.error(f"Non-retryable error: {str(e)}")
                raise

        raise last_error or Exception("Max retries exceeded")

    async def get_block(self, slot: int, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Get block information with retries and error handling.
        
        Args:
            slot: Block slot number
            **kwargs: Additional parameters for getBlock
            
        Returns:
            Block data or None if not found
            
        Raises:
            MissingBlocksError: If too many consecutive slots are skipped
            RPCError: For other RPC errors
        """
        # Import here to avoid circular imports
        from .solana_error import RetryableError, MissingBlocksError, MethodNotSupportedError
        
        # Initialize retry parameters
        retries = 0
        max_retries = 3
        backoff_time = 1.0
        
        # Track skipped slots
        skipped_slots = 0
        max_skipped_slots = 10
        
        # Try to get the block with retries
        while True:
            try:
                # Prepare options
                options = {
                    "encoding": "jsonParsed",
                    "transactionDetails": "full",
                    "rewards": False,
                    "maxSupportedTransactionVersion": 0
                }
                
                # Update with any provided kwargs
                if kwargs:
                    options.update(kwargs)
                    logger.debug(f"Using options: {options}")
                
                # Make RPC call
                logger.debug(f"Making RPC call for slot {slot}")
                client = await self.connection_pool.get_client()
                try:
                    result = await client.get_block(slot, options)
                except MethodNotSupportedError as e:
                    logger.error(f"Endpoint {client.endpoint} does not support getBlock method")
                    # Release the client and try a different one
                    await self.connection_pool.release(client, success=False)
                    
                    # If we've tried multiple times, it might be that none of our endpoints support getBlock
                    if retries >= max_retries - 1:
                        logger.error("None of the available endpoints support getBlock method")
                        raise
                    
                    retries += 1
                    await asyncio.sleep(backoff_time)
                    backoff_time = min(backoff_time * 2, 60)  # Cap backoff at 60 seconds
                    continue
                
                if not result or not isinstance(result, dict) or "result" not in result:
                    logger.warning(f"Invalid response format for block {slot}")
                    return None
                    
                block_data = result["result"]
                if not block_data or not isinstance(block_data, dict):
                    logger.warning(f"Invalid block data format for block {slot}")
                    return None
                    
                num_txns = len(block_data.get("transactions", []))
                logger.info(f"Got block {slot} with {num_txns} transactions")
                
                return block_data
                
            except RetryableError as e:
                if "Slot skipped" in str(e):
                    # Try next slot if current one is skipped
                    slot += 1
                    skipped_slots += 1
                    logger.warning(f"Slot {slot-1} was skipped, trying slot {slot}")
                    continue
                    
                retries += 1
                if retries < max_retries:
                    logger.warning(f"Retryable error for block {slot}, attempt {retries}/{max_retries}: {str(e)}")
                    await asyncio.sleep(backoff_time)
                    backoff_time = min(backoff_time * 2, 60)  # Cap backoff at 60 seconds
                    continue
                else:
                    logger.error(f"Max retries ({max_retries}) reached for block {slot}")
                    raise
                    
            except Exception as e:
                logger.error(f"Non-retryable error getting block {slot}: {str(e)}")
                raise
        
        if skipped_slots >= max_skipped_slots:
            logger.error(f"Too many consecutive skipped slots starting from {slot-skipped_slots}")
            raise MissingBlocksError(f"Too many consecutive skipped slots starting from {slot-skipped_slots}")
            
        return None

    async def process_block(self, slot: int) -> Optional[Dict[str, Any]]:
        """Process a single block with error handling."""
        try:
            block = await self.get_block(slot)
            if not block or not isinstance(block, dict):
                logger.warning(f"No valid block data for slot {slot}")
                return None
                
            # Process transactions if present
            transactions = block.get("transactions")
            if transactions is not None:
                return block
            else:
                logger.warning(f"No transactions field in block {slot}")
                return None
                
        except RetryableError as e:
            logger.error(f"Error processing block {slot}: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Error processing block {slot}: {str(e)}")
            raise

    async def process_blocks_batch(
        self,
        slots: List[int],
        commitment: str = DEFAULT_COMMITMENT,
        handlers: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """Process a batch of blocks with enhanced error handling and rate limiting."""
        results = []
        stats = {
            "total_blocks": len(slots),
            "processed_blocks": 0,
            "empty_blocks": 0,
            "error_blocks": 0,
            "total_transactions": 0,
            "total_instructions": 0,
            "processing_time_ms": 0,
            "errors": []
        }
        
        start_time = time.time()
        logger.info(f"Starting batch processing for {len(slots)} slots")
        
        try:
            # Process blocks with delay between each to respect rate limits
            for slot in slots:
                try:
                    logger.debug(f"Processing slot {slot}")
                    # Process block
                    result = await self.process_block(slot)
                    if not result:
                        logger.debug(f"No result for slot {slot}")
                        stats["empty_blocks"] += 1
                        continue
                        
                    # Update statistics
                    stats["processed_blocks"] += 1
                    if result.get("empty", True):
                        stats["empty_blocks"] += 1
                        logger.debug(f"Empty block at slot {slot}")
                    if not result.get("success", False):
                        stats["error_blocks"] += 1
                        if result.get("error"):
                            stats["errors"].append(result["error"])
                            logger.warning(f"Error in block {slot}: {result['error']}")
                            
                    # Track transactions and instructions
                    num_txns = len(result.get("transactions", []))
                    num_instructions = sum(len(tx.get("message", {}).get("instructions", [])) 
                                        for tx in result.get("transactions", []))
                    
                    stats["total_transactions"] += num_txns
                    stats["total_instructions"] += num_instructions
                    logger.debug(f"Processed block {slot}: {num_txns} txns, {num_instructions} instructions")
                    
                    results.append(result)
                    
                    # Add delay between blocks
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Error processing block {slot}: {str(e)}")
                    stats["error_blocks"] += 1
                    stats["errors"].append(str(e))
                    
            # Calculate total processing time
            stats["processing_time_ms"] = int((time.time() - start_time) * 1000)
            logger.info(f"Finished batch processing. Time: {stats['processing_time_ms']}ms, "
                       f"Processed: {stats['processed_blocks']}, "
                       f"Empty: {stats['empty_blocks']}, "
                       f"Errors: {stats['error_blocks']}")
            
            return {
                "success": True,
                "results": results,
                "statistics": stats
            }
            
        except Exception as e:
            error_msg = f"Error processing block batch: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "results": results,
                "statistics": stats,
                "error": error_msg
            }

    async def process_blocks(
        self,
        num_blocks: int = 10,
        start_slot: Optional[int] = None,
        end_slot: Optional[int] = None,
        commitment: str = DEFAULT_COMMITMENT,
        batch_size: int = 10,
        handlers: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """Process multiple blocks in parallel with batching."""
        try:
            # Ensure initialized
            await self.ensure_initialized()
            logger.info("Starting block processing")
            
            # Get latest block if start_slot not provided
            if start_slot is None:
                client = await self.connection_pool.get_client()
                start_slot = await client.get_slot(commitment=commitment)
                if not isinstance(start_slot, int):
                    logger.error("Failed to get current slot")
                    raise RPCError("Failed to get current slot")
                    
                logger.info(f"Got current slot: {start_slot}")
                    
            # Calculate end_slot if not provided
            if end_slot is None:
                end_slot = max(0, start_slot - num_blocks + 1)
                logger.info(f"Calculated end slot: {end_slot}")
                
            # Ensure valid slot range
            if start_slot < 0 or end_slot < 0 or start_slot < end_slot:
                logger.error(f"Invalid slot range: {start_slot} to {end_slot}")
                raise ValueError("Invalid slot range")
                
            # Initialize results
            blocks = []
            stats = {
                "total_blocks": num_blocks,
                "processed_blocks": 0,
                "empty_blocks": 0,
                "error_blocks": 0,
                "total_transactions": 0,
                "total_instructions": 0,
                "processing_time_ms": 0,
                "errors": []
            }
            
            start_time = time.time()
            
            # Process slots in batches
            current_slot = start_slot
            while current_slot >= end_slot:
                batch_end = max(end_slot, current_slot - batch_size + 1)
                batch_slots = list(range(current_slot, batch_end - 1, -1))
                logger.info(f"Processing batch of {len(batch_slots)} slots from {current_slot} to {batch_end}")
                
                # Process batch
                batch_result = await self.process_blocks_batch(
                    slots=batch_slots,
                    commitment=commitment,
                    handlers=handlers
                )
                
                if batch_result.get("success"):
                    blocks.extend(batch_result["results"])
                    stats["processed_blocks"] += batch_result["statistics"]["processed_blocks"]
                    stats["empty_blocks"] += batch_result["statistics"]["empty_blocks"]
                    stats["error_blocks"] += batch_result["statistics"]["error_blocks"]
                    stats["total_transactions"] += batch_result["statistics"]["total_transactions"]
                    stats["total_instructions"] += batch_result["statistics"]["total_instructions"]
                    stats["errors"].extend(batch_result["statistics"]["errors"])
                    logger.info(f"Successfully processed batch. Total blocks: {len(blocks)}")
                else:
                    stats["error_blocks"] += len(batch_slots)
                    if batch_result.get("error"):
                        stats["errors"].append(batch_result["error"])
                        logger.error(f"Error processing batch: {batch_result['error']}")
                
                current_slot = batch_end - 1
                
            # Calculate total processing time
            stats["processing_time_ms"] = int((time.time() - start_time) * 1000)
            logger.info(f"Finished processing blocks. Total time: {stats['processing_time_ms']}ms")
            
            return {
                "success": True,
                "blocks": blocks,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Error in process_blocks: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def analyze_blocks(
        self,
        start_slot: int,
        end_slot: int,
        commitment: str = DEFAULT_COMMITMENT,
        batch_size: int = 10,
        handlers: Optional[List[Any]] = None
    ) -> List[Dict[str, Any]]:
        """Analyze multiple blocks in parallel with batching."""
        try:
            logger.info(f"Analyzing blocks from {start_slot} to {end_slot}")
            
            # Validate slot range
            if start_slot > end_slot:
                raise ValueError("Start slot must be less than or equal to end slot")
            
            # Create batches
            batches = [list(range(start_slot, end_slot + 1)[i:i + batch_size]) for i in range(0, end_slot - start_slot + 1, batch_size)]
            
            results = []
            for batch in batches:
                # Add delay between batches to help with rate limiting
                if results:  # Don't delay before first batch
                    await asyncio.sleep(2.0)  # 2 second delay between batches
                
                batch_results = await self.process_blocks_batch(batch, commitment, handlers)
                results.extend(batch_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing blocks: {str(e)}")
            raise

    async def get_mints_from_recent_blocks(self, num_blocks: int = 10) -> Dict[str, Any]:
        """Get mint information from recent blocks."""
        try:
            latest = await self.get_latest_block()
            if not latest:
                return {
                    "mints": [],
                    "total_mints": 0,
                    "blocks_analyzed": 0,
                    "latest_block": None,
                    "error": "Failed to get current slot"
                }

            start_slot = latest['slot']
            end_slot = start_slot - num_blocks + 1
            
            logger.info(f"Analyzing blocks from {end_slot} to {start_slot}")
            
            results = await self.analyze_blocks(
                start_slot=end_slot,
                end_slot=start_slot,
                handlers=[self.handlers['mint']]
            )
            
            # Extract mint information
            mint_results = []
            blocks_analyzed = 0
            
            for block_result in results:
                if block_result['success']:
                    blocks_analyzed += 1
                    handler_results = block_result.get('handler_results', {})
                    mint_handler_result = handler_results.get('MintHandler', {})
                    if mint_handler_result and 'mint_operations' in mint_handler_result:
                        mint_results.extend(mint_handler_result['mint_operations'])

            return {
                "mints": mint_results,
                "total_mints": len(mint_results),
                "blocks_analyzed": blocks_analyzed,
                "latest_block": start_slot,
                "start_slot": end_slot,
                "end_slot": start_slot
            }

        except Exception as e:
            logger.error(f"Error getting mints from recent blocks: {str(e)}")
            raise RPCError(f"Failed to get mints from recent blocks: {str(e)}")

    async def get_signatures_for_address(
        self,
        address: Union[str, Pubkey],
        start_slot: Optional[int] = None,
        end_slot: Optional[int] = None,
        limit: int = 1000,
        before: Optional[str] = None,
        until: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get signatures for transactions involving the given address"""
        try:
            # Convert address to string if needed
            if isinstance(address, Pubkey):
                address = str(address)
                
            # Build params
            params = {"limit": limit}
            if start_slot is not None:
                params["minSlot"] = start_slot
            if end_slot is not None:
                params["maxSlot"] = end_slot
            if before:
                params["before"] = before
            if until:
                params["until"] = until
                
            logger.debug(f"Getting signatures for address {address} with params: {params}")
            
            client = await self.connection_pool.get_client()
            response = await client.get_signatures_for_address(address, **params)
            if not response:
                logger.info(f"No signatures found for address {address}")
                return []
                
            logger.debug(f"Found {len(response)} signatures for address {address}")
            return response
            
        except Exception as e:
            handle_rpc_error(e, f"get_signatures_for_address({address})")
            return []

    async def get_latest_block(self) -> Optional[Dict[str, Any]]:
        """Get the latest finalized block."""
        try:
            client = await self.connection_pool.get_client()
            slot = await client.get_slot()
            if not slot:
                logger.error("Failed to get current slot")
                return None
                
            return {"slot": slot}
            
        except Exception as e:
            handle_rpc_error(e, "get_latest_block")
            return None

    async def get_vote_accounts(self) -> Dict[str, Any]:
        """Get vote accounts information including stake distribution."""
        try:
            await self.ensure_initialized()
            client = await self.connection_pool.get_client()
            
            # Get vote accounts directly from client
            response = await client.get_vote_accounts()
            
            # Check if the response is valid
            if isinstance(response, dict):
                # The SolanaClient.get_vote_accounts already extracts the result
                # so we can return it directly
                return response
            
            # If response is not a dict, log and return empty dict
            logging.warning(f"Unexpected response type: {type(response)}")
            return {}
        except Exception as e:
            logging.error(f"Error getting vote accounts: {str(e)}")
            return {}

    async def get_cluster_nodes(self) -> List[Dict[str, Any]]:
        """
        Get information about all the nodes participating in the cluster.
        
        Returns:
            List of node information or empty list on error
        """
        # Ensure the handler is initialized
        await self.ensure_initialized()
        
        # Get the connection pool
        connection_pool = self.connection_pool
        
        # Track all errors for diagnostics
        all_errors = []
        
        try:
            # Get multiple clients to try in parallel
            clients = []
            tasks = []
            
            # Try to get up to 3 different clients
            for _ in range(3):
                try:
                    client = await connection_pool.get_client()
                    clients.append(client)
                    
                    # Create a task for this client
                    task = asyncio.create_task(self._get_cluster_nodes_from_client(client))
                    task.client = client  # Store the client reference on the task
                    tasks.append(task)
                except Exception as e:
                    logging.error(f"Error getting client from pool: {str(e)}")
                    if client:
                        try:
                            await connection_pool.release(client, success=False)
                        except Exception as release_error:
                            logging.error(f"Error releasing client: {str(release_error)}")
            
            # Wait for the first successful result or all failures
            if tasks:
                done, pending = await asyncio.wait(
                    tasks, 
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=5.0  # 5 second timeout for faster response
                )
                
                # Cancel any pending tasks
                for task in pending:
                    task.cancel()
                    # Make sure to release the client associated with this task
                    if hasattr(task, 'client'):
                        try:
                            await connection_pool.release(task.client, success=False)
                        except Exception as release_error:
                            logging.error(f"Error releasing client from cancelled task: {str(release_error)}")
                
                # Check for successful results
                for task in done:
                    try:
                        result = task.result()
                        if result and isinstance(result, tuple) and len(result) == 2:
                            nodes, success_client = result
                            
                            # Only consider this a success if we got actual nodes
                            if nodes and len(nodes) > 0:
                                # Release all clients except the successful one
                                for client in clients:
                                    if client != success_client:
                                        try:
                                            await connection_pool.release(client, success=False)
                                        except Exception as release_error:
                                            logging.error(f"Error releasing client: {str(release_error)}")
                                
                                # Release the successful client
                                try:
                                    await connection_pool.release(success_client, success=True)
                                except Exception as release_error:
                                    logging.error(f"Error releasing successful client: {str(release_error)}")
                                
                                # Log success statistics
                                logging.info(f"Successfully retrieved {len(nodes)} cluster nodes from {success_client.endpoint}")
                                
                                # Return the nodes
                                return nodes
                            else:
                                logging.warning(f"Task completed but returned empty nodes list from {success_client.endpoint}")
                                all_errors.append({
                                    'endpoint': success_client.endpoint,
                                    'error': 'Empty nodes list returned',
                                    'type': 'EmptyResponse',
                                    'timestamp': datetime.now().isoformat()
                                })
                                
                                # Release the client
                                try:
                                    await connection_pool.release(success_client, success=False)
                                except Exception as release_error:
                                    logging.error(f"Error releasing client: {str(release_error)}")
                    except Exception as e:
                        logging.error(f"Error processing task result: {str(e)}", exc_info=True)
                        all_errors.append({
                            'error': str(e),
                            'type': type(e).__name__,
                            'stack': traceback.format_exc(),
                            'timestamp': datetime.now().isoformat()
                        })
                
                # Release any remaining clients
                for client in clients:
                    try:
                        await connection_pool.release(client, success=False)
                    except Exception as release_error:
                        logging.error(f"Error releasing client: {str(release_error)}")
            
            # If we get here, all parallel attempts failed
            # Try to use the RPCNodeExtractor as a fallback
            logging.warning("All parallel RPC endpoints failed to retrieve cluster nodes, trying RPCNodeExtractor fallback")
            
            try:
                # Import the RPCNodeExtractor class
                from .rpc_node_extractor import RPCNodeExtractor
                
                # Create an extractor instance
                extractor = RPCNodeExtractor()
                
                # Get nodes from the extractor with a timeout
                nodes = await asyncio.wait_for(
                    extractor.get_all_rpc_nodes(),
                    timeout=4.0  # 4 second timeout for extractor
                )
                
                if nodes and len(nodes) > 0:
                    logging.info(f"Successfully retrieved {len(nodes)} nodes using RPCNodeExtractor fallback")
                    
                    # Convert to the expected format
                    formatted_nodes = []
                    for node in nodes:
                        formatted_nodes.append({
                            'pubkey': node.get('pubkey', ''),
                            'gossip': node.get('gossip', ''),
                            'tpu': node.get('tpu', ''),
                            'rpc': node.get('rpc', ''),
                            'version': node.get('version', 'unknown'),
                            'featureSet': node.get('feature_set', 0),
                            'shredVersion': node.get('shred_version', 0)
                        })
                    
                    return formatted_nodes
                else:
                    logging.error("RPCNodeExtractor fallback returned empty nodes list")
                    all_errors.append({
                        'endpoint': 'RPCNodeExtractor',
                        'error': 'Empty nodes list returned',
                        'type': 'EmptyResponse',
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except asyncio.TimeoutError:
                logging.error("RPCNodeExtractor fallback timed out")
                all_errors.append({
                    'endpoint': 'RPCNodeExtractor',
                    'error': 'Timeout after 4 seconds',
                    'type': 'TimeoutError',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as fallback_error:
                logging.error(f"Fallback RPCNodeExtractor also failed: {str(fallback_error)}", exc_info=True)
                all_errors.append({
                    'endpoint': 'RPCNodeExtractor',
                    'error': str(fallback_error),
                    'type': type(fallback_error).__name__,
                    'stack': traceback.format_exc(),
                    'timestamp': datetime.now().isoformat()
                })
            
            # Log all errors for diagnostics
            logging.error(f"All attempts to get cluster nodes failed. Errors: {json.dumps(all_errors)}")
            
            # Return empty list as last resort
            return []
                
        except Exception as e:
            logging.error(f"Error getting cluster nodes: {str(e)}", exc_info=True)
            all_errors.append({
                'error': str(e),
                'type': type(e).__name__,
                'stack': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            })
            logging.error(f"Final error details: {json.dumps(all_errors)}")
            return []

    async def get_version(self) -> Dict[str, Any]:
        """Get the version of the node."""
        try:
            client = await self.connection_pool.get_client()
            response = await client.get_version()
            
            # Check if the response is successful and extract the result
            if isinstance(response, dict) and response.get('success', False):
                result = response.get('result', {})
                if isinstance(result, dict):
                    return result
                return {}
            return {}
        except Exception as e:
            logging.error(f"Error getting version: {str(e)}")
            return {}

    async def get_epoch_info(self) -> Dict[str, Any]:
        """Get information about the current epoch."""
        try:
            client = await self.connection_pool.get_client()
            response = await client.get_epoch_info()
            
            # Check if the response is successful and extract the result
            if isinstance(response, dict) and response.get('success', False):
                result = response.get('result', {})
                if isinstance(result, dict):
                    return result
                return {}
            return {}
        except Exception as e:
            logging.error(f"Error getting epoch info: {str(e)}")
            return {}

    async def get_recent_performance(self) -> List[Dict[str, Any]]:
        """
        Get recent performance samples.
        
        Returns:
            List of performance samples or empty list on error
        """
        try:
            # Use safe_rpc_call_async for more robust error handling
            from ..utils.solana_helpers import safe_rpc_call_async
            from ..config import HELIUS_API_KEY
            
            # Try to get performance samples with explicit fallback handling
            max_attempts = 5  # Try up to 5 different endpoints
            tried_endpoints = set()
            not_supported_count = 0
            other_error_count = 0
            client = None  # Initialize client to None for proper cleanup
            
            # Create a list of known endpoints that support getRecentPerformanceSamples
            # These are endpoints that we know support this method
            known_supporting_endpoints = [
                "https://api.mainnet-beta.solana.com",
                "https://solana-api.projectserum.com",
                "https://rpc.ankr.com/solana"
            ]
            
            # First try the known supporting endpoints specifically
            for endpoint in known_supporting_endpoints:
                try:
                    # Get a specific client from the pool that matches the endpoint
                    client = await self.connection_pool.get_specific_client(endpoint)
                    
                    if client:
                        tried_endpoints.add(client.endpoint)
                        logging.info(f"Attempting to get performance samples from known supporting endpoint: {client.endpoint}")
                        
                        # Try to get performance samples with a shorter timeout
                        response = await asyncio.wait_for(
                            client.get_recent_performance_samples(),
                            timeout=5.0  # Shorter timeout for faster fallback
                        )
                        
                        # Process the response
                        if isinstance(response, dict):
                            # Check if there's an error indicating method not supported
                            if 'error' in response and isinstance(response['error'], dict):
                                error = response['error']
                                if error.get('code') == -32601 or "not supported" in error.get('message', '').lower():
                                    logging.warning(f"Endpoint {client.endpoint} does not support getRecentPerformanceSamples")
                                    not_supported_count += 1
                                    await self.connection_pool.release(client, success=True)
                                    client = None  # Reset client after release
                                else:
                                    logging.error(f"Error from endpoint {client.endpoint}: {error}")
                                    other_error_count += 1
                                    await self.connection_pool.release(client, success=False)
                                    client = None  # Reset client after release
                            elif 'result' in response:
                                if isinstance(response['result'], list):
                                    samples_count = len(response['result'])
                                    logging.info(f"Found {samples_count} performance samples from {client.endpoint}")
                                    if samples_count > 0:
                                        await self.connection_pool.release(client, success=True)
                                        client = None  # Reset client after release
                                        return response['result']
                                    else:
                                        logging.warning(f"Empty performance samples list returned from {client.endpoint}")
                                        await self.connection_pool.release(client, success=True)
                                        client = None  # Reset client after release
                                else:
                                    logging.warning(f"Result from {client.endpoint} is not a list: {type(response['result'])}")
                                    await self.connection_pool.release(client, success=True)
                                    client = None  # Reset client after release
                            else:
                                logging.warning(f"No result field in performance samples response from {client.endpoint}")
                                await self.connection_pool.release(client, success=True)
                                client = None  # Reset client after release
                        else:
                            logging.warning(f"Unexpected response type from {client.endpoint}: {type(response)}")
                            await self.connection_pool.release(client, success=True)
                            client = None  # Reset client after release
                except Exception as e:
                    if client is not None:
                        await self.connection_pool.release(client, success=False)
                        client = None  # Reset client after release
                    
                    error_msg = str(e).lower()
                    if "not supported" in error_msg or "method not found" in error_msg:
                        logging.warning(f"Endpoint does not support getRecentPerformanceSamples: {error_msg}")
                        not_supported_count += 1
                        # Continue to try another endpoint
                    else:
                        logging.error(f"Error getting performance samples from {endpoint}: {str(e)}")
                        logging.exception(e)
                        other_error_count += 1
            
            # If we still don't have data, try other endpoints
            for attempt in range(max_attempts):
                try:
                    # Get a client from the pool
                    client = await self.connection_pool.get_client()
                    
                    # Skip if we've already tried this endpoint
                    if client.endpoint in tried_endpoints:
                        logging.debug(f"Skipping already tried endpoint {client.endpoint}")
                        # Release the client back to the pool
                        await self.connection_pool.release(client, success=True)
                        client = None  # Reset client after release
                        continue
                    
                    tried_endpoints.add(client.endpoint)
                    logging.info(f"Attempting to get performance samples from {client.endpoint} (attempt {attempt+1}/{max_attempts})")
                    
                    # Try to get performance samples with a shorter timeout
                    response = await asyncio.wait_for(
                        client.get_recent_performance_samples(),
                        timeout=4.0  # Shorter timeout for faster fallback
                    )
                    
                    # Process the response
                    if isinstance(response, dict):
                        # Check if there's an error indicating method not supported
                        if 'error' in response and isinstance(response['error'], dict):
                            error = response['error']
                            if error.get('code') == -32601 or "not supported" in error.get('message', '').lower():
                                logging.warning(f"Endpoint {client.endpoint} does not support getRecentPerformanceSamples")
                                not_supported_count += 1
                                await self.connection_pool.release(client, success=True)
                                client = None  # Reset client after release
                                continue
                        
                        if 'result' in response:
                            if isinstance(response['result'], list):
                                samples_count = len(response['result'])
                                logging.info(f"Found {samples_count} performance samples")
                                if samples_count > 0:
                                    await self.connection_pool.release(client, success=True)
                                    client = None  # Reset client after release
                                    return response['result']
                                else:
                                    logging.warning("Empty performance samples list returned")
                                    await self.connection_pool.release(client, success=True)
                                    client = None  # Reset client after release
                                    # Continue to try another endpoint
                            else:
                                logging.warning(f"Result is not a list: {type(response['result'])}")
                                await self.connection_pool.release(client, success=True)
                                client = None  # Reset client after release
                                # Continue to try another endpoint
                        else:
                            logging.warning("No result field in performance samples response")
                            await self.connection_pool.release(client, success=True)
                            client = None  # Reset client after release
                            # Continue to try another endpoint
                    else:
                        logging.warning(f"Unexpected response type: {type(response)}")
                        await self.connection_pool.release(client, success=True)
                        client = None  # Reset client after release
                        # Continue to try another endpoint
                
                except Exception as e:
                    # Release the client back to the pool
                    if client is not None:
                        await self.connection_pool.release(client, success=False)
                        client = None  # Reset client after release
                    
                    # Check if this is a "method not supported" error
                    error_msg = str(e).lower()
                    if "not supported" in error_msg or "method not found" in error_msg:
                        logging.warning(f"Endpoint does not support getRecentPerformanceSamples: {error_msg}")
                        not_supported_count += 1
                        # Continue to try another endpoint
                    else:
                        logging.error(f"Error getting performance samples: {str(e)}")
                        logging.exception(e)  # Log full stack trace
                        other_error_count += 1
                        # Continue to try another endpoint
            
            # If we get here, we've tried multiple endpoints and none worked
            logging.warning(f"Failed to get performance samples after trying {len(tried_endpoints)} endpoints")
            logging.warning(f"Method not supported: {not_supported_count} endpoints, Other errors: {other_error_count} endpoints")
            
            # If all endpoints don't support the method, return a synthetic sample with reasonable defaults
            if not_supported_count == len(tried_endpoints):
                logging.error("getRecentPerformanceSamples not supported by any endpoint")
                
                # Create synthetic performance data based on typical Solana performance
                # This is better than returning an error when all endpoints don't support the method
                current_time = int(time.time())
                return [{
                    "numSlots": 120,  # ~2 slots per second is typical
                    "numTransactions": 1200,  # ~10 TPS per slot is reasonable
                    "samplePeriodSecs": 60,
                    "slot": 0,  # We don't know the actual slot
                    "timestamp": current_time - 60,  # 1 minute ago
                    "synthetic": True,  # Mark as synthetic data
                    "error": "Method not supported by any endpoint",
                    "endpoints_tried": len(tried_endpoints)
                }]
            
            # Otherwise, return an empty list to indicate error
            return []
        
        except Exception as e:
            logging.error(f"Error in get_recent_performance: {str(e)}")
            logging.exception(e)  # Log full stack trace
            
            # Ensure client is properly released if it exists
            if 'client' in locals() and client is not None:
                try:
                    await self.connection_pool.release(client, success=False)
                except Exception as release_error:
                    logging.error(f"Error releasing client in exception handler: {str(release_error)}")
            
            return []

    async def get_block_production(self) -> Dict[str, Any]:
        """
        Get block production information.
        
        Returns:
            Dict with block production information or error details
        """
        try:
            # Import required modules
            from ..utils.solana_helpers import safe_rpc_call_async
            from ..config import HELIUS_API_KEY
            
            # Try to get block production with explicit fallback handling
            max_attempts = 5  # Try up to 5 different endpoints
            tried_endpoints = set()
            not_supported_count = 0
            other_error_count = 0
            
            # First try the Helius endpoint specifically if available
            if HELIUS_API_KEY:
                try:
                    helius_endpoint = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
                    
                    # Get a specific client from the pool that matches the Helius endpoint
                    client = await self.connection_pool.get_specific_client(helius_endpoint)
                    
                    if client:
                        tried_endpoints.add(client.endpoint)
                        logging.info(f"Attempting to get block production from Helius endpoint")
                        
                        # Try to get block production with timeout
                        response = await asyncio.wait_for(
                            client.get_block_production(),
                            timeout=10.0
                        )
                        
                        # Process the response
                        if isinstance(response, dict):
                            # Check if there's an error indicating method not supported
                            if 'error' in response and isinstance(response['error'], dict):
                                error = response['error']
                                if error.get('code') == -32601 or "not supported" in error.get('message', '').lower():
                                    logging.warning(f"Helius endpoint does not support getBlockProduction")
                                    not_supported_count += 1
                                    await self.connection_pool.release(client, success=True)
                                else:
                                    logging.error(f"Error from Helius endpoint: {error}")
                                    other_error_count += 1
                                    await self.connection_pool.release(client, success=False)
                            elif 'result' in response:
                                logging.info(f"Successfully retrieved block production from Helius")
                                await self.connection_pool.release(client, success=True)
                                return response
                            else:
                                logging.warning("No result field in block production response from Helius")
                                await self.connection_pool.release(client, success=True)
                        else:
                            logging.warning(f"Unexpected response type from Helius: {type(response)}")
                            await self.connection_pool.release(client, success=True)
                except Exception as e:
                    if 'client' in locals() and client is not None:
                        await self.connection_pool.release(client, success=False)
                    
                    error_msg = str(e).lower()
                    if "not supported" in error_msg or "method not found" in error_msg:
                        logging.warning(f"Helius endpoint does not support getBlockProduction: {error_msg}")
                        not_supported_count += 1
                    else:
                        logging.error(f"Error getting block production from Helius: {str(e)}")
                        logging.exception(e)
                        other_error_count += 1
            
            # Then try other endpoints
            for attempt in range(max_attempts):
                try:
                    # Get a client from the pool
                    client = await self.connection_pool.get_client()
                    
                    # Skip if we've already tried this endpoint
                    if client.endpoint in tried_endpoints:
                        logging.debug(f"Skipping already tried endpoint {client.endpoint}")
                        # Release the client back to the pool
                        await self.connection_pool.release(client, success=True)
                        continue
                    
                    tried_endpoints.add(client.endpoint)
                    logging.info(f"Attempting to get block production from {client.endpoint} (attempt {attempt+1}/{max_attempts})")
                    
                    # Try to get block production with timeout
                    response = await asyncio.wait_for(
                        client.get_block_production(),
                        timeout=10.0
                    )
                    
                    # Process the response
                    if isinstance(response, dict):
                        # Check if there's an error indicating method not supported
                        if 'error' in response and isinstance(response['error'], dict):
                            error = response['error']
                            if error.get('code') == -32601 or "not supported" in error.get('message', '').lower():
                                logging.warning(f"Endpoint {client.endpoint} does not support getBlockProduction")
                                not_supported_count += 1
                                await self.connection_pool.release(client, success=True)
                                continue
                        
                        if 'result' in response:
                            logging.info(f"Successfully retrieved block production")
                            await self.connection_pool.release(client, success=True)
                            return response
                        else:
                            logging.warning("No result field in block production response")
                            await self.connection_pool.release(client, success=True)
                            # Continue to try another endpoint
                    else:
                        logging.warning(f"Unexpected response type: {type(response)}")
                        await self.connection_pool.release(client, success=True)
                        # Continue to try another endpoint
                
                except Exception as e:
                    # Release the client back to the pool
                    if 'client' in locals() and client is not None:
                        await self.connection_pool.release(client, success=False)
                    
                    # Check if this is a "method not supported" error
                    error_msg = str(e).lower()
                    if "not supported" in error_msg or "method not found" in error_msg:
                        logging.warning(f"Endpoint does not support getBlockProduction: {error_msg}")
                        not_supported_count += 1
                        # Continue to try another endpoint
                    else:
                        logging.error(f"Error getting block production: {str(e)}")
                        logging.exception(e)  # Log full stack trace
                        other_error_count += 1
                        # Continue to try another endpoint
            
            # If we get here, we've tried multiple endpoints and none worked
            logging.warning(f"Failed to get block production after trying {len(tried_endpoints)} endpoints")
            logging.warning(f"Method not supported: {not_supported_count} endpoints, Other errors: {other_error_count} endpoints")
            
            # Return a structured empty result with error information
            if not_supported_count == len(tried_endpoints):
                logging.error("getBlockProduction not supported by any endpoint")
                return {
                    "result": {
                        "value": {
                            "total": 0,
                            "skippedSlots": 0,
                            "byIdentity": {}
                        }
                    },
                    "error": {
                        "message": "Method not supported by any endpoint",
                        "code": -32601,
                        "data": {
                            "endpoints_tried": len(tried_endpoints),
                            "timestamp": int(time.time())
                        }
                    }
                }
            
            # Return a generic error response
            return {
                "result": {
                    "value": {
                        "total": 0,
                        "skippedSlots": 0,
                        "byIdentity": {}
                    }
                },
                "error": {
                    "message": f"Failed to get block production after {len(tried_endpoints)} attempts",
                    "code": -32000,
                    "data": {
                        "endpoints_tried": len(tried_endpoints),
                        "not_supported_count": not_supported_count,
                        "other_error_count": other_error_count,
                        "timestamp": int(time.time())
                    }
                }
            }
                
        except Exception as e:
            logging.error(f"Unexpected error in get_block_production: {str(e)}")
            logging.exception(e)  # Log full stack trace
            return {
                "result": {
                    "value": {
                        "total": 0,
                        "skippedSlots": 0,
                        "byIdentity": {}
                    }
                },
                "error": {
                    "message": f"Unexpected error: {str(e)}",
                    "code": -32000,
                    "data": {
                        "timestamp": int(time.time())
                    }
                }
            }

    async def get_network_status(self) -> Dict[str, Any]:
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
        # Initialize the result structure
        result = {
            'node_count': 0,
            'active_nodes': 0,
            'delinquent_nodes': 0,
            'version_distribution': {},
            'feature_set_distribution': {},
            'stake_distribution': {},
            'errors': [],
            'status': 'unknown',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Get cluster nodes
            nodes = await self.get_cluster_nodes()
            
            if not nodes:
                result['errors'].append({
                    'source': 'get_cluster_nodes',
                    'error': 'Failed to retrieve cluster nodes',
                    'timestamp': datetime.now().isoformat()
                })
                result['status'] = 'degraded'
                return result
                
            # Process node information
            result['node_count'] = len(nodes)
            
            # Track version and feature set distribution
            version_counts = {}
            feature_set_counts = {}
            
            for node in nodes:
                # Count active vs delinquent nodes
                if node.get('delinquent', False):
                    result['delinquent_nodes'] += 1
                else:
                    result['active_nodes'] += 1
                    
                # Track version distribution
                version = node.get('version', 'unknown')
                version_counts[version] = version_counts.get(version, 0) + 1
                
                # Track feature set distribution
                feature_set = node.get('featureSet', 0)
                feature_set_counts[feature_set] = feature_set_counts.get(feature_set, 0) + 1
                
            # Convert counts to percentages
            total_nodes = result['node_count']
            
            for version, count in version_counts.items():
                result['version_distribution'][version] = {
                    'count': count,
                    'percentage': round((count / total_nodes) * 100, 2)
                }
                
            for feature_set, count in feature_set_counts.items():
                result['feature_set_distribution'][str(feature_set)] = {
                    'count': count,
                    'percentage': round((count / total_nodes) * 100, 2)
                }
                
            # Try to get vote accounts for stake distribution
            try:
                vote_accounts = await self.get_vote_accounts()
                
                if vote_accounts and isinstance(vote_accounts, dict):
                    # Calculate total stake
                    current = vote_accounts.get('current', [])
                    delinquent = vote_accounts.get('delinquent', [])
                    
                    total_stake = 0
                    for validator in current + delinquent:
                        total_stake += validator.get('activatedStake', 0)
                        
                    # Only process if we have some stake
                    if total_stake > 0:
                        # Group validators by stake
                        stake_groups = {
                            'high': {'count': 0, 'stake': 0},  # Top 10% of validators by stake
                            'medium': {'count': 0, 'stake': 0},  # Middle 40% of validators
                            'low': {'count': 0, 'stake': 0},    # Bottom 50% of validators
                            'delinquent': {'count': 0, 'stake': 0}  # Delinquent validators
                        }
                        
                        # Process current validators
                        sorted_validators = sorted(current, key=lambda v: v.get('activatedStake', 0), reverse=True)
                        validator_count = len(sorted_validators)
                        
                        if validator_count > 0:
                            # Determine thresholds
                            high_threshold = max(1, int(validator_count * 0.1))
                            medium_threshold = max(high_threshold, int(validator_count * 0.5))
                            
                            # Categorize validators
                            for i, validator in enumerate(sorted_validators):
                                stake = validator.get('activatedStake', 0)
                                
                                if i < high_threshold:
                                    stake_groups['high']['count'] += 1
                                    stake_groups['high']['stake'] += stake
                                elif i < medium_threshold:
                                    stake_groups['medium']['count'] += 1
                                    stake_groups['medium']['stake'] += stake
                                else:
                                    stake_groups['low']['count'] += 1
                                    stake_groups['low']['stake'] += stake
                                    
                        # Process delinquent validators
                        for validator in delinquent:
                            stake = validator.get('activatedStake', 0)
                            stake_groups['delinquent']['count'] += 1
                            stake_groups['delinquent']['stake'] += stake
                            
                        # Calculate percentages
                        for group, data in stake_groups.items():
                            data['stake_percentage'] = round((data['stake'] / total_stake) * 100, 2)
                            
                        result['stake_distribution'] = stake_groups
                        
                else:
                    result['errors'].append({
                        'source': 'get_vote_accounts',
                        'error': 'Failed to retrieve vote accounts',
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as vote_error:
                logging.error(f"Error processing vote accounts: {str(vote_error)}", exc_info=True)
                result['errors'].append({
                    'source': 'get_vote_accounts',
                    'error': str(vote_error),
                    'type': type(vote_error).__name__,
                    'timestamp': datetime.now().isoformat()
                })
                
            # Determine overall network status
            active_percentage = 0
            if total_nodes > 0:
                active_percentage = (result['active_nodes'] / total_nodes) * 100
                
            if active_percentage >= 95:
                result['status'] = 'healthy'
            elif active_percentage >= 80:
                result['status'] = 'degraded'
            else:
                result['status'] = 'unhealthy'
                
            # Add performance metrics if available
            try:
                performance = await self.get_recent_performance()
                
                if performance and isinstance(performance, list) and len(performance) > 0:
                    # Calculate average TPS from the most recent samples
                    recent_samples = performance[:min(5, len(performance))]
                    
                    total_tps = 0
                    sample_count = 0
                    
                    for sample in recent_samples:
                        if isinstance(sample, dict) and 'numTransactions' in sample and 'samplePeriodSecs' in sample:
                            num_txns = sample.get('numTransactions', 0)
                            period_secs = sample.get('samplePeriodSecs', 1)
                            
                            if period_secs > 0:
                                tps = num_txns / period_secs
                                total_tps += tps
                                sample_count += 1
                                
                    if sample_count > 0:
                        result['average_tps'] = round(total_tps / sample_count, 2)
                        
                else:
                    result['errors'].append({
                        'source': 'get_recent_performance',
                        'error': 'Failed to retrieve performance samples',
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as perf_error:
                logging.error(f"Error processing performance data: {str(perf_error)}", exc_info=True)
                result['errors'].append({
                    'source': 'get_recent_performance',
                    'error': str(perf_error),
                    'type': type(perf_error).__name__,
                    'timestamp': datetime.now().isoformat()
                })
                
            return result
            
        except Exception as e:
            logging.error(f"Error getting network status: {str(e)}", exc_info=True)
            result['errors'].append({
                'source': 'get_network_status',
                'error': str(e),
                'type': type(e).__name__,
                'stack': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            })
            result['status'] = 'unhealthy'
            return result

    async def _get_cluster_nodes_from_client(self, client):
        """
        Get cluster nodes from a specific client.
        
        Args:
            client: The RPC client to use
            
        Returns:
            Tuple of (nodes list, client) if successful, or ([], client) on error
        """
        try:
            logging.info(f"Making get_cluster_nodes RPC call to endpoint: {client.endpoint}")
            
            # Use safe_rpc_call_async for better error handling and retry logic
            response = await safe_rpc_call_async(
                "getClusterNodes",  # Use the exact RPC method name
                client=client,
                max_retries=1,  # Reduced retries for faster response
                retry_delay=0.5,  # Shorter delay between retries
                timeout=5.0  # Shorter timeout for faster failure detection
            )
            
            # Enhanced response handling with detailed logging
            if isinstance(response, dict):
                if 'result' in response:
                    nodes = response['result']
                    if isinstance(nodes, list):
                        nodes_count = len(nodes) if nodes else 0
                        if nodes_count > 0:
                            logging.info(f"Found {nodes_count} cluster nodes in dict response with 'result' key from {client.endpoint}")
                            # Log a sample node for debugging
                            if nodes_count > 0:
                                sample_node = nodes[0]
                                logging.debug(f"Sample node format: {json.dumps(sample_node)[:200]}...")
                            return (nodes, client)
                        else:
                            logging.warning(f"Empty nodes list in 'result' from {client.endpoint}")
                            return ([], client)
                    else:
                        logging.warning(f"Non-list 'result' from {client.endpoint}: {type(nodes)}")
                        # Try to convert to list if possible
                        if nodes is not None:
                            try:
                                if isinstance(nodes, dict):
                                    # Some endpoints might return a single node as a dict
                                    logging.info(f"Converting single node dict to list from {client.endpoint}")
                                    return ([nodes], client)
                            except Exception as conversion_error:
                                logging.error(f"Error converting result to list: {str(conversion_error)}")
                        return ([], client)
                elif 'error' in response:
                    error_info = response['error']
                    error_msg = error_info.get('message', str(error_info))
                    error_code = error_info.get('code', 0)
                    logging.error(f"RPC error from {client.endpoint}: {error_msg} (code: {error_code})")
                    
                    # Check for specific error codes that indicate the endpoint doesn't support this method
                    if error_code in [-32601, -32600]:  # Method not found or invalid request
                        logging.error(f"Method getClusterNodes not supported by {client.endpoint}")
                    # Check for API key related errors
                    elif error_code in [401, 403, -32000, -32001, -32002, -32003, -32004]:
                        logging.error(f"API key or authorization error from {client.endpoint}: {error_msg}")
                        # Add to SSL bypass if it's an SSL error
                        if "SSL" in error_msg or "certificate" in error_msg.lower():
                            try:
                                from .solana_ssl_config import add_ssl_bypass_endpoint
                                add_ssl_bypass_endpoint(client.endpoint)
                                logging.info(f"Added {client.endpoint} to SSL bypass list due to certificate error")
                            except Exception as ssl_config_error:
                                logging.error(f"Error adding endpoint to SSL bypass: {str(ssl_config_error)}")
                    
                    return ([], client)
                elif '_soleco_context' in response:
                    # This is our special error context from safe_rpc_call_async
                    context = response.get('_soleco_context', {})
                    logging.error(f"RPC call failed with context: {json.dumps(context)}")
                    
                    # Log detailed error information for each endpoint
                    endpoint_errors = context.get('endpoint_errors', {})
                    if endpoint_errors:
                        for endpoint, error in endpoint_errors.items():
                            logging.error(f"Endpoint {endpoint} error: {json.dumps(error)}")
                            
                            # Check for SSL errors and add to bypass list
                            error_str = str(error)
                            if "SSL" in error_str or "certificate" in error_str.lower():
                                try:
                                    from .solana_ssl_config import add_ssl_bypass_endpoint
                                    add_ssl_bypass_endpoint(endpoint)
                                    logging.info(f"Added {endpoint} to SSL bypass list due to certificate error")
                                except Exception as ssl_config_error:
                                    logging.error(f"Error adding endpoint to SSL bypass: {str(ssl_config_error)}")
                    
                    return ([], client)
                else:
                    # Some endpoints might return a dict without result or error keys
                    logging.warning(f"Unexpected dict response format from {client.endpoint}: {list(response.keys())}")
                    
                    # Try to extract nodes if the response itself is a list of nodes (direct response)
                    if any(key in response for key in ['pubkey', 'gossip', 'tpu', 'rpc']):
                        logging.info(f"Response appears to be a single node from {client.endpoint}")
                        return ([response], client)
                    
                    # Try to find any array in the response that might contain nodes
                    for key, value in response.items():
                        if isinstance(value, list) and len(value) > 0:
                            # Check if the first item looks like a node
                            first_item = value[0]
                            if isinstance(first_item, dict) and any(node_key in first_item for node_key in ['pubkey', 'gossip', 'tpu', 'rpc']):
                                logging.info(f"Found potential nodes list in key '{key}' from {client.endpoint}")
                                return (value, client)
                    
                    return ([], client)
                    
            elif isinstance(response, list):
                # Some RPC endpoints return the result directly as a list
                nodes_count = len(response) if response else 0
                if nodes_count > 0:
                    logging.info(f"Found {nodes_count} cluster nodes in direct list response from {client.endpoint}")
                    # Validate that the list contains node objects
                    if all(isinstance(node, dict) for node in response):
                        # Check if at least one node has expected keys
                        if any(any(key in node for key in ['pubkey', 'gossip', 'tpu', 'rpc']) for node in response[:5]):
                            return (response, client)
                        else:
                            logging.warning(f"List items don't appear to be nodes from {client.endpoint}")
                            return ([], client)
                    else:
                        logging.warning(f"List contains non-dict items from {client.endpoint}")
                        return ([], client)
                else:
                    logging.warning(f"Empty list response from {client.endpoint}")
                    return ([], client)
                
            else:
                # Handle unexpected response types
                logging.warning(f"Unexpected response type from {client.endpoint}: {type(response)}")
                if response is not None:
                    logging.debug(f"Response preview: {str(response)[:200]}...")
                return ([], client)
                
        except asyncio.TimeoutError:
            logging.error(f"Timeout in _get_cluster_nodes_from_client for {client.endpoint}")
            return ([], client)
        except Exception as e:
            error_str = str(e)
            logging.error(f"Error in _get_cluster_nodes_from_client for {client.endpoint}: {error_str}", exc_info=True)
            
            # Check for SSL errors and add to bypass list
            if "SSL" in error_str or "certificate" in error_str.lower():
                try:
                    from .solana_ssl_config import add_ssl_bypass_endpoint
                    add_ssl_bypass_endpoint(client.endpoint)
                    logging.info(f"Added {client.endpoint} to SSL bypass list due to certificate error")
                except Exception as ssl_config_error:
                    logging.error(f"Error adding endpoint to SSL bypass: {str(ssl_config_error)}")
            
            return ([], client)
