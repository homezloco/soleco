"""
Handler for system address operations and validations.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from ..models.program_info import ProgramInfo
from .base_handler import BaseHandler, TransactionStats
from ..logging_config import setup_logging

# Configure logging
logger = setup_logging('solana.response.system')

class SystemHandler(BaseHandler):
    """Handler for system program operations"""
    
    def __init__(self):
        super().__init__()
        # System program constants
        self.SYSTEM_PROGRAM_ID = '11111111111111111111111111111111'
        self.COMPUTE_BUDGET_ID = 'ComputeBudget111111111111111111111111111111'
        self.VOTE_PROGRAM_ID = 'Vote111111111111111111111111111111111111111'
        
        # Known system instruction types
        self.INSTRUCTION_TYPES = {
            '0x0': 'create_account',
            '0x1': 'assign',
            '0x2': 'transfer',
            '0x3': 'create_account_with_seed',
            '0x4': 'advance_nonce_account',
            '0x5': 'withdraw_nonce_account',
            '0x6': 'initialize_nonce_account',
            '0x7': 'authorize_nonce_account',
            '0x8': 'allocate',
            '0x9': 'allocate_with_seed',
            '0xa': 'assign_with_seed',
            '0xb': 'transfer_with_seed'
        }
        
    async def process(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a transaction for system program operations"""
        try:
            if not tx_data or not isinstance(tx_data, dict):
                logger.debug("Invalid transaction data format in system handler")
                return {"success": False, "error": "Invalid transaction format"}
            
            # Initialize result
            result = {
                "success": True,
                "system_operations": [],
                "compute_budget_operations": [],
                "vote_operations": [],
                "statistics": {
                    "total_system_ops": 0,
                    "total_compute_budget_ops": 0,
                    "total_vote_ops": 0
                }
            }
            
            # Extract transaction components
            transaction = tx_data.get('transaction', {})
            meta = tx_data.get('meta')
            
            if not transaction:
                logger.debug("Missing transaction data in system handler")
                result["warning"] = "Missing transaction data"
                return result

            if not meta:
                logger.debug("Missing meta data in system handler")
                result["warning"] = "Missing meta data"
                # Continue processing with available data
            
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
            
            # Process instructions
            for idx, instruction in enumerate(instructions):
                try:
                    # Get program ID
                    program_id = self._extract_program_id(instruction, account_keys)
                    if not program_id:
                        continue
                    
                    # Get instruction type
                    instruction_type = self._get_instruction_type(program_id, instruction)
                    if not instruction_type:
                        continue
                        
                    # Get accounts involved
                    accounts = []
                    for account_idx in instruction.get('accounts', []):
                        if isinstance(account_idx, int) and account_idx < len(account_keys):
                            accounts.append(account_keys[account_idx])
                            
                    # Create operation info
                    operation = {
                        'index': idx,
                        'type': instruction_type,
                        'program_id': program_id,
                        'accounts': accounts,
                        'data': instruction.get('data')
                    }
                    
                    # Add to appropriate list based on program type
                    if program_id == '11111111111111111111111111111111':  # System program
                        result['system_operations'].append(operation)
                        result['statistics']['total_system_ops'] += 1
                    elif program_id == 'ComputeBudget111111111111111111111111111111':  # Compute budget
                        result['compute_budget_operations'].append(operation)
                        result['statistics']['total_compute_budget_ops'] += 1
                    elif program_id == 'Vote111111111111111111111111111111111111111':  # Vote program
                        result['vote_operations'].append(operation)
                        result['statistics']['total_vote_ops'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing instruction {idx}: {str(e)}")
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"Error in system handler: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block to analyze system program operations.
        
        This method analyzes all transactions in a block to track system program operations
        including account creations, transfers, and compute budget instructions.
        
        Args:
            block_data: Block data from Solana RPC
            
        Returns:
            Dict containing system operation results and statistics
        """
        try:
            if not block_data or not isinstance(block_data, dict):
                logger.warning("Invalid block data format")
                return None
                
            transactions = block_data.get('transactions', [])
            if not transactions:
                logger.debug("No transactions in block")
                return None
                
            # Track operations for this block
            system_ops = defaultdict(int)
            compute_budget_ops = defaultdict(int)
            vote_ops = defaultdict(int)
            
            # Process each transaction
            for tx in transactions:
                try:
                    result = await self.process(tx)
                    if not result or not isinstance(result, dict):
                        continue
                        
                    # Process system operations
                    for op in result.get('system_operations', []):
                        if isinstance(op, dict):
                            op_type = op.get('type', 'unknown')
                            system_ops[op_type] += 1
                            
                    # Process compute budget operations
                    for op in result.get('compute_budget_operations', []):
                        if isinstance(op, dict):
                            op_type = op.get('type', 'unknown')
                            compute_budget_ops[op_type] += 1
                            
                    # Process vote operations
                    for op in result.get('vote_operations', []):
                        if isinstance(op, dict):
                            op_type = op.get('type', 'unknown')
                            vote_ops[op_type] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing transaction in block: {str(e)}")
                    continue
            
            return {
                'system_operations': dict(system_ops),
                'compute_budget_operations': dict(compute_budget_ops),
                'vote_operations': dict(vote_ops),
                'statistics': {
                    'total_system_ops': sum(system_ops.values()),
                    'total_compute_budget_ops': sum(compute_budget_ops.values()),
                    'total_vote_ops': sum(vote_ops.values()),
                    'total_operations': sum(system_ops.values()) + sum(compute_budget_ops.values()) + sum(vote_ops.values())
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing block for system operations: {str(e)}")
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
    
    def _get_instruction_type(self, program_id: str, instruction: Dict[str, Any]) -> Optional[str]:
        """Get instruction type based on program ID"""
        try:
            if program_id == self.SYSTEM_PROGRAM_ID:
                return self._analyze_system_instruction(instruction)
            elif program_id == self.COMPUTE_BUDGET_ID:
                return self._analyze_compute_budget_instruction(instruction)
            elif program_id == self.VOTE_PROGRAM_ID:
                return self._analyze_vote_instruction(instruction)
            
        except Exception as e:
            logger.debug(f"Error getting instruction type: {str(e)}")
        
        return None
    
    def _analyze_system_instruction(self, instruction: Dict[str, Any]) -> Optional[str]:
        """Analyze system program instruction"""
        try:
            data = instruction.get('data')
            if not data:
                return None
            
            # Get instruction type
            instruction_type = self.INSTRUCTION_TYPES.get(data[:3], 'unknown')
            
            return instruction_type
            
        except Exception as e:
            logger.debug(f"Error analyzing system instruction: {str(e)}")
            return None
    
    def _analyze_compute_budget_instruction(self, instruction: Dict[str, Any]) -> Optional[str]:
        """Analyze compute budget instruction"""
        try:
            data = instruction.get('data')
            if not data:
                return None
            
            # Common compute budget instructions
            if data.startswith('0x0'):
                return "request_units"
            elif data.startswith('0x1'):
                return "request_heap_frame"
            
            return "unknown"
            
        except Exception as e:
            logger.debug(f"Error analyzing compute budget instruction: {str(e)}")
            return None
    
    def _analyze_vote_instruction(self, instruction: Dict[str, Any]) -> Optional[str]:
        """Analyze vote program instruction"""
        try:
            data = instruction.get('data')
            if not data:
                return None
            
            # Common vote instructions
            if data.startswith('0x0'):
                return "initialize"
            elif data.startswith('0x1'):
                return "authorize"
            elif data.startswith('0x2'):
                return "vote"
            
            return "unknown"
            
        except Exception as e:
            logger.debug(f"Error analyzing vote instruction: {str(e)}")
            return None
