"""
Handler for processing token-related responses from Solana transactions.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from solders.rpc.responses import GetBlockResp
from dataclasses import dataclass, field
from datetime import datetime
import time
from collections import defaultdict

from ..models.transaction import Transaction
from ..solana_error import (
    TransactionError, MissingTransactionDataError,
    InvalidInstructionError, InvalidMintAddressError,
    TokenBalanceError
)
from .base_handler import BaseHandler
from ..logging_config import setup_logging

# Configure logging
logger = setup_logging('solana.response.token')

class TokenHandler(BaseHandler):
    """Handler for token-related transactions"""
    
    def __init__(self):
        super().__init__()
        # Known program IDs for token operations
        self.TOKEN_PROGRAMS = {
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'spl_token',
            'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb': 'token2022'
        }
        
        # Known token instruction types
        self.INSTRUCTION_TYPES = {
            '0x0': 'initialize_mint',
            '0x1': 'initialize_account',
            '0x2': 'initialize_multisig',
            '0x3': 'transfer',
            '0x4': 'approve',
            '0x5': 'revoke',
            '0x6': 'set_authority',
            '0x7': 'mint_to',
            '0x8': 'burn',
            '0x9': 'close_account',
            '0xa': 'freeze_account',
            '0xb': 'thaw_account',
            '0xc': 'transfer_checked',
            '0xd': 'approve_checked',
            '0xe': 'mint_to_checked',
            '0xf': 'burn_checked'
        }
        
    async def handle_response(self, block_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process block data to extract token operations"""
        try:
            if not block_data or not isinstance(block_data, dict):
                logger.debug("Invalid block data format")
                return None
                
            transactions = block_data.get('transactions', [])
            if not transactions:
                logger.debug("No transactions in block")
                return None
            
            # Initialize result
            result = {
                "success": True,
                "token_operations": [],
                "token2022_operations": [],
                "associated_token_ops": [],
                "statistics": {
                    "total_operations": 0,
                    "total_transactions": 0,
                    "token_program_txs": 0,
                    "token2022_program_txs": 0,
                    "associated_token_txs": 0
                }
            }
            
            # Process each transaction
            for tx_idx, tx_data in enumerate(transactions):
                try:
                    tx_result = await self.process(tx_data)
                    if tx_result.get('success', False):
                        # Update statistics
                        result['statistics']['total_transactions'] += 1
                        result['statistics']['total_operations'] += tx_result['statistics'].get('total_operations', 0)
                        result['statistics']['token_program_txs'] += tx_result['statistics'].get('token_program_txs', 0)
                        result['statistics']['token2022_program_txs'] += tx_result['statistics'].get('token2022_program_txs', 0)
                        result['statistics']['associated_token_txs'] += tx_result['statistics'].get('associated_token_txs', 0)
                        
                        # Add operations
                        result['token_operations'].extend(tx_result.get('token_operations', []))
                        result['token2022_operations'].extend(tx_result.get('token2022_operations', []))
                        result['associated_token_ops'].extend(tx_result.get('associated_token_ops', []))
                except Exception as e:
                    logger.error(f"Error processing transaction {tx_idx}: {str(e)}")
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"Error in token handler: {str(e)}", exc_info=True)
            return None
            
    async def process(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a transaction for token operations"""
        try:
            if not tx_data or not isinstance(tx_data, dict):
                logger.debug("Invalid transaction data format in token handler")
                return {"success": False, "error": "Invalid transaction format"}
            
            # Extract transaction components
            transaction = tx_data.get('transaction', {})
            meta = tx_data.get('meta')
            
            # Initialize result
            result = {
                "success": True,
                "token_operations": [],
                "token2022_operations": [],
                "associated_token_ops": [],
                "statistics": {
                    "total_operations": 0,
                    "token_program_txs": 0,
                    "token2022_program_txs": 0,
                    "associated_token_txs": 0
                }
            }
            
            if not transaction:
                logger.debug("Missing transaction data in token handler")
                result["warning"] = "Missing transaction data"
                return result

            # Get message and account keys
            message = transaction.get('message', {})
            if not message:
                result["warning"] = "Missing message data"
                return result
            
            account_keys = message.get('accountKeys', [])
            instructions = message.get('instructions', [])
            
            if not instructions or not account_keys:
                result["warning"] = "Missing instructions or account keys"
                return result
                
            # Process each instruction
            for idx, instruction in enumerate(instructions):
                try:
                    if isinstance(instruction, dict):
                        # Handle parsed instruction format
                        parsed = instruction.get('parsed', {})
                        if parsed:
                            program = parsed.get('program')
                            type_ = parsed.get('type')
                            info = parsed.get('info', {})
                            
                            if program in ['spl-token', 'token-program']:
                                result['statistics']['token_program_txs'] += 1
                                result['token_operations'].append({
                                    'type': type_,
                                    'info': info
                                })
                            elif program == 'spl-token-2022':
                                result['statistics']['token2022_program_txs'] += 1
                                result['token2022_operations'].append({
                                    'type': type_,
                                    'info': info
                                })
                            
                            result['statistics']['total_operations'] += 1
                        else:
                            # Handle raw instruction format
                            program_id = instruction.get('programId')
                            if program_id in self.TOKEN_PROGRAMS:
                                program_type = self.TOKEN_PROGRAMS[program_id]
                                if program_type == 'spl_token':
                                    result['statistics']['token_program_txs'] += 1
                                elif program_type == 'token2022':
                                    result['statistics']['token2022_program_txs'] += 1
                                    
                                result['statistics']['total_operations'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing instruction {idx}: {str(e)}")
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block to analyze token operations.
        
        This method analyzes all transactions in a block to track token operations
        including transfers, mints, burns, and other token program instructions.
        
        Args:
            block_data: Block data from Solana RPC
            
        Returns:
            Dict containing token operation results and statistics
        """
        try:
            if not block_data or not isinstance(block_data, dict):
                logger.warning("Invalid block data format")
                return None
                
            transactions = block_data.get('transactions', [])
            if not transactions:
                logger.debug("No transactions in block")
                return None
                
            # Track token operations for this block
            token_ops = defaultdict(lambda: {
                'transfers': 0,
                'mints': 0,
                'burns': 0,
                'other_ops': 0,
                'total_volume': 0.0,
                'unique_accounts': set()
            })
            
            # Process each transaction
            for tx in transactions:
                try:
                    result = await self.process(tx)
                    if not result or not isinstance(result, dict):
                        continue
                        
                    # Process token operations list
                    for op in result.get('token_operations', []):
                        if not isinstance(op, dict):
                            continue
                            
                        token_addr = op.get('token_address')
                        if not token_addr:
                            continue
                            
                        instruction_type = op.get('instruction_type')
                        amount = float(op.get('amount', 0))
                        
                        # Update token operations
                        if instruction_type == 'transfer':
                            token_ops[token_addr]['transfers'] += 1
                            token_ops[token_addr]['total_volume'] += amount
                        elif instruction_type == 'mint_to':
                            token_ops[token_addr]['mints'] += 1
                        elif instruction_type == 'burn':
                            token_ops[token_addr]['burns'] += 1
                        else:
                            token_ops[token_addr]['other_ops'] += 1
                            
                        # Track unique accounts
                        accounts = op.get('accounts', [])
                        if accounts:
                            token_ops[token_addr]['unique_accounts'].update(accounts)
                        
                except Exception as e:
                    logger.error(f"Error processing transaction in block: {str(e)}")
                    continue
            
            # Convert sets to lists for JSON serialization
            formatted_ops = {}
            for token_addr, ops in token_ops.items():
                formatted_ops[token_addr] = {
                    'transfers': ops['transfers'],
                    'mints': ops['mints'],
                    'burns': ops['burns'],
                    'other_ops': ops['other_ops'],
                    'total_volume': ops['total_volume'],
                    'unique_accounts': list(ops['unique_accounts'])
                }
            
            return {
                'token_operations': formatted_ops,
                'statistics': {
                    'total_tokens': len(token_ops),
                    'total_operations': sum(
                        ops['transfers'] + ops['mints'] + ops['burns'] + ops['other_ops'] 
                        for ops in token_ops.values()
                    ),
                    'total_volume': sum(
                        ops['total_volume'] 
                        for ops in token_ops.values()
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing block for token operations: {str(e)}")
            return None
    
    def _extract_program_id(self, instruction: Dict[str, Any], account_keys: List[str]) -> Optional[str]:
        """Extract program ID from instruction using multiple methods"""
        try:
            # Direct program ID
            if 'programId' in instruction:
                return instruction['programId']
            
            # Program ID index
            if 'programIdIndex' in instruction:
                idx = instruction['programIdIndex']
                if isinstance(idx, int) and idx < len(account_keys):
                    return account_keys[idx]
            
            # Last account in accounts array (common pattern)
            accounts = instruction.get('accounts', [])
            if accounts and isinstance(accounts[-1], int) and accounts[-1] < len(account_keys):
                return account_keys[accounts[-1]]
            
        except Exception as e:
            logger.debug(f"Error extracting program ID: {str(e)}")
        
        return None
    
    def _analyze_token_instruction(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str],
        idx: int
    ) -> Optional[Dict[str, Any]]:
        """Analyze token program instruction"""
        try:
            data = instruction.get('data')
            accounts = instruction.get('accounts', [])
            
            if not data:
                return None
            
            # Get instruction type
            instruction_type = self.INSTRUCTION_TYPES.get(data[:3], 'unknown')
            
            # Get account addresses
            account_addresses = []
            for account_idx in accounts:
                if isinstance(account_idx, int) and account_idx < len(account_keys):
                    account_addresses.append(account_keys[account_idx])
            
            # Extract mint address for relevant instructions
            mint_address = None
            if instruction_type in ['initialize_mint', 'mint_to', 'mint_to_checked']:
                if len(account_addresses) > 0:
                    mint_address = account_addresses[0]
            
            return {
                "index": idx,
                "type": instruction_type,
                "accounts": account_addresses,
                "mint_address": mint_address,
                "data": data
            }
            
        except Exception as e:
            logger.debug(f"Error analyzing token instruction: {str(e)}")
            return None
    
    def _analyze_associated_token_instruction(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str],
        idx: int
    ) -> Optional[Dict[str, Any]]:
        """Analyze associated token program instruction"""
        try:
            data = instruction.get('data')
            accounts = instruction.get('accounts', [])
            
            if not data:
                return None
            
            # Get account addresses
            account_addresses = []
            for account_idx in accounts:
                if isinstance(account_idx, int) and account_idx < len(account_keys):
                    account_addresses.append(account_keys[account_idx])
            
            # For associated token program, usually:
            # accounts[0] = associated token account
            # accounts[1] = wallet address
            # accounts[2] = mint address
            mint_address = None
            wallet_address = None
            if len(account_addresses) >= 3:
                wallet_address = account_addresses[1]
                mint_address = account_addresses[2]
            
            return {
                "index": idx,
                "type": "create",
                "accounts": account_addresses,
                "wallet_address": wallet_address,
                "mint_address": mint_address,
                "data": data
            }
            
        except Exception as e:
            logger.debug(f"Error analyzing associated token instruction: {str(e)}")
            return None
    
    def _analyze_token_balances(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze token balance changes"""
        try:
            changes = {}
            
            # Process pre balances
            pre_balances = meta.get('preTokenBalances', [])
            for balance in pre_balances:
                mint = balance.get('mint')
                if mint:
                    if mint not in changes:
                        changes[mint] = {'pre': {}, 'post': {}}
                    owner = balance.get('owner')
                    amount = int(balance.get('uiTokenAmount', {}).get('amount', 0))
                    if owner:
                        changes[mint]['pre'][owner] = amount
            
            # Process post balances
            post_balances = meta.get('postTokenBalances', [])
            for balance in post_balances:
                mint = balance.get('mint')
                if mint:
                    if mint not in changes:
                        changes[mint] = {'pre': {}, 'post': {}}
                    owner = balance.get('owner')
                    amount = int(balance.get('uiTokenAmount', {}).get('amount', 0))
                    if owner:
                        changes[mint]['post'][owner] = amount
            
            # Calculate changes
            for mint in changes:
                changes[mint]['changes'] = {}
                for owner in set(changes[mint]['pre'].keys()) | set(changes[mint]['post'].keys()):
                    pre = changes[mint]['pre'].get(owner, 0)
                    post = changes[mint]['post'].get(owner, 0)
                    if pre != post:
                        changes[mint]['changes'][owner] = post - pre
            
            return changes
            
        except Exception as e:
            logger.error(f"Error analyzing token balances: {str(e)}")
            return {}
