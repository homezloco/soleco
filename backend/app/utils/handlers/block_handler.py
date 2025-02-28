"""
Block handler for processing Solana block data.
"""

import logging
import time
import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple
from .base_handler import BaseHandler
from ..solana_error import RPCError

logger = logging.getLogger(__name__)

class BlockProcessingStats:
    """Statistics tracker for block processing."""
    
    def __init__(self):
        self.total_blocks = 0
        self.total_errors = 0
        self.error_counts: Dict[str, int] = {}
        self.skipped_blocks = 0
        
    def increment_total(self):
        """Increment total blocks processed."""
        self.total_blocks += 1
        
    def increment_skipped(self):
        """Increment skipped blocks count."""
        self.skipped_blocks += 1
        
    def update_error_count(self, error_type: str):
        """Update error count for a specific error type."""
        self.total_errors += 1
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
    def get_current(self) -> Dict[str, Any]:
        """Get current statistics."""
        return {
            "total_blocks": self.total_blocks,
            "total_errors": self.total_errors,
            "skipped_blocks": self.skipped_blocks,
            "error_counts": self.error_counts
        }

class BlockHandler(BaseHandler):
    """Handler for processing Solana block data."""
    
    def __init__(self):
        super().__init__()
        self.program_ids: Set[str] = set()
        self.instruction_count: int = 0
        self.transaction_count: int = 0
        self.stats = BlockProcessingStats()
        self._block_cache: Dict[int, Dict[str, Any]] = {}
        self._max_retries = 3
        self._retry_delay = 1.0

    async def wait_for_block_availability(self, block_num: int, max_wait: int = 10) -> bool:
        """Wait for a block to become available."""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                client = await self.get_client()
                slot = await client.get_slot()
                if slot - block_num > 150:  # Block should be available after 150 confirmations
                    return True
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"Error checking slot for block {block_num}: {str(e)}")
                await asyncio.sleep(1)
        return False

    async def process_result(self, result: Dict[str, Any], block_num: int) -> Optional[Dict[str, Any]]:
        """Process a block result and extract relevant information."""
        try:
            # Check if block is available
            if not result:
                is_available = await self.wait_for_block_availability(block_num)
                if not is_available:
                    logger.warning(f"Block {block_num} not available after waiting")
                    self.stats.increment_skipped()
                    return None

            if not isinstance(result, dict):
                logger.warning(f"Block {block_num} response is invalid type: {type(result)}")
                return None

            # Handle missing transactions field
            if "transactions" not in result:
                if "blockTime" in result:
                    logger.info(f"Block {block_num} missing transactions field, but has blockTime")
                    return {
                        "block_num": block_num,
                        "block_time": result["blockTime"],
                        "transactions": []
                    }
                else:
                    logger.warning(f"Block {block_num} missing both transactions and blockTime fields")
                    return None

            # Extract block time
            block_time = result.get("blockTime")
            if not block_time:
                logger.warning(f"Block {block_num} missing blockTime field")
                return None

            # Process transactions
            processed_txs = []
            for tx in result.get("transactions", []):
                try:
                    if not isinstance(tx, dict):
                        continue

                    meta = tx.get("meta")
                    if not meta:
                        continue

                    # Skip failed transactions
                    if meta.get("err") is not None:
                        continue

                    transaction = tx.get("transaction")
                    if not transaction:
                        continue

                    # Process transaction
                    processed_tx = self._process_transaction(transaction, meta)
                    if processed_tx:
                        processed_txs.append(processed_tx)

                except Exception as e:
                    logger.warning(f"Error processing transaction in block {block_num}: {str(e)}")
                    continue

            # Update stats
            self.stats.increment_total()
            
            return {
                "block_num": block_num,
                "block_time": block_time,
                "transactions": processed_txs
            }

        except Exception as e:
            logger.error(f"Error processing block {block_num}: {str(e)}")
            self.stats.update_error_count(type(e).__name__)
            return None

    def _process_transaction(self, transaction: Dict[str, Any], meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single transaction and extract key information."""
        try:
            # Extract message and instructions
            message = transaction.get('message', {})
            if not message:
                return None

            # Get account keys and instructions
            account_keys = message.get('accountKeys', [])
            instructions = message.get('instructions', [])
            
            if not account_keys or not instructions:
                return None

            # Track program IDs
            for instruction in instructions:
                program_idx = instruction.get('programIdIndex')
                if program_idx is not None and program_idx < len(account_keys):
                    program_id = account_keys[program_idx]
                    self.program_ids.add(program_id)

            self.instruction_count += len(instructions)
            self.transaction_count += 1

            return {
                "success": True,
                "data": {
                    "signature": transaction.get('signatures', [''])[0],
                    "slot": meta.get('slot'),
                    "blockTime": meta.get('blockTime'),
                    "instructions": instructions,
                    "accounts": account_keys,
                    "program_ids": list(self.program_ids)
                }
            }

        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            return None

    def log_statistics(self):
        """Log block processing statistics."""
        try:
            logger.info("Block Processing Statistics:")
            logger.info(f"  Program IDs Found: {len(self.program_ids)}")
            logger.info("  Program IDs List:")
            for pid in self.program_ids:
                logger.info(f"    - {pid}")
            logger.info(f"  Total Instructions: {self.instruction_count}")
            logger.info(f"  Total Transactions: {self.transaction_count}")

        except Exception as e:
            logger.error(f"Error logging statistics: {str(e)}")

    def _get_statistics(self) -> Dict[str, Any]:
        """Get current statistics as a dictionary."""
        return {
            "program_ids": list(self.program_ids),
            "instruction_count": self.instruction_count,
            "transaction_count": self.transaction_count
        }
