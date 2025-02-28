"""
Helper functions and utilities for Solana query operations.
"""

from typing import Dict, List, Any, Union, Optional
import base64
import json
import logging
from .solana_types import (
    RPCError,
    RetryableError,
    RateLimitError,
    SlotSkippedError
)

# Configure logging
logger = logging.getLogger('solana.helpers')

# Default configurations
DEFAULT_BLOCK_OPTIONS = {
    "transactionDetails": "full",
    "rewards": False
}

DEFAULT_BATCH_SIZE = 10
DEFAULT_COMMITMENT = "finalized"

def handle_rpc_error(error: Exception, context: str) -> None:
    """Standardized error handling for RPC calls."""
    error_msg = str(error).lower()
    
    if "429" in error_msg or "rate limit" in error_msg:
        raise RateLimitError(f"Rate limit exceeded: {context}")
    elif "timeout" in error_msg:
        raise RetryableError(f"Timeout: {context}")
    elif "slot was skipped" in error_msg:
        raise SlotSkippedError(f"Slot skipped: {context}")
    elif "block not available" in error_msg:
        logger.info(f"Block not available: {context}")
        return None
    else:
        raise RPCError(f"RPC error in {context}: {error}")

def extract_message(tx: Any) -> Dict[str, Any]:
    """Extract and decode transaction message."""
    message = {}
    
    try:
        if isinstance(tx, dict):
            # Handle transaction wrapper
            if 'transaction' in tx:
                tx = tx['transaction']
                
            message = tx.get('message', {})
            if isinstance(message, str):
                try:
                    decoded = base64.b64decode(message)
                    message = json.loads(decoded)
                except:
                    logger.error("Failed to decode base64 message")
                    message = {}
        elif hasattr(tx, 'message'):
            message = tx.message
            if hasattr(message, '__dict__'):
                message = message.__dict__
                
        if not isinstance(message, dict):
            logger.debug(f"Invalid message type: {type(message)}")
            message = {}
            
    except Exception as e:
        logger.error(f"Error extracting message: {str(e)}")
        message = {}
        
    return message

def extract_account_keys(message: Dict[str, Any]) -> List[str]:
    """Extract account keys from message."""
    keys = []
    try:
        for key in message.get('accountKeys', []):
            if isinstance(key, dict):
                pubkey = key.get('pubkey')
                if pubkey:
                    keys.append(str(pubkey))
            elif isinstance(key, str):
                keys.append(str(key))
    except Exception as e:
        logger.error(f"Error extracting account keys: {str(e)}")
    return keys

def extract_signatures(tx: Any) -> List[str]:
    """Extract signatures from transaction."""
    signatures = []
    try:
        if isinstance(tx, dict):
            # Handle transaction wrapper
            if 'transaction' in tx:
                tx = tx['transaction']
                
            sigs = tx.get('signatures', [])
            if isinstance(sigs, (list, tuple)):
                signatures.extend(str(sig) for sig in sigs if sig)
    except Exception as e:
        logger.error(f"Error extracting signatures: {str(e)}")
    return signatures

def transform_instruction(instr: Any, account_keys: List[str], idx: int) -> Dict[str, Any]:
    """Transform a single instruction into standardized format."""
    try:
        # Handle raw string instruction
        if isinstance(instr, str):
            try:
                # Try to decode as base64
                decoded = base64.b64decode(instr)
                try:
                    # Try to parse as JSON
                    parsed = json.loads(decoded)
                    if isinstance(parsed, dict):
                        logger.debug(f"Successfully decoded instruction {idx} from base64 JSON")
                        return transform_instruction(parsed, account_keys, idx)
                except json.JSONDecodeError:
                    pass
            except:
                pass
                
            # If decoding fails, wrap raw string
            logger.debug(f"Wrapping raw string instruction {idx}")
            return {
                'programId': account_keys[0] if account_keys else '',
                'accounts': account_keys[1:] if len(account_keys) > 1 else [],
                'data': {
                    'raw': instr,
                    'parsed': None
                }
            }
            
        # Handle dict instruction
        if isinstance(instr, dict):
            logger.debug(f"Processing dict instruction {idx}")
            
            # Get program ID
            program_id = instr.get('programId', '')
            
            # Get accounts
            accounts = []
            raw_accounts = instr.get('accounts', [])
            if isinstance(raw_accounts, list):
                # Convert account indexes to addresses
                for acc_idx in raw_accounts:
                    if isinstance(acc_idx, int) and 0 <= acc_idx < len(account_keys):
                        accounts.append(account_keys[acc_idx])
                        
            # Get instruction data
            data = instr.get('data', '')
            if isinstance(data, dict):
                # Keep parsed data structure
                parsed_data = data
            else:
                # Try to decode if string
                if isinstance(data, str):
                    try:
                        decoded = base64.b64decode(data)
                        try:
                            parsed = json.loads(decoded)
                            parsed_data = {
                                'raw': data,
                                'parsed': parsed
                            }
                        except json.JSONDecodeError:
                            parsed_data = {
                                'raw': data,
                                'parsed': None
                            }
                    except:
                        parsed_data = {
                            'raw': data,
                            'parsed': None
                        }
                else:
                    parsed_data = {
                        'raw': str(data),
                        'parsed': None
                    }
                
            instruction = {
                'programId': program_id,
                'accounts': accounts,
                'data': parsed_data
            }
            
            # Add program ID from index if needed
            if not instruction['programId']:
                program_idx = instr.get('programIdIndex')
                if isinstance(program_idx, int) and 0 <= program_idx < len(account_keys):
                    instruction['programId'] = account_keys[program_idx]
                    logger.debug(f"Added program ID from index for instruction {idx}")
                    
            # Add account addresses from indexes if needed
            if not instruction['accounts']:
                account_indexes = instr.get('accountIndexes', [])
                if isinstance(account_indexes, list):
                    instruction['accounts'] = [
                        account_keys[idx] 
                        for idx in account_indexes 
                        if isinstance(idx, int) and 0 <= idx < len(account_keys)
                    ]
                    logger.debug(f"Added {len(instruction['accounts'])} accounts from indexes")
                    
            return instruction
            
        # Handle unknown format
        logger.warning(f"Unknown instruction format {type(instr)} for instruction {idx}")
        return {
            'programId': account_keys[0] if account_keys else '',
            'accounts': account_keys[1:] if len(account_keys) > 1 else [],
            'data': {
                'raw': str(instr),
                'parsed': None
            }
        }
        
    except Exception as e:
        logger.error(f"Error transforming instruction {idx}: {str(e)}")
        return {
            'programId': '',
            'accounts': [],
            'data': {
                'raw': '',
                'parsed': None
            }
        }

