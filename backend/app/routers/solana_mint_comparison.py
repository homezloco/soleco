import time
import logging
import sys
import os
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
from solders.pubkey import Pubkey
from solana.rpc.api import Client  # Synchronous client
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import solders.transaction_status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configure logging to DEBUG level
logging.getLogger().setLevel(logging.DEBUG)

# Known token program IDs
TOKEN_PROGRAM_IDS = {
    'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'Token Program',
    'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL': 'Associated Token Program',
    'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb': 'Token Program 2022'
}

# Known instruction types that might involve mint addresses
MINT_INSTRUCTION_TYPES = {
    0: 'InitializeMint',
    1: 'MintTo',
    7: 'InitializeMint2',
    14: 'CreateMint',
}

# Known system addresses to exclude
SYSTEM_ADDRESSES = {
    'So11111111111111111111111111111111111111112',  # Native SOL mint
    '11111111111111111111111111111111',  # System program
}

def is_valid_mint_address(addr: str) -> bool:
    """
    Validate if a string is a valid Solana mint address
    """
    if not isinstance(addr, str) or len(addr) < 32:
        return False
        
    try:
        Pubkey.from_string(addr)
        return True
    except (ValueError, TypeError):
        return False

def safe_serialize(obj):
    """
    Safely serialize complex Solders objects to JSON-compatible format
    
    Args:
        obj: Any object to be serialized
    
    Returns:
        JSON-serializable representation of the object
    """
    try:
        # Handle basic types first
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        
        # Handle list and tuple types
        if isinstance(obj, (list, tuple)):
            return [safe_serialize(item) for item in obj]
        
        # Handle dictionary types
        if isinstance(obj, dict):
            return {str(k): safe_serialize(v) for k, v in obj.items()}
        
        # Use string representation as fallback
        return str(obj)
    
    except Exception as e:
        logger.warning(f"Serialization error: {e}")
        return str(obj)


def patch_proxy_initialization():
    """
    Globally patch initialization methods to remove proxy arguments
    """
    try:
        import solana.rpc.api
        import solana.rpc.providers.http
        import httpx
        import functools
        
        def strip_proxy_kwargs(func):
            """
            Decorator to remove proxy-related arguments from any method
            """
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Remove common proxy-related arguments
                kwargs.pop('proxy', None)
                kwargs.pop('proxies', None)
                kwargs.pop('http_proxy', None)
                kwargs.pop('https_proxy', None)
                
                # Remove any other potential proxy arguments
                kwargs = {k: v for k, v in kwargs.items() 
                          if not any(proxy_key in k.lower() for proxy_key in ['proxy', 'proxies'])}
                
                return func(*args, **kwargs)
            return wrapper
        
        # Patch Client initialization methods
        original_client_init = httpx.Client.__init__
        httpx.Client.__init__ = strip_proxy_kwargs(original_client_init)
        
        # Patch Solana HTTP Provider initialization
        original_http_provider_init = solana.rpc.providers.http.HTTPProvider.__init__
        solana.rpc.providers.http.HTTPProvider.__init__ = strip_proxy_kwargs(original_http_provider_init)
        
        # Patch Solana Client initialization
        original_solana_client_init = solana.rpc.api.Client.__init__
        solana.rpc.api.Client.__init__ = strip_proxy_kwargs(original_solana_client_init)
        
        logger.info("Successfully applied comprehensive proxy removal monkey patch")
        return True
    
    except Exception as e:
        logger.error(f"Error applying proxy removal monkey patch: {e}")
        return False


