"""
Solana query module for handling blockchain data queries.
This module provides query handlers and utilities for fetching and processing Solana blockchain data.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import asyncio
import time
import json
import logging
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
    DEFAULT_COMMITMENT
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
    RetryableError
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
        """Ensure the connection pool is initialized."""
        if not self.initialized:
            if not self.connection_pool:
                self.connection_pool = await get_connection_pool()
            await self.connection_pool.initialize()
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
        """Get block information with retries and error handling."""
        retries = 0
        max_retries = 3
        backoff_time = 1.0
        skipped_slots = 0
        max_skipped_slots = 5
        
        logger.debug(f"Getting block data for slot {slot}")
        
        while True:
            try:
                # Set up request options
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
                
                # Create params list with slot and options
                params = [slot, options]
                
                # Make RPC call
                logger.debug(f"Making RPC call for slot {slot}")
                client = await self.connection_pool.get_client()
                result = await client.get_block(*params)
                
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
            logging.warning(f"Unexpected vote accounts response type: {type(response)}")
            return {}
        except Exception as e:
            logging.error(f"Error getting vote accounts: {str(e)}")
            return {}

    async def get_cluster_nodes(self) -> List[Dict[str, Any]]:
        """Get information about all the nodes participating in the cluster."""
        try:
            client = await self.connection_pool.get_client()
            logging.info(f"Making get_cluster_nodes RPC call to endpoint: {client.endpoint}")
            response = await client.get_cluster_nodes()
            
            # Log the response for debugging
            logging.info(f"get_cluster_nodes response: {response}")
            
            # Check if the response is successful and extract the result
            if isinstance(response, dict):
                if 'result' in response:
                    logging.info(f"Found {len(response['result'])} cluster nodes")
                    return response['result']
                elif 'result' in response.get('result', {}):
                    logging.info(f"Found {len(response['result']['result'])} cluster nodes (nested)")
                    return response['result']['result']
                else:
                    logging.warning(f"No 'result' field found in response: {response}")
            else:
                logging.warning(f"Response is not a dictionary: {response}")
            return []
        except Exception as e:
            logging.error(f"Error getting cluster nodes: {str(e)}")
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
            client = await self.connection_pool.get_client()
            response = await client.get_recent_performance_samples()
            
            # Log the response type and structure for debugging
            logging.debug(f"Performance samples response type: {type(response)}")
            if isinstance(response, dict):
                logging.debug(f"Performance samples response keys: {list(response.keys())}")
            
            # Handle direct JSON response format (most common case)
            if isinstance(response, dict) and 'jsonrpc' in response and 'result' in response:
                samples = response.get('result', [])
                if isinstance(samples, list):
                    logging.info(f"Retrieved {len(samples)} performance samples directly from JSON response")
                    return samples
                
            # Handle wrapped response format from safe_rpc_call_async
            if isinstance(response, dict) and response.get('success', False):
                result = response.get('result', {})
                if isinstance(result, dict) and 'result' in result:
                    samples = result['result']
                    if isinstance(samples, list):
                        logging.info(f"Retrieved {len(samples)} performance samples from wrapped response")
                        return samples
                    else:
                        logging.warning(f"Performance samples is not a list: {type(samples)}")
                else:
                    # Try direct access to result if it's a list
                    if isinstance(result, list):
                        logging.info(f"Retrieved {len(result)} performance samples from direct result list")
                        return result
                    else:
                        logging.warning(f"Performance samples result structure is unexpected: {result}")
            else:
                # If response is already a list, return it directly
                if isinstance(response, list):
                    logging.info(f"Retrieved {len(response)} performance samples from direct list response")
                    return response
                else:
                    logging.warning(f"Failed to get performance samples: {response}")
            
            return []
        except Exception as e:
            logging.error(f"Error getting performance samples: {str(e)}")
            logging.exception(e)  # Log full stack trace
            return []