def build_transaction_structure(tx: Any, meta: Any) -> Dict[str, Any]:
    """Build a standardized transaction structure from raw data."""
    try:
        if not tx:
            logger.debug("Empty transaction data")
            return {}
            
        # Extract message
        message = extract_message(tx)
        if not message:
            logger.debug("Empty message in transaction")
            return {}
            
        # Get account keys
        account_keys = extract_account_keys(message)
        if not account_keys:
            logger.debug("No account keys found in message")
            return {}
            
        # Process instructions
        instructions = []
        raw_instructions = message.get('instructions', [])
        
        if not raw_instructions:
            logger.debug("No instructions found in message")
            return {}
            
        logger.debug(f"Processing {len(raw_instructions)} instructions")
        
        # Transform each instruction
        for idx, instr in enumerate(raw_instructions):
            # Handle string instruction
            if isinstance(instr, str):
                instruction = {
                    'programId': account_keys[0] if account_keys else '',
                    'accounts': account_keys[1:] if len(account_keys) > 1 else [],
                    'data': {
                        'raw': instr,
                        'parsed': None
                    }
                }
            else:
                instruction = transform_instruction(instr, account_keys, idx)
                
            if instruction:
                instructions.append(instruction)
        
        # Build final structure
        result = {
            'transaction': {
                'message': {
                    'accountKeys': account_keys,
                    'instructions': instructions,
                    'recentBlockhash': message.get('recentBlockhash', ''),
                    'header': message.get('header', {})
                },
                'signatures': extract_signatures(tx)
            },
            'meta': meta
        }
        
        logger.debug(f"Built transaction structure with {len(instructions)} instructions")
        return result
        
    except Exception as e:
        logger.error(f"Error building transaction structure: {str(e)}")
        return {}

def transform_transaction_data(tx_data: Union[List, Dict]) -> Dict[str, Any]:
    """Transform raw transaction data into a standardized format."""
    try:
        # Extract transaction and meta data
        if isinstance(tx_data, list):
            tx = tx_data[0] if tx_data else None
            meta = tx_data[1] if len(tx_data) > 1 else None
        else:
            tx = tx_data
            meta = tx_data.get('meta') if isinstance(tx_data, dict) else None
            
        # Handle transaction object
        if isinstance(tx, dict) and 'transaction' in tx:
            tx = tx['transaction']
            
        # Build structure
        return build_transaction_structure(tx, meta)
        
    except Exception as e:
        logger.error(f"Error transforming transaction data: {str(e)}")
        return {}

def get_block_options(commitment: str = DEFAULT_COMMITMENT) -> Dict[str, Any]:
    """Get standardized block options with the given commitment level."""
    return {
        **DEFAULT_BLOCK_OPTIONS,
        "commitment": commitment
    }

def create_slot_batches(start_slot: int, end_slot: int, batch_size: int = DEFAULT_BATCH_SIZE) -> List[List[int]]:
    """Create batches of slots for parallel processing."""
    slots = list(range(start_slot, end_slot + 1))
    return [slots[i:i + batch_size] for i in range(0, len(slots), batch_size)]