def create_robust_client():
    """
    Create a Solana RPC client with robust configuration and full method support
    """
    # Ensure proxy patch is applied
    patch_proxy_initialization()
    
    try:
        # List of potential RPC endpoints
        rpc_endpoints = [
            {"url": "https://api.mainnet-beta.solana.com", "name": "Solana Mainnet"},
            {"url": "https://rpc.ankr.com/solana", "name": "Ankr"}
        ]
        
        for endpoint in rpc_endpoints:
            try:
                # Create client with minimal arguments
                client = Client(endpoint=endpoint["url"])
                
                # Validate connection
                try:
                    version_info = client.get_version()
                    logger.info(f"Successfully connected to {endpoint['name']}")
                    return client
                except Exception as validation_error:
                    logger.warning(f"RPC connection validation failed for {endpoint['name']}: {validation_error}")
                    continue
            
            except Exception as client_error:
                logger.warning(f"Client initialization error for {endpoint['name']}: {client_error}")
                continue
        
        logger.error("Failed to connect to any Solana RPC endpoint")
        return None
    
    except Exception as e:
        logger.error(f"Unexpected error in Solana RPC client creation: {e}")
        return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((Exception)),
    before_sleep=before_sleep_log(logger, logging.INFO)
)
async def get_block_with_retry(client, block_number):
    """
    Retrieve a block with retry logic
    """
    try:
        response = client.get_block(
            block_number,
            encoding='jsonParsed',
            max_supported_transaction_version=0
        )
        # Add a small delay between requests to respect rate limits
        await asyncio.sleep(0.2)
        return response
    except Exception as e:
        if "429" in str(e):
            logger.warning(f"Rate limit hit for block {block_number}, backing off...")
            raise  # This will trigger the retry with exponential backoff
        if "Block not available" in str(e):
            logger.info(f"Block {block_number} not available")
            return None
        raise


def process_mint_address(addr: Any, source: str, tx_index: int, extra_info: str = "", processed_addresses: set = None, mint_addresses: set = None) -> bool:
    """Helper function to process and validate a potential mint address"""
    try:
        # Convert Pubkey to string if needed
        if isinstance(addr, Pubkey):
            addr = str(addr)
        elif not isinstance(addr, str):
            logger.debug(f"Tx {tx_index}: Invalid address type: {type(addr)}")
            return False
            
        # Clean the address string
        addr = addr.strip()
        
        # Log the validation steps
        if processed_addresses is None:
            processed_addresses = set()
        if addr in processed_addresses:
            logger.debug(f"Tx {tx_index}: Address already processed: {addr}")
            return False
            
        if addr in SYSTEM_ADDRESSES:
            logger.debug(f"Tx {tx_index}: System address found: {addr}")
            return False
                
        if mint_addresses is None:
            mint_addresses = set()
        processed_addresses.add(addr)
        mint_addresses.add(addr)
        
        # Only log if it's a new unique address
        logger.debug(
            f"Transaction {tx_index}: Found new unique mint address:"
            f"\n    Source: {source}"
            f"\n    Mint: {addr}"
            + (f"\n    {extra_info}" if extra_info else "")
        )
        return True
    except Exception as e:
        logger.debug(f"Error processing mint address in tx {tx_index}: {str(e)}")
        return False

def process_token_balances(balances: List[Any], tx_index: int, balance_type: str, processed_addresses: set = None, mint_addresses: set = None) -> int:
    """Process token balances and extract mint addresses"""
    if not balances:
        return 0
    
    logger.debug(f"Processing {len(balances)} {balance_type} token balances for tx {tx_index}")
    new_mints_found = 0
    for balance in balances:
        try:
            if not balance:
                continue
            
            mint = getattr(balance, 'mint', None)
            if not mint:
                continue
            
            logger.debug(f"Found potential mint from {balance_type} balance in tx {tx_index}: {mint}")
            owner = getattr(balance, 'owner', 'Unknown')
            ui_token_amount = getattr(balance, 'ui_token_amount', {})
            
            # Handle different token amount formats
            amount = 0
            if isinstance(ui_token_amount, dict):
                amount = ui_token_amount.get('uiAmount', 0)
            elif hasattr(ui_token_amount, 'ui_amount'):
                amount = ui_token_amount.ui_amount or 0
            
            decimals = None
            if isinstance(ui_token_amount, dict):
                decimals = ui_token_amount.get('decimals')
            elif hasattr(ui_token_amount, 'decimals'):
                decimals = ui_token_amount.decimals
            
            if process_mint_address(mint, "token balance", tx_index, processed_addresses, mint_addresses):
                new_mints_found += 1
                
        except Exception as e:
            logger.debug(f"Error processing token balance in tx {tx_index}: {str(e)}")
            continue
                
    return new_mints_found

