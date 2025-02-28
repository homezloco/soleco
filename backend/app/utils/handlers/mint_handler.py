"""
Handler for processing mint-related responses from Solana transactions.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from solders.transaction import Transaction
from solders.instruction import Instruction
from solders.pubkey import Pubkey
from .instruction_handler import InstructionHandler
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)

class MintHandler(BaseHandler):
    """Handler for processing mint-related instructions"""

    # Token program IDs
    TOKEN_PROGRAMS = {
        'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # SPL Token
        'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'   # Token 2022
    }

    def __init__(self):
        """Initialize the mint handler"""
        super().__init__()
        self.instruction_handler = InstructionHandler()
        self.processed_mints = set()
        self.stats = {
            'total_instructions': 0,
            'token_instructions': 0,
            'mint_instructions': 0,
            'errors': []
        }

    async def handle_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a response from the Solana RPC"""
        try:
            if not response_data:
                return {"success": False, "error": "Empty response data"}

            # Extract transactions from response
            transactions = response_data.get('transactions', [])
            if not transactions:
                return {"success": True, "mint_addresses": [], "token_operations": []}

            # Process each transaction
            result = {
                'mint_addresses': set(),
                'token_operations': [],
                'statistics': self.stats.copy()
            }

            for tx_data in transactions:
                try:
                    # Extract transaction and account keys
                    transaction = tx_data.get('transaction')
                    meta = tx_data.get('meta')
                    
                    if not transaction or not meta:
                        continue

                    # Get account keys
                    account_keys = []
                    if isinstance(transaction, dict):
                        message = transaction.get('message', {})
                        if isinstance(message, dict):
                            account_keys = message.get('accountKeys', [])
                    
                    # Process the transaction
                    await self.process_transaction(transaction, account_keys)

                except Exception as e:
                    logger.error(f"Error processing transaction: {str(e)}", exc_info=True)
                    continue

            # Convert sets to lists for JSON serialization
            result['mint_addresses'] = list(result['mint_addresses'])
            return result

        except Exception as e:
            logger.error(f"Error handling response: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def process_transaction(self, transaction: Any, account_keys: List[str]) -> Dict[str, Any]:
        """Process a transaction and extract mint-related data"""
        try:
            # Convert to solders Transaction if needed
            if not isinstance(transaction, Transaction):
                try:
                    if isinstance(transaction, dict) and 'message' in transaction:
                        transaction = Transaction.from_json(transaction)
                except Exception as e:
                    logger.debug(f"Could not convert to solders Transaction: {e}")

            # Get instructions from transaction
            instructions = []
            if isinstance(transaction, Transaction):
                instructions = transaction.message.instructions
            elif isinstance(transaction, dict):
                message = transaction.get('message', {})
                if isinstance(message, dict):
                    instructions = message.get('instructions', [])
                    # Also check for inner instructions in meta
                    meta = transaction.get('meta', {})
                    if isinstance(meta, dict):
                        inner_instructions = meta.get('innerInstructions', [])
                        for inner in inner_instructions:
                            if isinstance(inner, dict):
                                instructions.extend(inner.get('instructions', []))

            # Process each instruction
            result = {
                'mint_addresses': set(),
                'token_operations': [],
                'statistics': self.stats.copy()
            }

            for i, instruction in enumerate(instructions):
                try:
                    await self._process_instruction(instruction, account_keys, result)
                except Exception as e:
                    error_msg = f"Error processing instruction {i}: {str(e)}"
                    logger.error(error_msg)
                    result['statistics']['errors'].append(error_msg)

            return result

        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}", exc_info=True)
            return {
                'mint_addresses': [],
                'token_operations': [],
                'statistics': {
                    **self.stats,
                    'errors': [f"Transaction processing error: {str(e)}"]
                }
            }

    async def _process_instruction(self, instruction: Any, account_keys: List[str], result: Dict[str, Any]) -> None:
        """Process a single instruction and extract relevant data."""
        try:
            # First try to convert instruction to dict format
            instruction_dict = self.instruction_handler.convert_to_dict(instruction, account_keys)
            if not instruction_dict:
                logger.debug("Could not convert instruction to dictionary format")
                return

            # Get program ID
            program_id = instruction_dict.get('programId')
            if not program_id:
                program_id = self.instruction_handler.extract_program_id(instruction, account_keys)
                if program_id:
                    instruction_dict['programId'] = program_id
                else:
                    logger.debug("Could not extract program ID")
                    return

            # Update statistics
            result['statistics']['total_instructions'] = result['statistics'].get('total_instructions', 0) + 1

            # Process based on program type
            if program_id in self.TOKEN_PROGRAMS:
                await self._process_token_instruction(instruction_dict, account_keys, result)
                result['statistics']['token_instructions'] = result['statistics'].get('token_instructions', 0) + 1
            elif program_id == 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL':
                await self._process_associated_token_instruction(instruction_dict, account_keys, result)
            elif program_id == 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s':
                await self._process_metadata_instruction(instruction_dict, account_keys, result)
            else:
                await self._process_unknown_instruction(instruction_dict, account_keys, result)

        except Exception as e:
            logger.error(f"Error processing instruction: {str(e)}", exc_info=True)
            if 'statistics' in result:
                result['statistics']['errors'] = result['statistics'].get('errors', [])
                result['statistics']['errors'].append(str(e))

    async def _process_token_instruction(self, instruction: Dict[str, Any], account_keys: List[str], result: Dict[str, Any]) -> None:
        """Process a token program instruction"""
        try:
            # Get accounts safely
            accounts = instruction.get('accounts', [])
            if not accounts:
                return

            # Process each account
            for idx, account in enumerate(accounts):
                try:
                    if not account or not self._is_valid_mint_address(account):
                        continue

                    # Get instruction type
                    instruction_type = None
                    data = instruction.get('data')
                    if isinstance(data, dict):
                        instruction_type = data.get('type') or data.get('instruction')
                    elif isinstance(data, str):
                        # Try to parse data string for type
                        try:
                            if data.startswith('0x'):
                                data = data[2:]
                            instruction_type = f"instruction_{data[:2]}"
                        except:
                            pass

                    # Create operation record
                    operation = {
                        'type': 'token_instruction',
                        'mint_address': account,
                        'program_id': instruction.get('programId'),
                        'instruction_type': instruction_type,
                        'slot': None,
                        'signature': None
                    }

                    # Add mint address if new
                    if account not in result['mint_addresses']:
                        result['mint_addresses'].add(account)
                        result['statistics']['mint_instructions'] = result['statistics'].get('mint_instructions', 0) + 1

                    # Add operation
                    result['token_operations'].append(operation)

                except Exception as e:
                    logger.error(f"Error processing account {idx}: {str(e)}", exc_info=True)
                    continue

        except Exception as e:
            logger.error(f"Error processing token instruction: {str(e)}", exc_info=True)

    async def _process_associated_token_instruction(self, instruction: Dict[str, Any], account_keys: List[str], result: Dict[str, Any]) -> None:
        """Process an associated token account instruction"""
        try:
            # Get accounts safely
            accounts = instruction.get('accounts', [])
            if not accounts:
                return

            # Process each account
            for idx, account in enumerate(accounts):
                try:
                    if not account or not self._is_valid_mint_address(account):
                        continue

                    # Add mint address if new
                    if account not in result['mint_addresses']:
                        result['mint_addresses'].add(account)

                except Exception as e:
                    logger.error(f"Error processing associated token account {idx}: {str(e)}", exc_info=True)
                    continue

        except Exception as e:
            logger.error(f"Error processing associated token instruction: {str(e)}", exc_info=True)

    async def _process_metadata_instruction(self, instruction: Dict[str, Any], account_keys: List[str], result: Dict[str, Any]) -> None:
        """Process a metadata program instruction"""
        try:
            # Get accounts safely
            accounts = instruction.get('accounts', [])
            if not accounts:
                return

            # Process each account
            for idx, account in enumerate(accounts):
                try:
                    if not account or not self._is_valid_mint_address(account):
                        continue

                    # Add mint address if new
                    if account not in result['mint_addresses']:
                        result['mint_addresses'].add(account)

                except Exception as e:
                    logger.error(f"Error processing metadata account {idx}: {str(e)}", exc_info=True)
                    continue

        except Exception as e:
            logger.error(f"Error processing metadata instruction: {str(e)}", exc_info=True)

    async def _process_unknown_instruction(self, instruction: Dict[str, Any], account_keys: List[str], result: Dict[str, Any]) -> None:
        """Process an unknown program instruction"""
        try:
            # Get accounts safely
            accounts = instruction.get('accounts', [])
            if not accounts:
                return

            # Process each account
            for idx, account in enumerate(accounts):
                try:
                    if not account or not self._is_valid_mint_address(account):
                        continue

                    # Add mint address if new
                    if account not in result['mint_addresses']:
                        result['mint_addresses'].add(account)

                except Exception as e:
                    logger.error(f"Error processing unknown account {idx}: {str(e)}", exc_info=True)
                    continue

        except Exception as e:
            logger.error(f"Error processing unknown instruction: {str(e)}", exc_info=True)

    def _is_valid_mint_address(self, address: str) -> bool:
        """
        Validate if an address is likely to be a mint address
        
        Args:
            address: The address to validate
            
        Returns:
            bool: True if valid mint address, False otherwise
        """
        try:
            if not address or not isinstance(address, str):
                return False

            # Basic format validation
            if len(address) != 32 and len(address) != 44:
                return False

            # Check if already processed
            if address in self.processed_mints:
                return False

            # Add to processed mints
            self.processed_mints.add(address)
            
            return True

        except Exception as e:
            logger.error(f"Error validating mint address: {str(e)}")
            return False
