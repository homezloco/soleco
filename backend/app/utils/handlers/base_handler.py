"""
Base handler for Solana RPC responses.
Provides common functionality and error handling for all response handlers.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union, Tuple, Set
from dataclasses import dataclass, field
from ..solana_error import (
    NodeBehindError,
    SlotSkippedError,
    MissingBlocksError,
    NodeUnhealthyError
)
from ..logging_config import setup_logging
from collections import defaultdict

# Configure logging
logger = setup_logging(__name__)

@dataclass
class TransactionStats:
    """Statistics for transaction processing"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    skipped_queries: int = 0
    total_transactions: int = 0  # Total transactions seen
    processed_transactions: int = 0  # Successfully processed transactions
    processed_blocks: int = 0
    total_blocks: int = 0
    mint_operations: int = 0
    token_operations: int = 0
    error_counts: Dict[str, int] = field(default_factory=dict)
    processing_duration: float = 0.0
    mint_addresses: Set[str] = field(default_factory=set)
    token_addresses: Set[str] = field(default_factory=set)

    def increment_processed(self) -> None:
        """Increment processed transaction count"""
        self.processed_transactions += 1
        self.successful_queries += 1

    def increment_total(self) -> None:
        """Increment total transaction count"""
        self.total_transactions += 1
        self.total_queries += 1

    def increment_block(self) -> None:
        """Increment processed block count"""
        self.processed_blocks += 1

    def set_total_blocks(self, total: int) -> None:
        """Set total blocks to process"""
        self.total_blocks = total

    def add_mint_address(self, address: str) -> None:
        """Add a mint address to the set"""
        if address:
            self.mint_addresses.add(address)
            self.mint_operations += 1

    def add_token_address(self, address: str) -> None:
        """Add a token address to the set"""
        if address:
            self.token_addresses.add(address)
            self.token_operations += 1

    def update_error_count(self, error_type: str) -> None:
        """Update error count for a specific error type"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.failed_queries += 1

    def log_stats(self) -> None:
        """Log current statistics"""
        logger.info(f"Transaction Processing Stats:")
        logger.info(f"  Total Queries: {self.total_queries}")
        logger.info(f"  Successful Queries: {self.successful_queries}")
        logger.info(f"  Failed Queries: {self.failed_queries}")
        logger.info(f"  Skipped Queries: {self.skipped_queries}")
        logger.info(f"  Total Transactions: {self.total_transactions}")
        logger.info(f"  Processed Transactions: {self.processed_transactions}")
        logger.info(f"  Total Blocks: {self.total_blocks}")
        logger.info(f"  Processed Blocks: {self.processed_blocks}")
        logger.info(f"  Processing Duration: {self.processing_duration:.2f}s")
        if self.error_counts:
            logger.info("Error Breakdown:")
            for error_type, count in self.error_counts.items():
                logger.info(f"  {error_type}: {count}")

    def get_current(self) -> Dict[str, Any]:
        """Get current statistics as a dictionary"""
        return {
            "total_transactions": self.total_transactions,
            "processed_transactions": self.processed_transactions,
            "processed_blocks": self.processed_blocks,
            "total_blocks": self.total_blocks,
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "skipped_queries": self.skipped_queries,
            "mint_operations": self.mint_operations,
            "token_operations": self.token_operations,
            "error_counts": dict(self.error_counts),
            "processing_duration": round(self.processing_duration, 2),
            "success_rate": round(self.successful_queries / max(self.total_queries, 1) * 100, 2),
            "error_rate": round(self.failed_queries / max(self.total_queries, 1) * 100, 2),
            "mint_addresses": list(self.mint_addresses),
            "token_addresses": list(self.token_addresses)
        }

class BaseHandler:
    """Base class for all Solana transaction handlers"""
    
    def __init__(self):
        self.stats = TransactionStats()
        # Common program IDs
        self.SYSTEM_PROGRAMS = {
            'Vote111111111111111111111111111111111111111': 'vote',
            'ComputeBudget111111111111111111111111111111': 'compute_budget',
            '11111111111111111111111111111111': 'system'
        }
        
    async def handle_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a raw RPC response"""
        try:
            if not response or not isinstance(response, dict):
                logger.warning("Invalid response format")
                self.stats.update_error_count("invalid_format")
                return {
                    "success": False,
                    "error": "Invalid response format",
                    "data": None,
                    "statistics": self.stats.get_current()
                }

            # Process the result
            result = await self.process_result(response)
            
            # Update statistics
            if result.get("success", False):
                self.stats.increment_processed()
            else:
                if result.get("error"):
                    self.stats.update_error_count(result["error"])

            return result

        except Exception as e:
            error_msg = f"Error in handle_response: {str(e)}"
            logger.error(error_msg)
            self.stats.update_error_count(type(e).__name__)
            return {
                "success": False,
                "error": error_msg,
                "data": None,
                "statistics": self.stats.get_current()
            }

    async def process_result(self, result: Any) -> Dict[str, Any]:
        """Process the result data. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement process_result")

    async def process(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a transaction with comprehensive error handling"""
        self.stats.increment_total()
        start_time = time.time()

        try:
            # Validate and extract components
            message, meta, account_keys, instructions = self._validate_transaction(tx_data)
            if not all([message, meta, account_keys, instructions]):
                raise ValueError("Missing required transaction components")
                
            # Process transaction data
            result = self._process_transaction_data(message, meta, account_keys, instructions)
            
            # Update statistics
            self.stats.increment_processed()
            self.stats.processing_duration += time.time() - start_time

            return result

        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}", exc_info=True)
            self.stats.update_error_count(type(e).__name__)
            self.stats.processing_duration += time.time() - start_time
            return {"success": False, "error": str(e)}

    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block of transactions.
        
        This is the main entry point for block processing. Each handler should override
        this method to implement their specific block processing logic.
        
        Args:
            block_data: Block data from Solana RPC
            
        Returns:
            Dict containing processing results and statistics
        """
        try:
            if not block_data or not isinstance(block_data, dict):
                logger.warning("Invalid block data format")
                return None
                
            transactions = block_data.get('transactions', [])
            if not transactions:
                logger.debug("No transactions in block")
                return None

            # Update block statistics
            self.stats.increment_block()
            start_time = time.time()
                
            results = []
            for tx in transactions:
                try:
                    result = await self.process(tx)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error processing transaction: {str(e)}")
                    self.stats.update_error_count(type(e).__name__)

            # Update processing duration
            self.stats.processing_duration = time.time() - start_time
                    
            # Return results with statistics
            return {
                'results': results,
                'statistics': self.stats.get_current()
            }
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            return {
                'error': str(e),
                'statistics': self.stats.get_current()
            }

    def _validate_transaction(self, transaction: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], List[str], List[Dict[str, Any]]]:
        """Validate transaction data and extract key components."""
        try:
            logger.debug("Starting transaction validation")
            
            # Extract transaction data
            if isinstance(transaction, list):
                tx = transaction[0] if transaction else None
                meta = transaction[1] if len(transaction) > 1 else None
                logger.debug(f"Extracted from list: tx={bool(tx)}, meta={bool(meta)}")
            else:
                tx = transaction
                meta = transaction.get('meta') if isinstance(transaction, dict) else None
                logger.debug(f"Extracted from dict: tx={bool(tx)}, meta={bool(meta)}")
                
            # Handle transaction object
            if isinstance(tx, dict) and 'transaction' in tx:
                tx = tx['transaction']
                logger.debug("Extracted inner transaction")
                
            # Extract message
            message = None
            if isinstance(tx, dict):
                message = tx.get('message', {})
                logger.debug(f"Extracted message type: {type(message)}")
                
                if isinstance(message, str):
                    logger.debug("Attempting to decode string message")
                    try:
                        import json
                        import base64
                        decoded = base64.b64decode(message)
                        message = json.loads(decoded)
                        logger.debug("Successfully decoded message")
                    except Exception as e:
                        logger.debug(f"Failed to decode message: {str(e)}")
                        message = {'raw': message}
                        
            # Get account keys
            account_keys = []
            if isinstance(message, dict):
                # Direct account keys
                keys = message.get('accountKeys', [])
                if isinstance(keys, list):
                    account_keys.extend(str(key) for key in keys if key)
                logger.debug(f"Found {len(account_keys)} account keys")
                    
            # Get instructions
            instructions = []
            if isinstance(message, dict):
                raw_instructions = message.get('instructions', [])
                logger.debug(f"Found {len(raw_instructions)} raw instructions")
                
                if isinstance(raw_instructions, list):
                    for idx, instr in enumerate(raw_instructions):
                        logger.debug(f"Processing instruction {idx}, type: {type(instr)}")
                        instruction = None
                        
                        # Handle string instruction
                        if isinstance(instr, str):
                            logger.debug(f"Processing string instruction: {instr[:32]}...")
                            if account_keys:
                                instruction = {
                                    'programId': account_keys[0],
                                    'accounts': account_keys[1:],
                                    'data': instr
                                }
                            else:
                                instruction = {
                                    'programId': None,
                                    'accounts': [],
                                    'data': instr
                                }
                            logger.debug(f"Converted string instruction: {instruction}")
                                
                        # Handle dict instruction
                        elif isinstance(instr, dict):
                            instruction = instr
                            logger.debug("Using dict instruction directly")
                            
                        if instruction:
                            instructions.append(instruction)
                        else:
                            logger.warning(f"Skipping instruction {idx} of unknown type: {type(instr)}")
                            
            logger.debug(f"Processed {len(instructions)} instructions")
            return message, meta, account_keys, instructions
            
        except Exception as e:
            logger.error(f"Error validating transaction: {str(e)}", exc_info=True)
            return {}, {}, [], []

    def _extract_program_id(self, instruction: Dict[str, Any], account_keys: List[str]) -> Optional[str]:
        """Extract program ID from instruction using multiple methods"""
        try:
            logger.debug(f"Extracting program ID from instruction type: {type(instruction)}")
            
            # Handle string instruction
            if isinstance(instruction, str):
                logger.debug("Processing string instruction")
                if account_keys:
                    program_id = account_keys[0]
                    logger.debug(f"Using first account key as program ID: {program_id}")
                    return program_id
                return None
                
            # Handle dict instruction
            if isinstance(instruction, dict):
                logger.debug("Processing dict instruction")
                # Direct program ID
                program_id = instruction.get('programId')
                if program_id:
                    logger.debug(f"Found direct program ID: {program_id}")
                    return str(program_id)
                    
                # Program ID from index
                program_idx = instruction.get('programIdIndex')
                if isinstance(program_idx, int) and 0 <= program_idx < len(account_keys):
                    program_id = account_keys[program_idx]
                    logger.debug(f"Found program ID from index {program_idx}: {program_id}")
                    return program_id
                    
            # Default to first account key if available
            if account_keys:
                program_id = account_keys[0]
                logger.debug(f"Using default first account key: {program_id}")
                return program_id
                
        except Exception as e:
            logger.error(f"Error extracting program ID: {str(e)}", exc_info=True)
            
        logger.debug("No program ID found")
        return None

    def _get_instruction_type(self, program_id: str, instruction: Dict[str, Any]) -> str:
        """Determine instruction type based on program ID and data"""
        try:
            # Handle system programs
            if program_id in self.SYSTEM_PROGRAMS:
                return self.SYSTEM_PROGRAMS[program_id]
                
            # Get instruction data
            data = instruction.get('data', {})
            
            # Handle string data
            if isinstance(data, str):
                return 'raw'
                
            # Handle dict data
            if isinstance(data, dict):
                # Check for parsed data
                if 'parsed' in data:
                    parsed = data['parsed']
                    if isinstance(parsed, dict):
                        return parsed.get('type', 'unknown')
                    return str(parsed)
                    
                # Check for raw data
                if 'raw' in data:
                    return 'raw'
                    
            return 'unknown'
            
        except Exception as e:
            logger.error(f"Error determining instruction type: {str(e)}")
            return 'error'

    async def process_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single transaction and return results"""
        try:
            # Validate and extract components
            message, meta, account_keys, instructions = self._validate_transaction(transaction)
            if not all([message, meta, account_keys, instructions]):
                raise ValueError("Missing required transaction components")
                
            # Process transaction data
            result = self._process_transaction_data(message, meta, account_keys, instructions)
            
            # Update statistics
            self.stats.increment_processed()
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            self.stats.update_error_count(type(e).__name__)
            return {}

    def _process_transaction_data(
            self,
            message: Dict[str, Any],
            meta: Dict[str, Any],
            account_keys: List[str],
            instructions: List[Dict[str, Any]]
        ) -> Dict[str, Any]:
        """Process transaction data with comprehensive analysis"""
        result = {
            'program_ids': set(),
            'instruction_types': [],
            'accounts': set(account_keys),
            'token_transfers': [],
            'errors': []
        }
        
        try:
            # Process each instruction
            for idx, instruction in enumerate(instructions):
                try:
                    # Skip None or empty instructions
                    if not instruction:
                        continue
                        
                    # Handle string instruction
                    if isinstance(instruction, str):
                        instruction = {
                            'programId': account_keys[0] if account_keys else '',
                            'accounts': account_keys[1:] if len(account_keys) > 1 else [],
                            'data': {
                                'raw': instruction,
                                'parsed': None
                            }
                        }
                        
                    # Get program ID
                    program_id = self._extract_program_id(instruction, account_keys)
                    if program_id:
                        result['program_ids'].add(program_id)
                        
                    # Get instruction type
                    instr_type = self._get_instruction_type(program_id or '', instruction)
                    result['instruction_types'].append(instr_type)
                    
                    # Process accounts
                    if isinstance(instruction, dict):
                        accounts = instruction.get('accounts', [])
                        if isinstance(accounts, list):
                            result['accounts'].update(
                                account_keys[i] for i in accounts 
                                if isinstance(i, int) and 0 <= i < len(account_keys)
                            )
                            
                except Exception as e:
                    error_msg = f"Error processing instruction {idx}: {str(e)}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
                    continue
                    
            # Analyze token balances
            if meta:
                self._analyze_token_balances(
                    meta.get('preTokenBalances', []),
                    meta.get('postTokenBalances', []),
                    result
                )
                
            # Convert sets to lists for JSON serialization
            result['program_ids'] = list(result['program_ids'])
            result['accounts'] = list(result['accounts'])
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing transaction data: {str(e)}")
            return result

    def _analyze_token_balances(self, pre_balances: List[Dict[str, Any]], post_balances: List[Dict[str, Any]], result: Dict[str, Any]) -> None:
        """Analyze token balance changes"""
        try:
            # Handle case where pre_balances is a dict containing both pre and post balances
            if isinstance(pre_balances, dict) and 'preTokenBalances' in pre_balances:
                meta = pre_balances
                pre_balances = meta.get('preTokenBalances', [])
                post_balances = meta.get('postTokenBalances', [])
                
            # Track unique token accounts and their balance changes
            token_changes = {}
            
            def safe_float(value) -> float:
                """Safely convert value to float, handling None and empty strings"""
                if value is None or value == '':
                    return 0.0
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0
            
            # Process pre-balances
            for balance in pre_balances:
                if not isinstance(balance, dict):
                    continue
                    
                mint = balance.get('mint')
                if mint:
                    if mint not in token_changes:
                        token_changes[mint] = {'pre': 0.0, 'post': 0.0}
                    
                    # Get token amount, handling possible None values
                    ui_amount = balance.get('uiTokenAmount', {})
                    if isinstance(ui_amount, dict):
                        amount = ui_amount.get('uiAmount')
                        if amount is not None:
                            token_changes[mint]['pre'] = safe_float(amount)
                        else:
                            # Try raw amount if uiAmount is not available
                            raw_amount = ui_amount.get('amount')
                            if raw_amount is not None:
                                token_changes[mint]['pre'] = safe_float(raw_amount)
            
            # Process post-balances
            for balance in post_balances:
                if not isinstance(balance, dict):
                    continue
                    
                mint = balance.get('mint')
                if mint:
                    if mint not in token_changes:
                        token_changes[mint] = {'pre': 0.0, 'post': 0.0}
                    
                    # Get token amount, handling possible None values
                    ui_amount = balance.get('uiTokenAmount', {})
                    if isinstance(ui_amount, dict):
                        amount = ui_amount.get('uiAmount')
                        if amount is not None:
                            token_changes[mint]['post'] = safe_float(amount)
                        else:
                            # Try raw amount if uiAmount is not available
                            raw_amount = ui_amount.get('amount')
                            if raw_amount is not None:
                                token_changes[mint]['post'] = safe_float(raw_amount)
            
            # Calculate changes
            token_operations = []
            for mint, changes in token_changes.items():
                change = changes['post'] - changes['pre']
                # Only include non-zero changes and valid amounts
                if change != 0 and (changes['pre'] != 0 or changes['post'] != 0):
                    token_operations.append({
                        'mint': mint,
                        'change': change,
                        'pre_balance': changes['pre'],
                        'post_balance': changes['post']
                    })
            
            # Add to result
            if token_operations:
                result['token_transfers'] = token_operations
            
        except Exception as e:
            logger.error(f"Error analyzing token balances: {str(e)}", exc_info=True)