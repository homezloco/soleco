"""
Solana utilities for working with transactions, instructions, and accounts.
RPC connection management is in solana_rpc.py.
"""

import logging
from typing import Dict, Any, Optional, Union, List
from solders.pubkey import Pubkey
from solders.instruction import Instruction
from solders.transaction import Transaction
from solders.message import Message
from solders.signature import Signature
from solana.rpc.types import TxOpts
from .solana_rpc import SolanaConnectionPool, SolanaClient

logger = logging.getLogger(__name__)

async def get_signatures_for_address(
    pool: SolanaConnectionPool,
    address: Union[str, Pubkey],
    before: Optional[str] = None,
    until: Optional[str] = None,
    limit: Optional[int] = None,
    commitment: Optional[str] = None,
    start_slot: Optional[int] = None,
    end_slot: Optional[int] = None,
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    """Get signatures for address using the connection pool"""
    return await pool.get_signatures_for_address(
        address=address,
        before=before,
        until=until,
        limit=limit,
        commitment=commitment,
        start_slot=start_slot,
        end_slot=end_slot,
        max_retries=max_retries
    )

async def get_transaction_data(
    client: SolanaClient,
    signature: Union[str, Signature],
    commitment: Optional[str] = None,
    max_supported_transaction_version: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Get transaction data using a specific client"""
    try:
        return await client.get_transaction(
            signature=signature,
            commitment=commitment,
            max_supported_transaction_version=max_supported_transaction_version
        )
    except Exception as e:
        logger.error(f"Error getting transaction data for {signature}: {str(e)}")
        return None

def parse_transaction_instruction(
    instruction: Dict[str, Any],
    program_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Parse a transaction instruction"""
    try:
        # Extract basic instruction data
        parsed_instruction = {
            'program_id': instruction.get('program_id'),
            'accounts': instruction.get('accounts', []),
            'data': instruction.get('data')
        }
        
        # Add parsed data if available
        if 'parsed' in instruction:
            parsed_instruction['parsed'] = instruction['parsed']
            
        # Filter by program if specified
        if program_id and parsed_instruction['program_id'] != program_id:
            return None
            
        return parsed_instruction
        
    except Exception as e:
        logger.error(f"Error parsing instruction: {e}")
        return None

def extract_mint_from_instruction(instruction: Dict[str, Any]) -> Optional[str]:
    """Extract mint address from a create token instruction"""
    try:
        if not instruction.get('parsed'):
            return None
            
        parsed = instruction['parsed']
        
        # Check for token creation
        if parsed.get('type') == 'initializeMint':
            return parsed.get('info', {}).get('mint')
            
        # Check for mint to instruction
        if parsed.get('type') == 'mintTo':
            return parsed.get('info', {}).get('mint')
            
        return None
        
    except Exception as e:
        logger.error(f"Error extracting mint from instruction: {e}")
        return None

def is_token_creation_instruction(instruction: Dict[str, Any]) -> bool:
    """Check if an instruction is a token creation instruction"""
    try:
        if not instruction.get('parsed'):
            return False
            
        parsed = instruction['parsed']
        
        # Check for initialize mint
        if parsed.get('type') == 'initializeMint':
            return True
            
        # Check for create account
        if parsed.get('type') == 'createAccount':
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error checking token creation instruction: {e}")
        return False

def parse_transaction_for_mints(
    transaction_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Parse a transaction to find mint creations and token transfers"""
    try:
        result = {
            'new_mints': [],
            'mint_transfers': []
        }
        
        if not transaction_data or 'message' not in transaction_data:
            return result
            
        # Get instructions
        instructions = transaction_data['message'].get('instructions', [])
        
        # Parse each instruction
        for instruction in instructions:
            parsed = parse_transaction_instruction(instruction)
            if not parsed:
                continue
                
            # Check for mint creation
            if is_token_creation_instruction(parsed):
                mint = extract_mint_from_instruction(parsed)
                if mint:
                    result['new_mints'].append(mint)
                    
            # Check for mint transfers
            if parsed.get('parsed', {}).get('type') == 'mintTo':
                mint = extract_mint_from_instruction(parsed)
                if mint:
                    result['mint_transfers'].append(mint)
                    
        return result
        
    except Exception as e:
        logger.error(f"Error parsing transaction for mints: {e}")
        return {'new_mints': [], 'mint_transfers': []}
