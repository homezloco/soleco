"""
Handler for processing Solana instructions with robust extraction and validation.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from collections import defaultdict
from solders.instruction import Instruction, AccountMeta
from solders.pubkey import Pubkey

logger = logging.getLogger(__name__)

@dataclass
class InstructionMetadata:
    """Metadata for instruction processing"""
    program_id: str
    instruction_type: Optional[str] = None
    accounts: List[str] = field(default_factory=list)
    data: Any = None
    parsed_info: Dict[str, Any] = field(default_factory=dict)

class InstructionHandler:
    """Handler for Solana instruction processing"""
    
    # Common program IDs
    TOKEN_PROGRAMS = {
        'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'spl_token',
        'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb': 'token2022',
        'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s': 'metadata',
        'p1exdMJcjVao65QdewkaZRUnU6VPSXhus9n2GzWfh98': 'metaplex',
        'cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ': 'candy_machine',
        'CndyV3LdqHUfDLmE5naZjVN8rBZz4tqhdefbAnjHG3JR': 'candy_machine',
        'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL': 'ata',
    }
    
    # Known system addresses
    SYSTEM_ADDRESSES = {
        'So11111111111111111111111111111111111111112',  # Wrapped SOL
        'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
        'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',  # Associated Token Program
        'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',  # Token Program 2022
        '11111111111111111111111111111111',  # System Program
        'ComputeBudget111111111111111111111111111111',  # Compute Budget
        'Vote111111111111111111111111111111111111111',  # Vote Program
        'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr',  # Memo Program
    }
    
    def __init__(self):
        """Initialize the instruction handler"""
        self.stats = defaultdict(int)
        
    def convert_to_dict(self, instruction: Any, account_keys: List[str]) -> Dict[str, Any]:
        """
        Convert an instruction to a standardized dictionary format using solders

        Args:
            instruction: The instruction to convert
            account_keys: List of account keys

        Returns:
            Dict containing standardized instruction data
        """
        try:
            # Handle None or empty instruction
            if not instruction:
                logger.debug("Empty instruction received")
                return None

            # Handle string instructions
            if isinstance(instruction, str):
                if not account_keys:
                    logger.debug("String instruction received but no account keys available")
                    return None
                return {
                    'programId': account_keys[0],
                    'accounts': account_keys[1:] if len(account_keys) > 1 else [],
                    'data': instruction
                }

            # Handle solders Instruction type
            if isinstance(instruction, Instruction):
                return {
                    'programId': str(instruction.program_id),
                    'accounts': [str(acc.pubkey) for acc in instruction.accounts],
                    'data': instruction.data.hex() if instruction.data else None
                }

            # Handle dict instructions
            if isinstance(instruction, dict):
                # Try multiple ways to get program ID
                program_id = None
                for key in ['programId', 'program_id', 'program']:
                    if key in instruction:
                        program_id = str(instruction[key])
                        break

                # Try to get program ID from accounts if not found
                if not program_id and 'accounts' in instruction:
                    accounts = instruction['accounts']
                    if accounts and len(accounts) > 0:
                        program_id = str(accounts[-1])

                # Get accounts list
                accounts = []
                if 'accounts' in instruction:
                    acc_list = instruction['accounts']
                    if isinstance(acc_list, list):
                        accounts = [str(acc) for acc in acc_list if acc]
                elif 'keys' in instruction:
                    key_list = instruction['keys']
                    if isinstance(key_list, list):
                        accounts = [str(key) for key in key_list if key]

                # Get instruction data
                data = None
                if 'data' in instruction:
                    data_val = instruction['data']
                    if isinstance(data_val, (str, bytes)):
                        data = str(data_val)
                    elif isinstance(data_val, dict):
                        data = data_val
                    else:
                        try:
                            data = str(data_val)
                        except:
                            data = None

                return {
                    'programId': program_id,
                    'accounts': accounts,
                    'data': data
                }

            # Try to convert to solders Instruction
            try:
                if hasattr(instruction, 'program_id') and hasattr(instruction, 'accounts'):
                    program_id = str(instruction.program_id)
                    accounts = []
                    
                    # Handle different account formats
                    if isinstance(instruction.accounts, list):
                        for acc in instruction.accounts:
                            if isinstance(acc, str):
                                accounts.append(acc)
                            elif hasattr(acc, 'pubkey'):
                                accounts.append(str(acc.pubkey))
                            elif isinstance(acc, dict) and 'pubkey' in acc:
                                accounts.append(str(acc['pubkey']))
                    
                    # Handle data in different formats
                    data = None
                    if hasattr(instruction, 'data'):
                        data_val = instruction.data
                        if isinstance(data_val, (str, bytes)):
                            data = str(data_val)
                        elif isinstance(data_val, dict):
                            data = data_val
                        else:
                            try:
                                data = str(data_val)
                            except:
                                data = None
                    
                    return {
                        'programId': program_id,
                        'accounts': accounts,
                        'data': data
                    }
            except Exception as e:
                logger.debug(f"Failed to convert to solders Instruction: {e}")

            # Handle unknown instruction types
            logger.warning(f"Unknown instruction type: {type(instruction)}")
            return None

        except Exception as e:
            logger.error(f"Error converting instruction to dict: {str(e)}", exc_info=True)
            return None

    def extract_program_id(self, instruction: Any, account_keys: List[str]) -> Optional[str]:
        """
        Extract program ID from instruction using solders when possible
        
        Args:
            instruction: The instruction to extract from
            account_keys: List of account keys
            
        Returns:
            str: Program ID if found, None otherwise
        """
        try:
            if not instruction or not account_keys:
                logger.debug("Skipping instruction - missing instruction or account keys")
                return None
                
            # Try to convert to solders Instruction first
            try:
                if isinstance(instruction, Instruction):
                    return str(instruction.program_id)
                    
                if hasattr(instruction, 'program_id') and hasattr(instruction, 'accounts'):
                    program_id = Pubkey.from_string(str(instruction.program_id))
                    return str(program_id)
            except Exception as e:
                logger.debug(f"Failed to use solders for program ID: {e}")

            # Fallback to other methods
            program_id = None
            
            # Method 1: Check message header
            if hasattr(instruction, 'message') and hasattr(instruction.message, 'header'):
                header = instruction.message.header
                if hasattr(header, 'program_ids') and header.program_ids:
                    program_id = str(header.program_ids[0])
                    logger.debug(f"Found program_id via message header: {program_id}")
                    return program_id
                    
            # Method 2: Direct program_id attribute
            if not program_id and hasattr(instruction, 'program_id'):
                try:
                    program_id = str(instruction.program_id)
                    logger.debug(f"Found program_id via direct attribute: {program_id}")
                    return program_id
                except Exception as e:
                    logger.debug(f"Error getting direct program_id: {e}")
                    
            # Method 3: Dict format
            if isinstance(instruction, dict):
                program_id = instruction.get('programId') or instruction.get('program_id')
                if program_id:
                    return str(program_id)
                    
            # Method 4: String instruction
            if isinstance(instruction, str) and account_keys:
                return str(account_keys[0])
                
            return program_id
            
        except Exception as e:
            logger.error(f"Error extracting program ID: {str(e)}", exc_info=True)
            return None
            
    def process_instruction(self, instruction: Any, account_keys: List[str]) -> Optional[InstructionMetadata]:
        """
        Process an instruction and extract metadata
        
        Args:
            instruction: The instruction to process
            account_keys: List of account keys
            
        Returns:
            InstructionMetadata if successful, None if error
        """
        try:
            # Convert instruction to standardized dict format
            instr_dict = self.convert_to_dict(instruction, account_keys)
            if not instr_dict:
                return None
                
            # Extract program ID
            program_id = instr_dict.get('programId')
            if not program_id:
                return None
                
            # Create metadata
            metadata = InstructionMetadata(program_id=program_id)
            
            # Add accounts
            metadata.accounts = instr_dict.get('accounts', [])
            
            # Add data and parsed info
            data = instr_dict.get('data', {})
            if isinstance(data, dict):
                metadata.data = data.get('raw', '')
                parsed = data.get('parsed', {})
                if isinstance(parsed, dict):
                    metadata.instruction_type = parsed.get('type')
                    metadata.parsed_info = parsed.get('info', {})
                    
            return metadata
            
        except Exception as e:
            logger.error(f"Error processing instruction: {str(e)}", exc_info=True)
            return None
            
    def is_token_mint_instruction(self, instruction: Any) -> bool:
        """
        Check if instruction is a token mint operation
        
        Args:
            instruction: The instruction to check
            
        Returns:
            bool: True if mint instruction, False otherwise
        """
        try:
            # Handle string instruction
            if isinstance(instruction, str):
                # Check if instruction string matches mint types
                mint_types = {'mint', 'mintTo', 'MintTo', 'mint_to', 'createMint', 'CreateMint'}
                return instruction in mint_types
                
            # Handle dict instruction
            if isinstance(instruction, dict):
                # Check data field
                data = instruction.get('data', {})
                if isinstance(data, dict):
                    # Check parsed type
                    parsed = data.get('parsed', {})
                    if isinstance(parsed, dict):
                        instr_type = parsed.get('type')
                        if isinstance(instr_type, str):
                            return instr_type.lower() in {'mint', 'mintto', 'createmint', 'mint_to'}
                            
                    # Check raw data
                    raw = data.get('raw')
                    if isinstance(raw, str):
                        return raw.lower() in {'mint', 'mintto', 'createmint', 'mint_to'}
                        
                # Check direct type field
                instr_type = instruction.get('type')
                if isinstance(instr_type, str):
                    return instr_type.lower() in {'mint', 'mintto', 'createmint', 'mint_to'}
                    
            # Handle object with attributes
            if hasattr(instruction, 'type'):
                instr_type = getattr(instruction, 'type')
                if isinstance(instr_type, str):
                    return instr_type.lower() in {'mint', 'mintto', 'createmint', 'mint_to'}
                    
            # Handle raw data attribute
            if hasattr(instruction, 'data'):
                data = getattr(instruction, 'data')
                if isinstance(data, str):
                    return data.lower() in {'mint', 'mintto', 'createmint', 'mint_to'}
                    
            return False
            
        except Exception as e:
            logger.debug(f"Error checking mint instruction: {str(e)}")
            return False
            
    def is_valid_program_id(self, program_id: str) -> bool:
        """
        Validate program ID format and characteristics
        
        Args:
            program_id: The program ID to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if not program_id:
                return False
                
            # Convert to string if needed
            if not isinstance(program_id, str):
                program_id = str(program_id)
                
            # Check length
            if len(program_id) < 32 or len(program_id) > 44:
                return False
                
            # Check characters
            valid_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
            return all(c in valid_chars for c in program_id)
            
        except Exception as e:
            logger.error(f"Error validating program ID: {str(e)}", exc_info=True)
            return False
            
    def get_instruction_type(self, program_id: str) -> Optional[str]:
        """
        Get instruction type based on program ID
        
        Args:
            program_id: The program ID to check
            
        Returns:
            str: Instruction type if known, None otherwise
        """
        return self.TOKEN_PROGRAMS.get(program_id)
        
    def is_system_program(self, program_id: str) -> bool:
        """
        Check if program ID is a known system program
        
        Args:
            program_id: The program ID to check
            
        Returns:
            bool: True if system program, False otherwise
        """
        return program_id in self.SYSTEM_ADDRESSES