def process_instruction(instruction: Any, account_keys: List[Any], tx_index: int, instr_index: int, processed_addresses: set = None, mint_addresses: set = None) -> int:
    """Process a single instruction to extract mint addresses"""
    try:
        program_id = str(getattr(instruction, 'program_id', None))
        if not program_id:
            return 0
        
        logger.debug(f"Tx {tx_index}, Instruction {instr_index} program_id: {program_id}")
        
        if program_id not in TOKEN_PROGRAM_IDS:
            return 0
        
        program_name = TOKEN_PROGRAM_IDS[program_id]
        logger.debug(f"Found token program instruction: {program_name}")
        
        instr_data = getattr(instruction, 'data', b'')
        if not instr_data:
            logger.debug(f"No instruction data for {program_name} instruction")
            return 0
        
        try:
            instr_type = int(instr_data[0])
            logger.debug(f"Instruction type: {instr_type}")
        except (IndexError, ValueError) as e:
            logger.debug(f"Error getting instruction type: {e}")
            return 0
        
        if instr_type not in MINT_INSTRUCTION_TYPES:
            return 0
        
        instr_name = MINT_INSTRUCTION_TYPES[instr_type]
        logger.debug(f"Found mint instruction: {instr_name}")
        
        account_indices = getattr(instruction, 'accounts', []) or []
        logger.debug(f"Account indices: {account_indices}")
        
        new_mints_found = 0
        # For mint initialization, check both first and second accounts
        # as mint address location can vary by instruction type
        for acc_idx in range(min(2, len(account_indices))):
            try:
                mint_index = account_indices[acc_idx]
                if mint_index >= len(account_keys):
                    logger.debug(f"Account index {mint_index} out of range (max {len(account_keys)-1})")
                    continue
                    
                potential_mint = str(account_keys[mint_index])
                logger.debug(f"Found potential mint address: {potential_mint}")
                
                extra_info = (
                    f"Program: {program_name}"
                    f"\n    Instruction: {instr_name}"
                    f"\n    Account Index: {acc_idx}"
                )
                
                if process_mint_address(potential_mint, "instruction", tx_index, extra_info, processed_addresses, mint_addresses):
                    new_mints_found += 1
                    
            except (IndexError, AttributeError) as e:
                logger.debug(f"Error accessing account key {acc_idx} in tx {tx_index}, instruction {instr_index}: {e}")
                continue
                    
        return new_mints_found
            
    except Exception as e:
        logger.debug(f"Error processing instruction {instr_index} in tx {tx_index}: {str(e)}")
        return 0

def extract_mint_addresses_from_block(block_data) -> List[str]:
    """
    Extract mint addresses from a Solana block
    
    Args:
        block_data: Solana block response object
    
    Returns:
        List of unique mint addresses found in the block
    """
    mint_addresses = set()
    processed_addresses = set()  # Track already processed addresses
    
    try:
        transactions = block_data.transactions
        total_transactions = len(transactions)
        logger.info(f"Processing block with {total_transactions} transactions")
        
        # Log first transaction structure for debugging
        if transactions:
            first_tx = transactions[0]
            logger.debug(f"First transaction type: {type(first_tx)}")
            logger.debug(f"First transaction attributes: {dir(first_tx)}")
            if hasattr(first_tx, 'transaction'):
                tx_obj = first_tx.transaction
                logger.debug(f"Transaction object type: {type(tx_obj)}")
                logger.debug(f"Transaction object attributes: {dir(tx_obj)}")
                if hasattr(tx_obj, 'message'):
                    msg = tx_obj.message
                    logger.debug(f"Message type: {type(msg)}")
                    logger.debug(f"Message attributes: {dir(msg)}")
        
        total_new_mints = 0
        for tx_index, tx in enumerate(transactions, 1):
            try:
                if not isinstance(tx, solders.transaction_status.EncodedTransactionWithStatusMeta):
                    logger.debug(f"Transaction {tx_index} type: {type(tx)}")
                    continue
                    
                meta = tx.meta
                if meta is None:
                    logger.debug(f"Transaction {tx_index} meta is None")
                    continue
                    
                if hasattr(meta, 'err') and meta.err is not None:
                    logger.debug(f"Transaction {tx_index} has error: {meta.err}")
                    continue

                # Process token balances
                pre_balances = getattr(meta, 'pre_token_balances', [])
                post_balances = getattr(meta, 'post_token_balances', [])
                
                if pre_balances or post_balances:
                    logger.debug(f"Transaction {tx_index} has token balances - Pre: {len(pre_balances)}, Post: {len(post_balances)}")
                
                new_mints_from_pre = process_token_balances(pre_balances, tx_index, "pre", processed_addresses, mint_addresses)
                new_mints_from_post = process_token_balances(post_balances, tx_index, "post", processed_addresses, mint_addresses)
                total_new_mints += new_mints_from_pre + new_mints_from_post

                # Process transaction instructions
                transaction = tx.transaction
                if not transaction:
                    logger.debug(f"Transaction {tx_index} has no transaction data")
                    continue
                    
                message = getattr(transaction, 'message', None)
                if not message:
                    logger.debug(f"Transaction {tx_index} has no message")
                    continue
                
                instructions = getattr(message, 'instructions', []) or []
                account_keys = getattr(message, 'account_keys', []) or []
                
                if instructions:
                    logger.debug(f"Transaction {tx_index} has {len(instructions)} instructions")
                    # Log first instruction of first transaction for debugging
                    if tx_index == 1 and instructions:
                        first_instr = instructions[0]
                        logger.debug(f"First instruction type: {type(first_instr)}")
                        logger.debug(f"First instruction attributes: {dir(first_instr)}")
                
                for instr_index, instruction in enumerate(instructions):
                    new_mints = process_instruction(instruction, account_keys, tx_index, instr_index, processed_addresses, mint_addresses)
                    total_new_mints += new_mints
            
            except Exception as tx_error:
                logger.error(f"Error processing transaction {tx_index}/{total_transactions}: {tx_error}")
                continue
                
            if tx_index % 100 == 0:
                logger.info(f"Processed {tx_index}/{total_transactions} transactions, found {total_new_mints} unique mints so far")
    
    except Exception as block_error:
        logger.error(f"Error extracting mint addresses from block: {block_error}")
        return []

    # Convert to sorted list for consistent output
    valid_mint_addresses = sorted(mint_addresses)

    logger.info(f"Completed processing {total_transactions} transactions. Found {len(valid_mint_addresses)} unique mint addresses")

    if valid_mint_addresses:
        logger.debug("Unique mint addresses found:")
        for addr in valid_mint_addresses[:10]:
            logger.debug(f"  - {addr}")
        if len(valid_mint_addresses) > 10:
            logger.debug(f"  ... and {len(valid_mint_addresses) - 10} more")

    return valid_mint_addresses


