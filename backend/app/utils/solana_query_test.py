"""
Solana query module for handling blockchain data queries.
This module provides query handlers and utilities for fetching and processing Solana blockchain data.
"""

from typing import Dict, List, Optional, Any, Union, Tuple, Set
from solders.pubkey import Pubkey
from solders.signature import Signature
import logging
import asyncio
from datetime import datetime
from collections import defaultdict
import time
import uuid
from fastapi import Depends

from .solana_rpc import SolanaConnectionPool
from .solana_errors import RetryableError, RPCError
from .response_base import ResponseHandler
from .handlers.mint_response_handler import MintResponseHandler

logger = logging.getLogger(__name__)

# Global connection pool
_connection_pool: Optional[SolanaConnectionPool] = None

async def initialize_connection_pool():
    """Initialize the global connection pool"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = SolanaConnectionPool()
        await _connection_pool.initialize()
    return _connection_pool

async def get_connection_pool():
    """Get the global connection pool, initializing it if necessary"""
    if _connection_pool is None:
        await initialize_connection_pool()
    return _connection_pool

class QueryBatchStats:
    """Track statistics for query batches"""
    
    def __init__(self):
        self.total_queries = 0
        self.error_queries = 0
        self.error_counts = defaultdict(int)
        self.skipped_queries = 0
        self.start_time = datetime.now()
        
    def log_summary(self):
        """Log a summary of the batch processing statistics"""
        duration = (datetime.now() - self.start_time).total_seconds()
        logger.info(
            f"Query Batch Stats:\n"
            f"Total Queries: {self.total_queries}\n"
            f"Error Queries: {self.error_queries}\n"
            f"Skipped Queries: {self.skipped_queries}\n"
            f"Duration: {duration:.2f}s"
        )
        if self.error_counts:
            logger.info("Error breakdown:")
            for error_type, count in self.error_counts.items():
                logger.info(f"  {error_type}: {count}")

class ResponseHandler:
    """Base class for handling Solana RPC responses"""
    
    def __init__(self):
        self.stats = QueryBatchStats()
        
    def handle_response(self, response: Dict[str, Any]) -> Any:
        """
        Handle a raw RPC response
        
        Args:
            response: The raw RPC response
            
        Returns:
            Processed result
        """
        if "error" in response:
            error = response["error"]
            logger.error(f"RPC error: {error}")
            raise RPCError(str(error))
            
        if "result" not in response:
            logger.error("No result in response")
            raise RPCError("No result in response")
            
        try:
            result = self.process_result(response["result"])
            self.stats.total_queries += 1
            return result
        except Exception as e:
            self.stats.error_queries += 1
            self.stats.error_counts[type(e).__name__] += 1
            raise
            
    def process_result(self, result: Any) -> Any:
        """
        Process the result portion of the response
        
        Args:
            result: The result to process
            
        Returns:
            Processed result
        """
        raise NotImplementedError("Subclasses must implement process_result")

class SolanaQueryHandler:
    """Handler for Solana blockchain queries"""
    
    def __init__(self, connection_pool: Optional[SolanaConnectionPool] = Depends(get_connection_pool)):
        if connection_pool is None:
            raise ValueError("Connection pool is required")
        self.connection_pool = connection_pool
        self.stats = QueryBatchStats()
        
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
            self.stats.error_queries += 1
            self.stats.error_counts[type(e).__name__] += 1
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
                            self.stats.total_queries += 1
                    except Exception as e:
                        logger.warning(f"Failed to get transaction {sig_info['signature']}: {str(e)}")
                        self.stats.error_queries += 1
                        self.stats.error_counts[type(e).__name__] += 1
                        continue
                        
                # Add delay between batches to avoid rate limits
                if i + batch_size < len(signatures):
                    await asyncio.sleep(batch_delay)
                    
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting program transactions: {str(e)}")
            self.stats.error_queries += 1
            self.stats.error_counts[type(e).__name__] += 1
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
                self.stats.total_queries += 1
                return response
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting account info for {address}: {str(e)}")
            self.stats.error_queries += 1
            self.stats.error_counts[type(e).__name__] += 1
            return None

    async def get_block_with_retry(self, slot: int, commitment: str = "finalized") -> Optional[Dict[str, Any]]:
        """
        Get block data with retries
        
        Args:
            slot: Block slot number
            commitment: Commitment level (finalized, confirmed, processed)
            
        Returns:
            Block data if successful, None otherwise
        """
        max_retries = 3
        retry_delay = 1.0
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                client = await self.connection_pool.get_client()
                block = await client.get_block(slot, commitment=commitment)
                return block
            except Exception as e:
                logger.error(f"Error getting block {slot}: {str(e)}")
                if retry_count < max_retries - 1:
                    logger.info(f"Retrying block {slot} after {retry_delay}s delay")
                    await asyncio.sleep(retry_delay)
                else:
                    raise RPCError(f"Failed to get block {slot} after {max_retries} attempts: {e}")
                    
            retry_count += 1
            
        return None

    async def get_latest_block(self) -> Dict[str, Any]:
        """
        Get the latest available block.
        
        Returns:
            Dict containing block slot and other metadata
            
        Raises:
            RPCError: If there's an error getting the block
        """
        try:
            client = await self.connection_pool.get_client()
            slot = await client.get_slot(commitment="confirmed")
            
            # Try getting blocks starting from 20 slots behind to ensure availability
            # Add delay between attempts to avoid rate limiting
            for offset in range(20, 0, -1):
                target_slot = slot - offset
                try:
                    block = await self.get_block_with_retry(target_slot, commitment="confirmed")
                    if block:
                        logger.info(f"Successfully retrieved block at slot {target_slot}")
                        return {
                            'slot': target_slot,
                            'block': block
                        }
                except Exception as block_error:
                    logger.warning(f"Failed to get block at slot {target_slot}: {str(block_error)}")
                    await asyncio.sleep(0.5)  # Add delay between attempts
                    continue
            
            logger.error("Failed to get any recent blocks after trying multiple slots")
            raise RPCError("Failed to get latest block data")
        except Exception as e:
            logger.error(f"Error getting latest block: {str(e)}")
            raise RPCError(f"Failed to get latest block: {str(e)}")

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
            latest_block = await self.get_latest_block()
            if not latest_block:
                raise RPCError("Failed to get latest block")

            blocks = []
            
            # Start from 5 blocks behind latest to ensure finality
            start_slot = latest_block['slot'] - num_blocks - 5
            
            for slot in range(start_slot, start_slot + num_blocks):
                block = await self.get_block_with_retry(slot)
                if block:
                    blocks.append(block)
                    
            return blocks
            
        except Exception as e:
            logger.error(f"Error getting recent blocks: {e}")
            raise RPCError("Failed to get recent blocks") from e

    async def get_mints_from_recent_blocks(self, num_blocks: int = 10) -> Dict[str, Any]:
        """
        Get mint information from recent blocks, starting from 5 blocks behind latest
        to ensure we only process finalized blocks.
        
        Args:
            num_blocks: Number of recent blocks to analyze
            
        Returns:
            Dict containing mint information and statistics
            
        Raises:
            RPCError: If there's an error getting block data
        """
        if not self.connection_pool:
            raise RPCError("Connection pool not initialized")

        client = await self.connection_pool.get_client()
        if not client:
            raise RPCError("Failed to get Solana client")

        # Get current slot with finalized commitment
        try:
            slot = await self.get_latest_block()
            if slot is None:
                return {
                    "mints": [],
                    "total_mints": 0,
                    "blocks_analyzed": 0,
                    "latest_block": None,
                    "error": "Failed to get current slot"
                }
            logger.info(f"Current slot: {slot['slot']}")
        except Exception as e:
            logger.error(f"Failed to get current slot: {e}")
            raise RPCError("Failed to get current slot")

        # Start from 5 blocks behind current to ensure finalization
        start_block = slot['slot'] - 5
        
        results = []
        blocks_analyzed = 0
        errors = []
        
        for i in range(num_blocks):
            try:
                target_slot = start_block - i
                logger.info(f"Processing block at slot {target_slot}")
                
                # Get block with retry logic
                block = await self.get_block_with_retry(target_slot)
                
                if block:
                    blocks_analyzed += 1
                    mints = await self._extract_mints_from_block(block)
                    for mint in mints:
                        mint['slot'] = target_slot  # Ensure slot is recorded
                    results.extend(mints)
                else:
                    error_msg = f"Block {target_slot} not available"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    
                # Add a small delay between blocks
                await asyncio.sleep(0.2)
                
            except Exception as e:
                error_msg = f"Error analyzing block {start_block - i}: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue

        return {
            "mints": results,
            "total_mints": len(results),
            "blocks_analyzed": blocks_analyzed,
            "latest_block": start_block,
            "current_slot": slot['slot'],
            "errors": errors,
            "error": None if blocks_analyzed > 0 else "No valid blocks found"
        }

    async def process_block(
        self,
        slot: int,
        response_handler: Optional[ResponseHandler] = None
    ) -> Dict[str, Any]:
        """Process a block and extract relevant data using response handler"""
        try:
            # Get client and validate
            client = await self.connection_pool.get_client()
            if not client:
                logger.error("Failed to get Solana client")
                return {
                    "success": False,
                    "error": "Failed to get Solana client",
                    "result": None
                }
            
            # Get block data with retry
            block = await self.get_block_with_retry(slot)
            if not block:
                return {
                    "success": False,
                    "error": f"Block {slot} not available",
                    "result": None
                }
                
            # Process block with handler if provided
            if response_handler:
                try:
                    # Create a proper RPC response format
                    rpc_response = {
                        "jsonrpc": "2.0",
                        "result": block,
                        "id": str(uuid.uuid4())
                    }
                    
                    # Call handle_response with the formatted response
                    result = response_handler.handle_response(rpc_response)
                    return {
                        "success": True,
                        "error": None,
                        "result": result
                    }
                except Exception as e:
                    logger.error(f"Error processing block {slot}: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Error processing block: {str(e)}",
                        "result": None
                    }
            
            # Default processing if no handler provided
            return {
                "success": True,
                "error": None,
                "result": block
            }
            
        except Exception as e:
            logger.error(f"Error processing block {slot}: {str(e)}")
            return {
                "success": False,
                "error": f"Error processing block: {str(e)}",
                "result": None
            }

    async def process_blocks(
        self,
        start_block: int,
        end_block: int,
        handler: Optional[ResponseHandler] = None,
        batch_size: int = 10,
        batch_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        Process a range of blocks with a response handler
        
        Args:
            start_block: Starting block number
            end_block: Ending block number
            handler: Response handler for processing blocks
            batch_size: Number of blocks to process in each batch
            batch_delay: Delay between batches in seconds
            
        Returns:
            Dict containing processing results and any errors
        """
        if not self.connection_pool:
            logger.error("No connection pool available")
            raise ValueError("Connection pool required")
            
        if not handler:
            logger.error("No response handler provided")
            raise ValueError("Response handler required")
            
        if start_block > end_block:
            logger.error(f"Invalid block range: {start_block} > {end_block}")
            raise ValueError("Start block must be <= end block")
            
        try:
            # Get client from pool
            client = await self.connection_pool.get_client()
            if not client:
                logger.error("Failed to get client from pool")
                raise RPCError("No client available")
                
            # Process blocks in batches
            results = []
            current_block = start_block
            blocks_processed = 0
            
            while current_block <= end_block:
                batch_end = min(current_block + batch_size - 1, end_block)
                
                try:
                    # Get block with retry logic and commitment
                    block_data = await self.get_block_with_retry(current_block, commitment="confirmed")
                    
                    if block_data:
                        # Process block with handler
                        result = handler.handle_response({
                            "jsonrpc": "2.0",
                            "result": block_data
                        })
                        if result and result.get("success", False):
                            results.append(result)
                            blocks_processed += 1
                            logger.debug(f"Successfully processed block {current_block}")
                    else:
                        logger.warning(f"No data returned for block {current_block}")
                    
                except Exception as e:
                    logger.error(f"Error processing block {current_block}: {str(e)}")
                    
                # Move to next batch
                current_block = batch_end + 1
                if current_block <= end_block:
                    await asyncio.sleep(batch_delay)
                    
            # Return combined results with all found addresses
            return {
                "success": True,
                "error": None,
                "results": results,
                "blocks_processed": blocks_processed,
                "start_block": start_block,
                "end_block": end_block,
                "mint_addresses": list(handler.mint_addresses) if hasattr(handler, 'mint_addresses') else [],
                "pump_token_addresses": list(handler.pump_tokens) if hasattr(handler, 'pump_tokens') else []
            }
            
        except Exception as e:
            logger.error(f"Error processing blocks: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "blocks_processed": 0,
                "start_block": start_block,
                "end_block": end_block
            }

    async def _extract_mints_from_block(self, block: Dict[str, Any]) -> list:
        """Extract mint addresses from a block"""
        mints = []
        transactions = block.get('transactions', [])
        
        for tx_obj in transactions:
            try:
                # Get transaction data and meta from the correct location
                tx = None
                meta = None
                
                if isinstance(tx_obj, dict):
                    # Handle nested transaction data
                    if 'transaction' in tx_obj:
                        tx = tx_obj['transaction']
                    else:
                        tx = tx_obj
                        
                    meta = tx_obj.get('meta', {})
                    
                    # Handle case where message is at root level
                    if 'message' in tx:
                        message = tx['message']
                    else:
                        message = tx
                else:
                    # Handle Solders object
                    tx = getattr(tx_obj, 'transaction', None)
                    meta = getattr(tx_obj, 'meta', None)
                    message = getattr(tx, 'message', None) if tx else None

                if not message:
                    continue

                # Check pre-token balances from meta
                if meta:
                    pre_token_balances = meta.get('preTokenBalances', [])
                    for balance in pre_token_balances:
                        if balance.get('mint'):
                            mints.append({
                                'address': balance['mint'],
                                'program': 'pre_token_balance',
                                'slot': block.get('slot'),
                                'timestamp': block.get('blockTime')
                            })

                # Get instructions from message
                instructions = message.get('instructions', []) if isinstance(message, dict) else getattr(message, 'instructions', [])
                
                # Process each instruction
                for inst in instructions:
                    if isinstance(inst, dict):
                        program_id = inst.get('programId')
                        accounts = inst.get('accounts', [])
                        data = inst.get('data', '')
                    else:
                        program_id = getattr(inst, 'program_id', None)
                        accounts = getattr(inst, 'accounts', [])
                        data = getattr(inst, 'data', '')

                    # Check for mint-related instructions
                    if accounts and ('mint' in str(data).lower() or program_id in [
                        'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
                        'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'   # Token 2022 Program
                    ]):
                        mint_address = accounts[0]
                        if mint_address:
                            mints.append({
                                'address': str(mint_address),
                                'program': str(program_id) if program_id else 'unknown',
                                'slot': block.get('slot'),
                                'timestamp': block.get('blockTime')
                            })

            except Exception as e:
                logger.warning(f"Error processing transaction in block {block.get('slot')}: {e}")
                continue
                
        return mints
