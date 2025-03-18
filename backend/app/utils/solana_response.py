"""
Solana query module for handling blockchain data queries.
This module provides query handlers and utilities for fetching and processing Solana blockchain data.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Set, Union, TypeVar
from dataclasses import dataclass
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import time
from collections import defaultdict

from solders.rpc.responses import GetBlockResp
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient

from .solana_connection import SolanaConnectionPool
from .solana_types import (
    EndpointConfig,
    RPCError,
    NodeBehindError,
    SlotSkippedError,
    MissingBlocksError,
    SimulationError,
    NodeUnhealthyError,
    RateLimitError
)
from .handlers.base_handler import BaseHandler
from .handlers.token_handler import TokenHandler
from .handlers.program_handler import ProgramHandler
from .base_response_handler import ResponseHandler, SolanaResponseManager
from .handlers.mint_response_handler import MintResponseHandler

logger = logging.getLogger(__name__)

T = TypeVar('T')

class MintHandler(ResponseHandler):
    """Handler for mint-related responses with enhanced error handling"""
    
    def __init__(self, response_manager: Optional[SolanaResponseManager] = None):
        """Initialize with optional response manager"""
        super().__init__(response_manager)
        self.error_counts = defaultdict(int)
        self.start_time = None
        
    async def process_result(self, result: Any) -> Dict[str, Any]:
        """Process mint transaction result with comprehensive error handling"""
        try:
            if not result or not isinstance(result, dict):
                logger.warning("Invalid mint result format")
                return {
                    "success": False,
                    "error": "Invalid mint result format",
                    "mint_addresses": [],
                    "statistics": self.stats.get_current()
                }

            # Extract block data
            block_data = result.get('result', {})
            if not isinstance(block_data, dict):
                logger.warning("Invalid mint block data format")
                return {
                    "success": False,
                    "error": "Invalid mint block data format",
                    "mint_addresses": [],
                    "statistics": self.stats.get_current()
                }

            # Process transactions
            transactions = block_data.get('transactions', [])
            if not transactions:
                logger.debug("No transactions found in block")
                return {
                    "success": True,
                    "mint_addresses": [],
                    "statistics": self.stats.get_current()
                }

            # Track mint addresses and statistics
            mint_addresses = []
            for tx in transactions:
                try:
                    # Process transaction
                    mint_info = await self._process_transaction(tx)
                    if mint_info.get('mint_address'):
                        mint_addresses.append(mint_info['mint_address'])
                        
                    # Update statistics
                    self.stats.total_processed += 1
                    if mint_info.get('inner_instructions', 0) > 0:
                        self.stats.inner_instructions += mint_info['inner_instructions']
                    
                except Exception as tx_error:
                    error_type = type(tx_error).__name__
                    self.error_counts[error_type] += 1
                    logger.warning(f"Error processing transaction: {str(tx_error)}")

            # Update statistics
            self.stats.increment_total()
            self.stats.increment_success()
            
            return {
                "success": True,
                "slot": block_data.get('slot', 0),
                "timestamp": block_data.get('blockTime', int(time.time())),
                "mint_addresses": mint_addresses,
                "statistics": {
                    **self.stats.get_current(),
                    "error_counts": dict(self.error_counts)
                }
            }

        except Exception as e:
            error_msg = f"Error processing mint result: {str(e)}"
            logger.error(error_msg)
            self.stats.increment_failure()
            self.stats.record_error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "mint_addresses": [],
                "statistics": {
                    **self.stats.get_current(),
                    "error_counts": dict(self.error_counts)
                }
            }

class QueryBatchStats:
    """Statistics for query batches."""
    
    def __init__(self):
        self.total_queries = 0
        self.successful_queries = 0
        self.failed_queries = 0
        self.skipped_queries = 0
        self.rate_limited_queries = 0
        self.error_types: Dict[str, int] = {}
        self.total_processed = 0
        self.large_transfers = 0
        self.inner_instructions = 0
        self.unique_programs = 0
        
    def increment_total(self):
        self.total_queries += 1
        
    def increment_success(self):
        self.successful_queries += 1
        
    def increment_failure(self):
        self.failed_queries += 1
        
    def increment_skipped(self):
        self.skipped_queries += 1
        
    def increment_rate_limited(self):
        self.rate_limited_queries += 1
        
    def record_error(self, error_type: str):
        if error_type not in self.error_types:
            self.error_types[error_type] = 0
        self.error_types[error_type] += 1
        
    def get_current(self) -> Dict[str, Any]:
        return {
            "total": self.total_queries,
            "successful": self.successful_queries,
            "failed": self.failed_queries,
            "skipped": self.skipped_queries,
            "rate_limited": self.rate_limited_queries,
            "error_types": self.error_types,
            "total_processed": self.total_processed,
            "large_transfers": self.large_transfers,
            "inner_instructions": self.inner_instructions,
            "unique_programs": self.unique_programs
        }

class SolanaQueryHandler:
    """Handler for Solana blockchain queries."""
    
    def __init__(self, connection_pool: Optional[SolanaConnectionPool] = None):
        if connection_pool is None:
            raise ValueError("Connection pool is required")
        self.connection_pool = connection_pool
        self.stats = QueryBatchStats()
        
        # Initialize response manager with config
        config = EndpointConfig(
            url=connection_pool.get_primary_endpoint(),
            requests_per_second=40.0,
            burst_limit=80,
            max_retries=3,
            retry_delay=1.0
        )
        
        self.response_manager = SolanaResponseManager(config)
        self.response_handler = ResponseHandler(self.response_manager)
        
        # Initialize handlers
        self.base_handler = BaseHandler()
        self.token_handler = TokenHandler()
        self.program_handler = ProgramHandler()
        self.mint_handler = MintHandler()
        
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
            client = await self.connection_pool.get_client()
            
            # Convert address to string if needed
            if isinstance(address, Pubkey):
                address = str(address)
                
            # Build params
            params = {
                "limit": limit
            }
            
            if start_slot is not None:
                params["minSlot"] = start_slot
            if end_slot is not None:
                params["maxSlot"] = end_slot
            if before:
                params["before"] = before
            if until:
                params["until"] = until
                
            response = await client.get_signatures_for_address(address, **params)
            if not response:
                return []
                
            return response
            
        except Exception as e:
            logger.error(f"Error getting signatures for {address}: {str(e)}")
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            return []
            
    async def get_program_transactions(
        self,
        program_id: Union[str, Pubkey],
        start_slot: Optional[int] = None,
        end_slot: Optional[int] = None,
        limit: int = 1000,
        batch_size: int = 10,
        batch_delay: float = 5.0
    ) -> List[Dict[str, Any]]:
        """Get transactions for a specific program"""
        try:
            # Convert program_id to Pubkey if it's a string
            if isinstance(program_id, str):
                program_id = Pubkey.from_string(program_id)
                
            # Get signatures for the slot range
            signatures = await self.get_signatures_for_address(
                address=program_id,
                start_slot=start_slot,
                end_slot=end_slot,
                limit=limit
            )
            
            if not signatures:
                return []
                
            # Get transaction data for each signature in batches
            transactions = []
            client = await self.connection_pool.get_client()
            
            for i in range(0, len(signatures), batch_size):
                batch = signatures[i:i + batch_size]
                logger.debug(f"Processing batch of {len(batch)} signatures")
                
                for sig_info in batch:
                    try:
                        tx_data = await client.get_transaction(sig_info["signature"])
                        if tx_data:
                            transactions.append(tx_data)
                            self.stats.increment_success()
                    except Exception as e:
                        logger.warning(f"Failed to get transaction {sig_info['signature']}: {str(e)}")
                        self.stats.increment_failure()
                        self.stats.record_error(type(e).__name__)
                        continue
                        
                # Add delay between batches to avoid rate limits
                if i + batch_size < len(signatures):
                    await asyncio.sleep(batch_delay)
                    
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting program transactions: {str(e)}")
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            return []
            
    async def get_account_info(
        self,
        address: Union[str, Pubkey],
        commitment: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get account information for a specific address"""
        try:
            client = await self.connection_pool.get_client()
            
            # Convert address to Pubkey if it's a string
            if isinstance(address, str):
                address = Pubkey.from_string(address)
                
            response = await client.get_account_info(address, commitment=commitment)
            if response:
                self.stats.increment_success()
                return response
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting account info for {address}: {str(e)}")
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception)),
        before_sleep=before_sleep_log(logger, logging.INFO)
    )
    async def get_block_with_retry(self, client: AsyncClient, slot: int) -> Optional[Dict[str, Any]]:
        """Get block with retry logic."""
        try:
            # Get block with commitment level
            block = await client.get_block(
                slot,
                commitment="confirmed"
            )
            
            # Add small delay between requests
            await asyncio.sleep(0.2)
            
            return block
            
        except Exception as e:
            if "429" in str(e):
                logger.warning(f"Rate limit hit for block {slot}, backing off...")
                await asyncio.sleep(1)  # Basic backoff
                return None
                
            if "Block not available" in str(e):
                logger.info(f"Block {slot} not available")
                return None
                
            logger.error(f"Error getting block {slot}: {e}")
            return None
            
    async def get_latest_block(self) -> Optional[Dict[str, Any]]:
        """Get latest block info with retries."""
        try:
            # Get current slot
            client = await self.connection_pool.get_client()
            slot = await client.get_slot()
            logger.debug(f"Got latest slot: {slot}")

            # Try multiple slots with larger offset for better availability
            for offset in range(50, 150, 10):  # Try slots 50-150 blocks back with step of 10
                target_slot = slot - offset
                logger.info(f"Trying block at slot {target_slot}")
                
                try:
                    block = await self.get_block_data(target_slot)
                    if block:
                        return {
                            'slot': target_slot,
                            'block': block
                        }
                except Exception as block_error:
                    logger.warning(f"Failed to get block at slot {target_slot}: {str(block_error)}")
                    await asyncio.sleep(0.5)  # Add delay between attempts
                    continue
            
            logger.error("Failed to get any recent blocks after trying multiple slots")
            return None

        except Exception as e:
            logger.error(f"Error getting latest block: {str(e)}")
            return None

    async def get_block_data(self, slot: int, handlers: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
        """Process block data with handlers"""
        start_time = time.time()
        
        try:
            block_data = await self.get_block(slot)
            if not block_data:
                logger.warning(f"No data found for block {slot}")
                return None
                
            # Process block with handlers
            results = {}
            for handler in handlers or []:
                handler_name = handler.__class__.__name__
                try:
                    results[handler_name] = await handler.process_block(block_data)
                except Exception as e:
                    logger.error(f"Error in {handler_name}: {str(e)}")
                    results[handler_name] = {"error": str(e)}
            
            # Log processing summary
            duration = time.time() - start_time
            logger.info(f"Block {slot} Processing Summary:")
            logger.info(f"  Duration: {duration:.2f}s")
            logger.info(f"  Handlers Processed: {len(handlers or [])}")
            
            # Log handler-specific stats at debug level
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Handler Statistics:")
                for handler_name, result in results.items():
                    if isinstance(result, dict) and 'statistics' in result:
                        stats = result['statistics']
                        logger.debug(f"  {handler_name}:")
                        for key, value in stats.items():
                            logger.debug(f"    {key}: {value}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing block {slot}: {str(e)}")
            return None

    async def get_recent_blocks(self, num_blocks: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent finalized blocks.

        Args:
            num_blocks: Number of recent blocks to retrieve

        Returns:
            List of block data dictionaries

        Raises:
            RPCError: If there's an error getting block data
        """
        try:
            # Get latest block
            latest_block = await self.get_latest_block()
            if not latest_block:
                logger.error("Failed to get latest block")
                self.stats.increment_failure()
                self.stats.record_error("no_latest_block")
                return []
                
            blocks = []
            
            # Start from 5 blocks behind latest to ensure finality
            start_slot = latest_block['slot'] - num_blocks
            
            for slot in range(start_slot, start_slot + num_blocks):
                block = await self.get_block_data(slot)
                if block:
                    blocks.append(block)
                    
            return blocks
            
        except Exception as e:
            logger.error(f"Error getting recent blocks: {str(e)}")
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            return []

    async def process_blocks(
        self,
        num_blocks: int = 10,
        start_slot: Optional[int] = None,
        end_slot: Optional[int] = None,
        commitment: Optional[str] = None,
        max_supported_transaction_version: Optional[int] = None,
        batch_size: int = 5,
        handlers: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """Process multiple blocks in parallel batches."""
        logger = logging.getLogger(__name__)
        
        try:
            # Get latest block if start/end not specified
            if start_slot is None or end_slot is None:
                latest_block = await self.get_latest_block()
                if latest_block is None:
                    logger.error("Failed to get latest block")
                    self.stats.increment_failure()
                    self.stats.record_error("no_latest_block")
                    return {
                        "success": False,
                        "error": "Failed to get latest block",
                        "result": None
                    }
                    
                # Start from latest block and work backwards
                latest_slot = latest_block['slot']
                current_slot = latest_slot - 20  # Start 20 blocks back for better availability
                available_slot = None
                
                # Try up to 20 slots to find an available block
                for _ in range(20):
                    client = await self.connection_pool.get_client()
                    block = await self.get_block_with_retry(client, current_slot)
                    if block:
                        available_slot = current_slot
                        break
                    current_slot -= 1
                
                if available_slot is None:
                    logger.error("Could not find available blocks")
                    self.stats.increment_failure()
                    self.stats.record_error("no_available_blocks")
                    return {
                        "success": False,
                        "error": "Could not find available blocks",
                        "result": None
                    }
                    
                # Set start and end slots based on available block
                if start_slot is None:
                    start_slot = available_slot
                if end_slot is None:
                    end_slot = start_slot + num_blocks - 1
                    
            # Process blocks in batches
            processed_blocks = []
            current_batch = []
            
            for slot in range(start_slot, end_slot + 1):
                current_batch.append(slot)
                
                if len(current_batch) >= batch_size or slot == end_slot:
                    # Process batch
                    batch_tasks = []
                    for batch_slot in current_batch:
                        task = asyncio.create_task(self.get_block_data(batch_slot, handlers))
                        batch_tasks.append(task)
                        
                    # Wait for batch to complete
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Process results
                    for result in batch_results:
                        if isinstance(result, Exception):
                            logger.error(f"Error processing block: {str(result)}")
                            continue
                        if result:
                            processed_blocks.append(result)
                            
                    current_batch = []
                    
            # Compile results
            mint_addresses = set()
            mint_operations = []
            errors = []
            
            for block in processed_blocks:
                if 'mint_addresses' in block:
                    mint_addresses.update(block['mint_addresses'])
                if 'mint_operations' in block:
                    mint_operations.extend(block['mint_operations'])
                if 'errors' in block:
                    errors.extend(block['errors'])
                    
            return {
                "success": True,
                "result": {
                    "mint_addresses": list(mint_addresses),
                    "mint_operations": mint_operations,
                    "processed_blocks": len(processed_blocks),
                    "total_blocks": num_blocks,
                    "errors": errors
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing blocks: {str(e)}")
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            return {
                "success": False,
                "error": str(e),
                "result": None
            }

    async def get_mints_from_recent_blocks(self, num_blocks: int = 10) -> Dict[str, Any]:
        """
        Get mint information from recent blocks, starting from 20 blocks behind latest
        to ensure we only process finalized and available blocks.
        
        Args:
            num_blocks: Number of recent blocks to analyze
            
        Returns:
            Dict containing mint information and statistics
            
        Raises:
            RPCError: If there's an error getting block data
        """
        try:
            # Get current slot with finalized commitment
            slot_info = await self.get_latest_block()
            if slot_info is None:
                return {
                    "success": False,
                    "error": "Failed to get latest block",
                    "result": None
                }

            # Start from 20 blocks behind to ensure blocks are available
            start_slot = max(0, slot_info['slot'] - 20)
            end_slot = start_slot + num_blocks - 1
            
            logger.info(f"Analyzing blocks from {start_slot} to {end_slot}")
            
            # Process blocks
            results = await self.process_blocks(
                num_blocks=num_blocks,
                start_slot=start_slot,
                end_slot=end_slot,
                commitment="finalized"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting mints from recent blocks: {str(e)}")
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            return {
                "success": False,
                "error": str(e),
                "result": None
            }

    async def process_block(
        self,
        slot: int,
    ) -> Dict[str, Any]:
        """Process a block at the given slot with comprehensive error handling and statistics tracking."""
        try:
            # Get block data with retry
            block_data = await self.get_block(slot)
            
            # Handle missing block
            if not block_data:
                logger.warning(f"Block {slot} not available")
                return {
                    "success": False,
                    "error": "Block not available",
                    "result": None
                }
            
            # Process block through response manager
            try:
                result = await self.response_manager.handle_response(block_data)
                if not result:
                    raise ValueError("Failed to process block data")
                    
                # Update block processing statistics
                self.stats.increment_success()
                return {
                    "success": True,
                    "slot": slot,
                    "result": result
                }
                
            except Exception as e:
                logger.error(f"Error processing block data: {str(e)}")
                self.stats.increment_errors()
                return {
                    "success": False,
                    "error": f"Failed to process block: {str(e)}",
                    "result": None
                }
                
        except Exception as e:
            logger.error(f"Error processing block {slot}: {str(e)}")
            self.stats.increment_errors()
            return {
                "success": False,
                "error": str(e),
                "result": None
            }

    async def get_block(
        self,
        slot: int,
        commitment: str = "finalized",
        max_supported_transaction_version: int = 0
    ) -> Dict[str, Any]:
        """Get block data with retries and comprehensive error handling."""
        try:
            # Track request
            self.stats.increment_total()
            
            # Get client from pool
            client = await self.connection_pool.get_client()
            if not client:
                logger.error("Failed to get client from connection pool")
                self.stats.increment_failure()
                self.stats.record_error("no_client")
                raise RPCError("No client available")
            
            # Prepare request with full transaction details
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "getBlock",
                "params": [
                    slot,
                    {
                        "encoding": "json",  
                        "maxSupportedTransactionVersion": max_supported_transaction_version,
                        "transactionDetails": "full",
                        "commitment": commitment,
                        "rewards": False  
                    }
                ]
            }
            
            # Execute request with retry logic
            response = await self._execute_with_retry(request)
            
            if not response:
                logger.error(f"No response for block {slot}")
                self.stats.increment_failure()
                self.stats.record_error("no_response")
                return None
                
            # Handle different response formats
            if isinstance(response, dict):
                # Check for error response
                if 'error' in response:
                    error_msg = response['error'].get('message', 'Unknown error')
                    logger.error(f"RPC error for block {slot}: {error_msg}")
                    self.stats.increment_failure()
                    self.stats.record_error("rpc_error")
                    return None
                    
                # Extract result
                result = response.get('result')
                if not result:
                    logger.error(f"No result in response for block {slot}")
                    self.stats.increment_failure()
                    self.stats.record_error("no_result")
                    return None
                    
                # Add slot to result
                result['slot'] = slot
                
                self.stats.increment_success()
                return result
            else:
                logger.error(f"Invalid response type for block {slot}: {type(response)}")
                self.stats.increment_failure()
                self.stats.record_error("invalid_response_type")
                return None
                
        except Exception as e:
            logger.error(f"Error getting block {slot}: {str(e)}")
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            return None

    async def get_multiple_blocks(
        self,
        start_slot: int,
        end_slot: int,
        commitment: str = "finalized",
        max_supported_transaction_version: int = 0,
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """Get multiple blocks in parallel with batching."""
        try:
            logger.info(f"Getting blocks from {start_slot} to {end_slot}")
            
            # Validate slot range
            if start_slot > end_slot:
                raise ValueError("Start slot must be less than or equal to end slot")
            
            # Create batches
            slots = range(start_slot, end_slot + 1)
            batches = [slots[i:i + batch_size] for i in range(0, len(slots), batch_size)]
            
            results = []
            for batch in batches:
                # Process batch in parallel
                tasks = [
                    self.get_block_data(
                        slot,
                        commitment=commitment,
                        max_supported_transaction_version=max_supported_transaction_version
                    )
                    for slot in batch
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle results
                for slot, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to get block {slot}: {str(result)}")
                        results.append({
                            "slot": slot,
                            "success": False,
                            "error": str(result)
                        })
                    else:
                        results.append({
                            "slot": slot,
                            "success": True,
                            "result": result
                        })
                
            return results
            
        except Exception as e:
            logger.error(f"Error getting multiple blocks: {str(e)}")
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            raise

    async def _execute_with_retry(
        self,
        request: Dict[str, Any],
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 8.0,
        backoff_factor: float = 2.0
    ) -> Any:
        """Execute RPC request with exponential backoff retry."""
        last_error = None
        delay = initial_delay

        for attempt in range(max_retries):
            try:
                # Get client from pool
                client = await self.connection_pool.get_client()
                if not client:
                    raise RPCError("No client available")
                
                # Execute request
                response = await client._make_rpc_call(request['method'], request['params'])
                
                # Handle different response types based on method
                if request['method'] == 'getSlot':
                    if not isinstance(response, (int, dict)):
                        logger.error(f"Invalid slot response type: {type(response)}")
                        raise RPCError("Invalid slot response")
                    # Handle both direct int response and JSON-RPC response
                    if isinstance(response, dict):
                        if 'result' in response:
                            return response['result']
                        elif 'error' in response:
                            raise RPCError(f"RPC error: {response['error']}")
                    return response
                    
                # For other methods, expect dictionary response
                if not isinstance(response, dict):
                    logger.error(f"Invalid response type: {type(response)}")
                    raise RPCError("Invalid response structure")
                
                # Check for RPC error
                if 'error' in response:
                    error = response['error']
                    error_msg = error.get('message', str(error))
                    error_code = error.get('code', 'unknown')
                    raise RPCError(f"RPC error {error_code}: {error_msg}")
                
                # Check for result
                if 'result' not in response:
                    raise RPCError("No result in response")
                
                # For getBlock, handle null result (block not available)
                if request['method'] == 'getBlock' and response['result'] is None:
                    return None
                
                # Process response with response manager
                processed_response = await self.response_manager.handle_response(response)
                return processed_response

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = min(delay * backoff_factor, max_delay)
                    logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"All retry attempts failed: {str(e)}")
                    if isinstance(e, RPCError):
                        raise
                    raise RPCError(f"Request failed after {max_retries} retries: {str(last_error)}")

    async def get_multiple_blocks(
        self,
        start_slot: int,
        end_slot: int,
        commitment: str = "finalized",
        max_supported_transaction_version: int = 0,
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """Get multiple blocks in parallel with batching."""
        try:
            logger.info(f"Getting blocks from {start_slot} to {end_slot}")
            
            # Validate slot range
            if start_slot > end_slot:
                raise ValueError("Start slot must be less than or equal to end slot")
            
            # Create batches
            slots = range(start_slot, end_slot + 1)
            batches = [slots[i:i + batch_size] for i in range(0, len(slots), batch_size)]
            
            results = []
            for batch in batches:
                # Process batch in parallel
                tasks = [
                    self.get_block_data(
                        slot,
                        commitment=commitment,
                        max_supported_transaction_version=max_supported_transaction_version
                    )
                    for slot in batch
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle results
                for slot, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to get block {slot}: {str(result)}")
                        results.append({
                            "slot": slot,
                            "success": False,
                            "error": str(result)
                        })
                    else:
                        results.append({
                            "slot": slot,
                            "success": True,
                            "result": result
                        })
                
            return results
            
        except Exception as e:
            logger.error(f"Error getting multiple blocks: {str(e)}")
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            raise

    async def extract_mint_data(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract mint-related data from a block."""
        try:
            # Initialize result sets
            mint_addresses = set()
            pump_token_addresses = set()
            mint_operations = []
            
            # Get slot from block data
            slot = block_data.get("slot")
            if not slot:
                logger.warning("Block data missing slot")
                return None
                
            # Get transactions
            transactions = block_data.get("transactions", [])
            if not transactions:
                return {
                    "mint_addresses": [],
                    "pump_token_addresses": [],
                    "mint_operations": [],
                    "slot": slot
                }
                
            # Process each transaction
            for tx_index, tx in enumerate(transactions):
                try:
                    # Skip invalid transactions
                    if not isinstance(tx, dict):
                        continue
                        
                    # Get transaction data and metadata
                    if "transaction" in tx:
                        tx_data = tx["transaction"]
                        meta = tx.get("meta", {})
                    else:
                        tx_data = tx
                        meta = tx.get("meta", {})
                        
                    # Skip if no transaction data
                    if not tx_data:
                        continue
                        
                    # Extract message data
                    if isinstance(tx_data, dict):
                        message = tx_data.get("message", {})
                        if not message:
                            continue
                            
                        # Get account keys
                        account_keys = message.get("accountKeys", [])
                        if not account_keys:
                            continue
                            
                        # Convert account keys to strings if needed
                        account_keys = [str(key) if not isinstance(key, str) else key for key in account_keys]
                        
                        # Look for mint instructions
                        instructions = message.get("instructions", [])
                        for ix in instructions:
                            program_id = ix.get("programId")
                            if not program_id:
                                continue
                                
                            # Check for token program instructions
                            if program_id in [
                                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token Program
                                "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"   # Token2022 Program
                            ]:
                                # Get accounts from instruction
                                accounts = ix.get("accounts", [])
                                if not accounts:
                                    continue
                                    
                                if isinstance(accounts[0], int):
                                    # Convert account indices to addresses
                                    try:
                                        accounts = [account_keys[idx] for idx in accounts if idx < len(account_keys)]
                                    except (IndexError, TypeError) as e:
                                        logger.debug(f"Error converting account indices: {str(e)}")
                                        continue
                                        
                                if not accounts:
                                    continue
                                    
                                # Get instruction data
                                data = ix.get("data", "")
                                if not data:
                                    continue
                                    
                                # Check for mint initialization
                                if any(op in data.lower() for op in [
                                    "initializemint",
                                    "createmint",
                                    "initialize_mint",
                                    "create_mint"
                                ]):
                                    try:
                                        # First account is usually the mint
                                        mint_address = accounts[0]
                                        if not isinstance(mint_address, str):
                                            logger.debug(f"Invalid mint address format: {mint_address}")
                                            continue
                                            
                                        # Skip known token mints
                                        if mint_address in [
                                            "So11111111111111111111111111111111111111112",  # Wrapped SOL
                                            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                                            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
                                            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # USDT-2
                                            "7i5KKsX2weiTkry7jA4ZwSJ4zRWqW2PPkiupCAMMQCLQ",  # Bonk
                                        ]:
                                            continue
                                            
                                        mint_addresses.add(mint_address)
                                        mint_operations.append({
                                            "address": mint_address,
                                            "program": program_id,
                                            "data": data,
                                            "accounts": accounts,
                                            "slot": slot,
                                        })
                                    except (IndexError, TypeError, AttributeError) as e:
                                        logger.debug(f"Error processing mint address: {str(e)}")
                                        continue
                except Exception as e:
                    logger.error(f"Error processing transaction {tx_index}: {str(e)}")
                    continue
                    
            return {
                "mint_addresses": list(mint_addresses),
                "pump_token_addresses": list(pump_token_addresses),
                "mint_operations": mint_operations,
                "slot": slot
            }
            
        except Exception as e:
            logger.error(f"Error extracting mint data: {str(e)}")
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            return None

    async def analyze_new_mints(self, num_blocks: int = 1) -> Dict[str, Any]:
        """Analyze new mints from recent blocks"""
        try:
            # Get latest block
            latest_block = await self.get_latest_block()
            if not latest_block:
                logger.error("Failed to get latest block")
                self.stats.increment_failure()
                self.stats.record_error("no_latest_block")
                return {
                    "success": False,
                    "error": "Failed to get latest block",
                    "mint_addresses": [],
                    "pump_token_addresses": [],
                    "mint_operations": [],
                    "blocks_processed": 0
                }
                
            # Get slot from latest block
            if not isinstance(latest_block, dict) or "slot" not in latest_block:
                logger.error("Invalid latest block format - missing slot")
                return {
                    "success": False,
                    "error": "Invalid latest block format",
                    "mint_addresses": [],
                    "pump_token_addresses": [],
                    "mint_operations": [],
                    "blocks_processed": 0
                }
                
            # Calculate block range
            current_slot = latest_block["slot"]
            buffer = 5  # Look at blocks slightly behind to ensure availability
            end_block = current_slot - buffer  # End a few blocks behind current
            start_block = end_block - num_blocks + 1  # Start one block before end_block based on requested blocks
            
            # Process blocks
            blocks_processed = 0
            all_mint_addresses = set()
            all_pump_tokens = set()
            all_mint_operations = []
            errors = []
            
            for slot in range(start_block, end_block + 1):
                try:
                    # Get block data
                    block = await self.get_block_data(slot)
                    if not block:
                        logger.warning(f"No data for block {slot}")
                        continue
                        
                    # Extract mint addresses
                    try:
                        result = await self.extract_mint_data(block)
                        if result:
                            all_mint_addresses.update(result["mint_addresses"])
                            all_pump_tokens.update(result.get("pump_token_addresses", []))
                            all_mint_operations.extend(result["mint_operations"])
                            blocks_processed += 1
                    except Exception as e:
                        error_msg = f"Error extracting mints from block {slot}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Error processing block {slot}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    
            return {
                "success": True,
                "error": None,
                "mint_addresses": list(all_mint_addresses),
                "pump_token_addresses": list(all_pump_tokens),
                "mint_operations": all_mint_operations,
                "blocks_processed": blocks_processed,
                "start_block": start_block,
                "end_block": end_block,
                "errors": errors
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error analyzing new mints: {error_msg}")
            self.stats.increment_failure()
            self.stats.record_error(type(e).__name__)
            return {
                "success": False,
                "error": error_msg,
                "mint_addresses": [],
                "pump_token_addresses": [],
                "mint_operations": [],
                "blocks_processed": 0,
                "errors": [error_msg]
            }

    async def analyze_blocks(self, num_blocks: int = 1, commitment: str = "confirmed") -> Dict[str, Any]:
        """Analyze recent blocks for mint operations"""
        try:
            latest_slot = await self.get_latest_slot()
            if not latest_slot:
                return {"success": False, "error": "Failed to get latest slot"}

            results = {
                "success": True,
                "result": {
                    "mint_addresses": set(),
                    "mint_operations": [],
                    "mint_types": {
                        "new_mints": 0,
                        "mint_to": 0,
                        "ata_created": 0
                    },
                    "tx_types": set(),
                    "processed_blocks": 0,
                    "total_blocks": num_blocks,
                    "errors": [],
                    "statistics": self.stats.get_current()
                }
            }

            for i in range(num_blocks):
                target_slot = latest_slot - 50 - i  # Skip very recent blocks to avoid uncle blocks
                logger.info(f"Trying block at slot {target_slot}")
                
                block_data = await self.get_block_data(target_slot)
                if not block_data:
                    logger.warning(f"Block {target_slot} not available")
                    continue

                # Process block with handlers
                handler_result = await self.mint_handler.process(block_data)
                if handler_result.get('success'):
                    results['result']['processed_blocks'] += 1
                    results['result']['mint_addresses'].update(handler_result.get('mint_addresses', []))
                    results['result']['mint_operations'].extend(handler_result.get('mint_operations', []))
                    results['result']['tx_types'].update(handler_result.get('tx_types', []))
                    
                    # Update mint type counters
                    mint_types = handler_result.get('mint_types', {})
                    results['result']['mint_types']['new_mints'] += mint_types.get('new_mints', 0)
                    results['result']['mint_types']['mint_to'] += mint_types.get('mint_to', 0)
                    results['result']['mint_types']['ata_created'] += mint_types.get('ata_created', 0)
                else:
                    results['result']['errors'].append(f"Failed to process block {target_slot}: {handler_result.get('error')}")

            # Convert sets to lists for JSON serialization
            results['result']['mint_addresses'] = list(results['result']['mint_addresses'])
            results['result']['tx_types'] = list(results['result']['tx_types'])
            
            return results

        except Exception as e:
            logger.error(f"Error analyzing blocks: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

__all__ = [
    'MintResponseHandler',
    'MintHandler',
    'QueryBatchStats',
    'SolanaQueryHandler'
]