async def get_mints_from_recent_blocks(limit: int = 1) -> Dict[str, List[str]]:
    """
    Retrieve mint addresses from a recent Solana block
    """
    client = create_robust_client()
    if client is None:
        logger.error("Could not create Solana RPC client")
        return {"error": "Could not create Solana RPC client"}
    
    try:
        # Get current slot
        current_slot = client.get_slot().value
        logger.info(f"Current slot: {current_slot}")
        
        # Get the most recent finalized block
        target_slot = current_slot - 5  # Look at a block that's definitely finalized
        
        try:
            logger.info(f"Attempting to retrieve block {target_slot}")
            block_response = await get_block_with_retry(client, target_slot)
            
            if not block_response:
                return {"message": f"Block {target_slot} data not available"}
            
            # Get the actual block data
            block_data = block_response.value
            if block_data is None:
                return {"message": "Block data is None"}
                
            # Get transactions from the block
            transactions = block_data.transactions
            if not transactions:
                return {"message": f"No transactions found in block {target_slot}"}
                
            logger.info(f"Found {len(transactions)} transactions in block {target_slot}")
            
            # Extract mint addresses from transactions
            mint_addresses = extract_mint_addresses_from_block(block_data)
            
            return {str(target_slot): mint_addresses}
                
        except Exception as e:
            logger.error(f"Error getting block data: {e}")
            return {"error": f"Failed to get block data: {str(e)}"}
    
    except Exception as e:
        logger.error(f"Error in get_mints_from_recent_blocks: {e}")
        return {"error": str(e)}


# Create FastAPI router
router = APIRouter(
    tags=["solana"],
    responses={404: {"description": "Not found"}},
)

@router.get("/comparison/solana/mints")  # This will be prefixed with /api/solana from main.py
async def get_mints(limit: Optional[int] = Query(1, description="Number of recent blocks to retrieve")):
    """
    Get mint addresses from recent Solana blocks.
    """
    try:
        logger.debug("Starting mint address extraction")
        result = await get_mints_from_recent_blocks(limit)
        logger.debug(f"Extraction complete, result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error getting mints: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Example usage
if __name__ == "__main__":
    # Set logging to DEBUG for more detailed output
    logging.getLogger().setLevel(logging.DEBUG)
    recent_block_mints = asyncio.run(get_mints_from_recent_blocks())  # Default to 1 block
    logger.info("Mint Addresses per Block:")
    for block, mints in recent_block_mints.items():
        logger.info("Block {}: {} mints".format(block, len(mints)))
        logger.debug("Mints: {}".format(mints))
