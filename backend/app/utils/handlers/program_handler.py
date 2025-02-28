"""
Handler for processing program-related responses from Solana transactions.
"""

from typing import Dict, Any, List, Optional
import logging
from ..logging_config import setup_logging
from .base_handler import BaseHandler
from collections import defaultdict

# Configure logging
logger = setup_logging("solana.program")

class ProgramHandler(BaseHandler):
    """Handler for program-related operations"""
    
    def __init__(self):
        """Initialize program handler"""
        super().__init__()
        # Known program IDs for common operations
        self.KNOWN_PROGRAMS = {
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'spl_token',
            'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb': 'token2022',
            'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s': 'metadata',
            'p1exdMJcjVao65QdewkaZRUnU6VPSXhus9n2GzWfh98': 'metaplex',
            'cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ': 'candy_machine',
            'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL': 'ata'
        }
        
    async def process(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a transaction for program interactions"""
        try:
            if not tx_data or not isinstance(tx_data, dict):
                logger.debug("Invalid transaction data format in program handler")
                return {"success": False, "error": "Invalid transaction format"}
            
            # Initialize result
            result = {
                "success": True,
                "program_interactions": {},
                "instruction_details": [],
                "statistics": {
                    "total_programs": 0,
                    "total_instructions": 0
                }
            }
            
            # Extract transaction components
            transaction = tx_data.get('transaction', {})
            meta = tx_data.get('meta')
            
            if not transaction:
                logger.debug("Missing transaction data in program handler")
                result["warning"] = "Missing transaction data"
                return result

            if not meta:
                logger.debug("Missing meta data in program handler")
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
            
            # Process program interactions
            program_interactions = defaultdict(lambda: {
                'count': 0,
                'instruction_types': defaultdict(int),
                'unique_accounts': set()
            })
            instruction_details = []
            
            # Process instructions
            for idx, instruction in enumerate(instructions):
                try:
                    # Get program ID
                    program_id = self._extract_program_id(instruction, account_keys)
                    if not program_id:
                        continue
                    
                    # Analyze instruction
                    instruction_info = self._analyze_instruction(
                        program_id,
                        instruction,
                        account_keys,
                        idx
                    )
                    if instruction_info:
                        instruction_details.append(instruction_info)
                        
                        # Update program interaction stats
                        program_interactions[program_id]['count'] += 1
                        program_interactions[program_id]['instruction_types'][instruction_info['instruction_type']] += 1
                        program_interactions[program_id]['unique_accounts'].update(instruction_info['accounts'])
                    
                except Exception as e:
                    logger.error(f"Error processing instruction {idx}: {str(e)}")
                    continue
            
            # Format program interactions for output
            formatted_interactions = {}
            for program_id, details in program_interactions.items():
                formatted_interactions[program_id] = {
                    'count': details['count'],
                    'instruction_types': dict(details['instruction_types']),
                    'unique_accounts': list(details['unique_accounts']),
                    'type': self.get_program_type(program_id)
                }
            
            # Update result
            result["program_interactions"] = formatted_interactions
            result["instruction_details"] = instruction_details
            result["statistics"].update({
                "total_programs": len(program_interactions),
                "total_instructions": len(instruction_details)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in program handler: {str(e)}")
            return {"success": False, "error": str(e)}
    
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
    
    def _analyze_instruction(
        self,
        program_id: str,
        instruction: Dict[str, Any],
        account_keys: List[str],
        idx: int
    ) -> Optional[Dict[str, Any]]:
        """Analyze instruction details"""
        try:
            program_type = self.get_program_type(program_id)
            
            # Get instruction data
            data = instruction.get('data')
            accounts = instruction.get('accounts', [])
            
            # Get account addresses
            account_addresses = []
            for account_idx in accounts:
                if isinstance(account_idx, int) and account_idx < len(account_keys):
                    account_addresses.append(account_keys[account_idx])
            
            # Determine instruction type
            instruction_type = self._get_instruction_type(program_type, data)
            
            return {
                "index": idx,
                "program_id": program_id,
                "program_type": program_type,
                "instruction_type": instruction_type,
                "accounts": account_addresses,
                "data": data
            }
            
        except Exception as e:
            logger.debug(f"Error analyzing instruction: {str(e)}")
            return None
    
    def _get_instruction_type(self, program_type: str, data: Optional[str]) -> str:
        """Determine instruction type based on program type and data"""
        try:
            if not data:
                return 'unknown'
            
            # Token program instructions
            if program_type in ['spl_token', 'token2022']:
                if data.startswith('0x0'):
                    return 'initialize'
                elif data.startswith('0x1'):
                    return 'close'
                elif data.startswith('0x3'):
                    return 'transfer'
                elif data.startswith('0x7'):
                    return 'mint_to'
                elif data.startswith('0x8'):
                    return 'burn'
            
            # System program instructions
            elif program_type == 'system':
                if data.startswith('0x0'):
                    return 'create_account'
                elif data.startswith('0x2'):
                    return 'transfer'
                elif data.startswith('0x3'):
                    return 'create_account_with_seed'
            
            return 'unknown'
            
        except Exception as e:
            logger.debug(f"Error getting instruction type: {str(e)}")
            return 'unknown'
    
    def get_program_type(self, program_id: str) -> str:
        """Get the type of a program based on its ID"""
        return self.KNOWN_PROGRAMS.get(program_id, 'unknown')
    
    def is_system_program(self, program_id: str) -> bool:
        """Check if a program ID is a system program"""
        return program_id in self.KNOWN_PROGRAMS and self.KNOWN_PROGRAMS[program_id] == 'system'
    
    def is_token_program(self, program_id: str) -> bool:
        """Check if a program ID is a token program"""
        program_type = self.KNOWN_PROGRAMS.get(program_id)
        return program_type in ['spl_token', 'token2022']

    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block to analyze program interactions.
        
        This method analyzes all transactions in a block to track program interactions
        and instruction types.
        
        Args:
            block_data: Block data from Solana RPC
            
        Returns:
            Dict containing program interaction results and statistics
        """
        try:
            if not block_data or not isinstance(block_data, dict):
                logger.warning("Invalid block data format")
                return None
                
            transactions = block_data.get('transactions', [])
            if not transactions:
                logger.debug("No transactions in block")
                return None
                
            # Track program interactions for this block
            program_interactions = defaultdict(lambda: {
                'count': 0,
                'instruction_types': defaultdict(int),
                'unique_accounts': set()
            })
            
            # Process each transaction
            for tx in transactions:
                try:
                    result = await self.process(tx)
                    if not result or not isinstance(result, dict):
                        continue
                        
                    # Process program interactions
                    for program_id, details in result.get('program_interactions', {}).items():
                        program_interactions[program_id]['count'] += details.get('count', 0)
                        
                        # Track instruction types
                        for instr_type, count in details.get('instruction_types', {}).items():
                            program_interactions[program_id]['instruction_types'][instr_type] += count
                            
                        # Track unique accounts
                        program_interactions[program_id]['unique_accounts'].update(
                            details.get('unique_accounts', [])
                        )
                        
                except Exception as e:
                    logger.error(f"Error processing transaction in block: {str(e)}")
                    continue
            
            # Format results for JSON serialization
            formatted_interactions = {}
            for program_id, details in program_interactions.items():
                formatted_interactions[program_id] = {
                    'count': details['count'],
                    'instruction_types': dict(details['instruction_types']),
                    'unique_accounts': list(details['unique_accounts']),
                    'program_type': self.get_program_type(program_id)
                }
            
            return {
                'program_interactions': formatted_interactions,
                'statistics': {
                    'total_programs': len(program_interactions),
                    'total_interactions': sum(
                        details['count'] 
                        for details in program_interactions.values()
                    ),
                    'unique_instruction_types': len(set(
                        instr_type
                        for details in program_interactions.values()
                        for instr_type in details['instruction_types'].keys()
                    ))
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing block for program interactions: {str(e)}")
            return None
