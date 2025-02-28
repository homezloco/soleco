"""
Block handler for processing Solana block data.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Set
from .base_handler import BaseHandler
from ..solana_error import RPCError
import base58

logger = logging.getLogger(__name__)

class BlockHandler(BaseHandler):
    """Handler for processing Solana block data."""
    
    def __init__(self):
        super().__init__()
        self.program_ids: Set[str] = set()
        self.instruction_count: int = 0
        self.transaction_count: int = 0
        self.mint_addresses: Set[str] = set()
        self.new_mint_addresses: Set[str] = set()
        self.pump_tokens: Set[str] = set()
        self.stats = BlockProcessingStats()

    @staticmethod
    def is_valid_base58(address: str) -> bool:
        try:
            decoded = base58.b58decode(address)
            return len(decoded) == 32  # Solana public keys are 32 bytes
        except Exception:
            return False

    async def process_result(self, result: Any) -> Dict[str, Any]:
        """Process block data with comprehensive error handling."""
        try:
            if not result or not isinstance(result, dict):
                logger.warning("Invalid result format")
                return {
                    "success": False,
                    "error": "Invalid result format",
                    "data": None,
                    "statistics": self.stats.get_current()
                }

            # Extract block data
            block_data = result.get('result', {})
            if not isinstance(block_data, dict):
                logger.warning("Invalid block data format")
                return {
                    "success": False,
                    "error": "Invalid block data format",
                    "data": None,
                    "statistics": self.stats.get_current()
                }

            # Reset counters
            self.program_ids.clear()
            self.instruction_count = 0
            self.transaction_count = 0
            self.mint_addresses.clear()
            self.new_mint_addresses.clear()

            # Process transactions
            transactions = block_data.get('transactions', [])
            if not transactions:
                logger.debug("No transactions found in block")
                self.log_statistics()
                return {
                    "success": True,
                    "data": {
                        "slot": block_data.get('slot', 0),
                        "timestamp": block_data.get('blockTime', int(time.time())),
                        "transactions": [],
                        "statistics": self._get_statistics()
                    },
                    "statistics": self.stats.get_current()
                }

            # Process each transaction
            processed_txs = []
            for tx in transactions:
                try:
                    processed_tx = await self.process_transaction(tx)
                    if processed_tx:
                        processed_txs.append(processed_tx)
                        self.transaction_count += 1
                        self.instruction_count += processed_tx.get('instruction_count', 0)
                        self.stats.increment_processed()
                except Exception as tx_error:
                    logger.warning(f"Error processing transaction: {str(tx_error)}")
                    self.stats.update_error_count(type(tx_error).__name__)

            # Log statistics
            self.log_statistics()

            # Update statistics
            self.stats.increment_total()
            
            return {
                "success": True,
                "data": {
                    "slot": block_data.get('slot', 0),
                    "timestamp": block_data.get('blockTime', int(time.time())),
                    "transactions": processed_txs,
                    "statistics": self._get_statistics()
                },
                "statistics": self.stats.get_current()
            }

        except Exception as e:
            error_msg = f"Error processing block result: {str(e)}"
            logger.error(error_msg)
            self.stats.update_error_count(type(e).__name__)
            return {
                "success": False,
                "error": error_msg,
                "data": None,
                "statistics": self.stats.get_current()
            }

    async def process_transaction(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single transaction and extract key information."""
        try:
            # Extract transaction data
            transaction = tx.get('transaction', {})
            meta = tx.get('meta', {})
            
            if not transaction or not meta:
                return None

            # Track pre and post token balances
            pre_token_balances = {tb['mint']: tb for tb in meta.get('preTokenBalances', [])}
            post_token_balances = {tb['mint']: tb for tb in meta.get('postTokenBalances', [])}
            
            # Find new mint addresses by comparing pre/post balances
            for mint_address in post_token_balances:
                if mint_address not in pre_token_balances:
                    logger.debug(f"Found new mint address from token balances: {mint_address}")
                    self.mint_addresses.add(mint_address)
                    self.new_mint_addresses.add(mint_address)

            # Extract message and instructions
            message = transaction.get('message', {})
            if not message:
                return None

            # Get account keys and instructions
            account_keys = message.get('accountKeys', [])
            instructions = message.get('instructions', [])
            log_messages = meta.get('logMessages', []) or []
            
            if not account_keys or not instructions:
                return None

            # Track program IDs and check for mint operations
            found_mint = False
            for instruction in instructions:
                program_idx = instruction.get('programIdIndex')
                if program_idx is not None and program_idx < len(account_keys):
                    program_id = account_keys[program_idx]
                    self.program_ids.add(program_id)
                    
                    # Check for Token Program operations
                    if program_id in ['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
                                    'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBxvf9Ss623VQ5DA']:   # Token-2022
                        accounts = instruction.get('accounts', [])
                        data = instruction.get('data', '')

                        # Check for token account initialization
                        for msg in log_messages:
                            if "Initialize the associated token account" in msg:
                                # Look for mint address in nearby messages
                                for i in range(max(0, log_messages.index(msg)-3), min(len(log_messages), log_messages.index(msg)+3)):
                                    if "Creating account" in log_messages[i]:
                                        # Extract mint address from account creation
                                        parts = log_messages[i].split()
                                        for part in parts:
                                            if len(part) >= 32:  # Likely a base58 address
                                                logger.debug(f"Found potential mint from account creation: {part}")
                                                self.mint_addresses.add(part)
                                                self.new_mint_addresses.add(part)
                                                found_mint = True

                        # Check for CreateMint instruction
                        if any('Initialize mint' in msg or 'Create mint' in msg or 'Token mint' in msg for msg in log_messages):
                            for account_idx in accounts:
                                if account_idx < len(account_keys):
                                    mint_address = account_keys[account_idx]
                                    logger.debug(f"Found potential mint from instruction: {mint_address}")
                                    self.mint_addresses.add(mint_address)
                                    self.new_mint_addresses.add(mint_address)
                                    found_mint = True

                        # Check for MintTo instruction (0x7 = MintTo)
                        elif data and (data.startswith('7') or data.startswith('0x07')):
                            mint_idx = accounts[0] if accounts else None
                            if mint_idx is not None and mint_idx < len(account_keys):
                                mint_address = account_keys[mint_idx]
                                self.mint_addresses.add(mint_address)
                                logger.debug(f"Found MintTo operation for: {mint_address}")
                                found_mint = True

            # Check inner instructions
            inner_instructions = meta.get('innerInstructions', [])
            for inner in inner_instructions:
                for inner_ix in inner.get('instructions', []):
                    inner_program_idx = inner_ix.get('programIdIndex')
                    if inner_program_idx is not None and inner_program_idx < len(account_keys):
                        inner_program_id = account_keys[inner_program_idx]
                        if inner_program_id in ['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
                                             'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBxvf9Ss623VQ5DA']:
                            inner_accounts = inner_ix.get('accounts', [])
                            for account_idx in inner_accounts:
                                if account_idx < len(account_keys):
                                    mint_address = account_keys[account_idx]
                                    if any('Initialize mint' in msg or 'Create mint' in msg or 
                                         'Token mint' in msg or 'Creating mint' in msg for msg in log_messages):
                                        logger.debug(f"Found potential mint from inner instruction: {mint_address}")
                                        self.mint_addresses.add(mint_address)
                                        self.new_mint_addresses.add(mint_address)
                                        found_mint = True

            return {
                "success": True,
                "program_ids": list(self.program_ids),
                "instruction_count": len(instructions),
                "mint_addresses": list(self.mint_addresses),
                "new_mint_addresses": list(self.new_mint_addresses),
                "found_mint": found_mint
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
            token_programs = {
                'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'Token Program',
                'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBxvf9Ss623VQ5DA': 'Token-2022'
            }
            for pid in self.program_ids:
                if pid in token_programs:
                    logger.info(f"    - {pid} ({token_programs[pid]})")

            logger.info(f"  Total Instructions: {self.instruction_count}")
            logger.info(f"  Total Transactions: {self.transaction_count}")
            logger.info(f"  Total Mint Addresses: {len(self.mint_addresses)}")
            
            if self.mint_addresses:
                logger.info("  Mint Addresses List: ")
                for addr in self.mint_addresses:
                    validation_status = []
                    if self.is_valid_base58(addr):
                        validation_status.append("✓ Valid base58 encoding")
                    if addr.endswith('pump'):
                        validation_status.append("⚡ Pump token")
                    status_str = f" ({', '.join(validation_status)})" if validation_status else ""
                    logger.info(f"    - {addr}{status_str}")
                    
            logger.info(f"  New Mint Addresses: {len(self.new_mint_addresses)}")
            pump_tokens = {addr for addr in self.new_mint_addresses if addr.endswith('pump')}
            logger.info(f"  New Pump Tokens: {len(pump_tokens)}")
            
            if self.new_mint_addresses:
                logger.info("  New Mint Addresses List:")
                for addr in self.new_mint_addresses:
                    validation_status = []
                    if self.is_valid_base58(addr):
                        validation_status.append("✓ Valid base58 encoding")
                    if addr.endswith('pump'):
                        validation_status.append("⚡ Pump token")
                    status_str = f" ({', '.join(validation_status)})" if validation_status else ""
                    logger.info(f"    - {addr}{status_str}")

        except Exception as e:
            logger.error(f"Error logging statistics: {str(e)}")

    def _get_statistics(self) -> Dict[str, Any]:
        """Get current statistics as a dictionary."""
        return {
            "program_ids_count": len(self.program_ids),
            "instruction_count": self.instruction_count,
            "transaction_count": self.transaction_count,
            "mint_addresses_count": len(self.mint_addresses),
            "new_mint_addresses_count": len(self.new_mint_addresses),
            "new_mint_addresses": list(self.new_mint_addresses)
        }
