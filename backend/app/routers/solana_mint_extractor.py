import time 
import logging
import sys
import os
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
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
from ..utils.solana_query import SolanaQueryHandler
from ..utils.handlers.mint_extractor import MintExtractor
from ..utils.solana_rpc import get_connection_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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

async def create_robust_client():
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
                    version_info = await client.get_version()
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

async def get_block_with_retry(client, block_number: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a block with retry logic
    
    Args:
        client: Solana RPC client
        block_number: Block number to retrieve
        
    Returns:
        Block data if successful, None otherwise
    """
    max_retries = 3
    retry_delay = 1.0  # seconds
    
    for attempt in range(max_retries):
        try:
            # Get block with proper async handling
            response = await client.get_block(block_number)
            if not response:
                logger.warning(f"Empty response for block {block_number}")
                continue
                
            # Validate response
            if not hasattr(response, 'value'):
                logger.warning(f"Invalid response format for block {block_number}")
                continue
                
            return response.value
            
        except Exception as e:
            logger.error(f"Error getting block {block_number} (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
            
    return None

async def get_mints_from_recent_blocks(limit: int = 1) -> Dict[str, Any]:
    """
    Retrieve mint addresses from recent Solana blocks

    Args:
        limit: Number of recent blocks to scan (1-10)

    Returns:
        Dictionary containing:
        - blocks: List of dictionaries with block-specific data
        - summary: Overall statistics across all blocks
    """
    try:
        # Create robust client with proper async initialization
        client = await create_robust_client()
        if client is None:
            logger.error("Could not create Solana RPC client")
            return {"error": "Could not create Solana RPC client"}
        
        # Get current slot
        slot_response = await client.get_slot()
        if not slot_response or not hasattr(slot_response, 'value'):
            logger.error("Invalid slot response")
            return {"error": "Could not get current slot"}
            
        current_slot = slot_response.value
        logger.info(f"Current slot: {current_slot}")
        
        # Initialize response structure
        response = {
            "blocks": [],
            "summary": {
                "total_blocks_scanned": 0,
                "total_transactions": 0,
                "total_transactions_with_mints": 0,
                "total_mint_addresses": 0,
                "unique_mint_addresses": set(),
                "processing_time": 0,
                "errors": []
            }
        }
        
        # Process blocks
        start_time = time.time()
        for block_offset in range(limit):
            try:
                # Calculate target slot for this block
                target_slot = current_slot - 5 - block_offset  # Look at blocks that are definitely finalized
                logger.info(f"Processing block at slot {target_slot}")
                
                # Get block data with proper async handling
                block_response = await get_block_with_retry(client, target_slot)
                if not block_response:
                    logger.warning(f"Block {target_slot} data not available")
                    response["summary"]["errors"].append(f"Block {target_slot} data not available")
                    continue
                
                # Extract mint addresses from block
                block_result = extract_mint_addresses_from_block(block_response)
                
                # Add block-specific results
                block_data = {
                    "slot": target_slot,
                    "transactions": block_result["total_transactions"],
                    "transactions_with_mints": block_result["transactions_with_mints"],
                    "mint_addresses": list(block_result["mint_addresses"]),
                    "pump_token_addresses": list(block_result["pump_token_addresses"]),
                    "transaction_stats": block_result["transaction_stats"],
                    "processing_time": block_result["processing_time"],
                    "errors": block_result["errors"]
                }
                response["blocks"].append(block_data)
                
                # Update summary statistics
                response["summary"]["total_blocks_scanned"] += 1
                response["summary"]["total_transactions"] += block_result["total_transactions"]
                response["summary"]["total_transactions_with_mints"] += block_result["transactions_with_mints"]
                response["summary"]["total_mint_addresses"] += len(block_result["mint_addresses"])
                response["summary"]["unique_mint_addresses"].update(block_result["mint_addresses"])
                response["summary"]["errors"].extend(block_result["errors"])
                
            except Exception as e:
                error_msg = f"Error processing block {target_slot}: {str(e)}"
                logger.error(error_msg)
                response["summary"]["errors"].append(error_msg)
        
        # Finalize summary
        end_time = time.time()
        response["summary"]["processing_time"] = end_time - start_time
        response["summary"]["unique_mint_addresses"] = list(response["summary"]["unique_mint_addresses"])
        
        return response
        
    except Exception as e:
        error_msg = f"Error in get_mints_from_recent_blocks: {str(e)}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "blocks": [],
            "summary": {
                "total_blocks_scanned": 0,
                "total_transactions": 0,
                "total_transactions_with_mints": 0,
                "total_mint_addresses": 0,
                "unique_mint_addresses": [],
                "processing_time": 0,
                "errors": [error_msg]
            }
        }

def extract_mint_addresses_from_block(block_data) -> Dict[str, Any]:
    """
    Extract mint addresses from a Solana block
    
    Args:
        block_data: Solana block response object (solders.rpc.responses.GetBlockResp)
    
    Returns:
        Dictionary containing:
        - total_transactions: Total number of transactions in the block
        - transactions_with_mints: Number of transactions with mint addresses
        - mint_addresses: List of unique mint addresses found in the block
        - pump_token_addresses: List of unique pump tokens found
        - transaction_stats: Breakdown of transaction types
        - processing_time: Time taken to process the block
        - errors: List of errors encountered during processing
    """
    start_time = time.time()
    
    # Initialize result structure
    result = {
        "total_transactions": 0,
        "transactions_with_mints": 0,
        "mint_addresses": set(),
        "pump_token_addresses": set(),
        "transaction_stats": {
            'vote': 0,
            'token': 0,
            'token2022': 0,
            'nft': 0,
            'marketplace': 0,
            'compute_budget': 0,
            'associated_token': 0,
            'other': 0
        },
        "processing_time": 0,
        "errors": []
    }
    
    try:
        # Validate block data
        if not block_data:
            logger.warning("Empty block data")
            return result
            
        # Extract transactions
        transactions = []
        if hasattr(block_data, 'transactions'):
            transactions = block_data.transactions
        elif isinstance(block_data, dict):
            transactions = block_data.get('transactions', [])
            
        if not transactions:
            logger.info("No transactions in block")
            return result
            
        result["total_transactions"] = len(transactions)
        
        # Process each transaction
        for tx_index, tx in enumerate(transactions):
            try:
                # Extract transaction and meta
                if isinstance(tx, dict):
                    transaction = tx.get('transaction')
                    meta = tx.get('meta')
                else:
                    transaction = getattr(tx, 'transaction', None)
                    meta = getattr(tx, 'meta', None)
                    
                if not transaction or not meta:
                    logger.debug(f"Skipping transaction {tx_index} - missing transaction or meta")
                    continue
                    
                # Extract message
                if isinstance(transaction, dict):
                    message = transaction.get('message')
                else:
                    message = getattr(transaction, 'message', None)
                    
                if not message:
                    logger.debug(f"Skipping transaction {tx_index} - missing message")
                    continue
                    
                # Extract account keys
                account_keys = []
                if isinstance(message, dict):
                    account_keys = message.get('accountKeys', [])
                else:
                    account_keys = getattr(message, 'account_keys', [])
                    
                if not account_keys:
                    logger.debug(f"Skipping transaction {tx_index} - no account keys")
                    continue
                    
                # Convert account keys to strings
                account_keys = [str(key) for key in account_keys]
                
                # Process instructions
                instructions = []
                if isinstance(message, dict):
                    instructions = message.get('instructions', [])
                else:
                    instructions = getattr(message, 'instructions', [])
                    
                if not instructions:
                    logger.debug(f"No instructions in transaction {tx_index}")
                    continue
                    
                # Process each instruction
                for instr_index, instruction in enumerate(instructions):
                    if process_instruction(instruction, account_keys, tx_index, instr_index) > 0:
                        result["transactions_with_mints"] += 1
                        
                # Process token balances
                if isinstance(meta, dict):
                    pre_balances = meta.get('preTokenBalances', [])
                    post_balances = meta.get('postTokenBalances', [])
                else:
                    pre_balances = getattr(meta, 'pre_token_balances', []) or []
                    post_balances = getattr(meta, 'post_token_balances', []) or []
                    
                if process_token_balances(pre_balances, tx_index, 'pre') > 0:
                    result["transactions_with_mints"] += 1
                if process_token_balances(post_balances, tx_index, 'post') > 0:
                    result["transactions_with_mints"] += 1
                    
            except Exception as e:
                error_msg = f"Error processing transaction {tx_index}: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
                
    except Exception as e:
        error_msg = f"Error processing block: {str(e)}"
        logger.error(error_msg)
        result["errors"].append(error_msg)
        
    # Finalize result
    result["processing_time"] = time.time() - start_time
    result["mint_addresses"] = list(result["mint_addresses"])
    result["pump_token_addresses"] = list(result["pump_token_addresses"])
    
    return result

def process_token_balances(token_balances, tx_index, balance_type):
    """Process token balances to extract mint addresses"""
    new_mints = 0
    for balance in token_balances:
        try:
            mint_address = str(balance.mint)
            if mint_address in processed_addresses:
                continue
            processed_addresses.add(mint_address)
            
            if mint_address.endswith('pump'):
                unique_pump_tokens.add(mint_address)
                logger.info(f"Found pump token: {mint_address} in {balance_type} token balance (tx {tx_index})")
                new_mints += 1
            else:
                mint_addresses.add(mint_address)
                logger.info(f"Found mint in {balance_type} token balance: {mint_address} (tx {tx_index})")
                new_mints += 1
        except Exception as e:
            logger.error(f"Error processing token balance: {str(e)}")
    return new_mints

def process_instruction(instruction: Any, account_keys: List[Any], tx_index: int, instr_index: int) -> int:
    """Process a single instruction to extract mint addresses"""
    found_mints = 0
    
    try:
        if not instruction or not account_keys:
            logger.debug("Skipping instruction - missing instruction or account keys")
            return 0
            
        # Get program ID - try multiple methods to extract it
        program_id = None
        
        logger.debug(f"Starting program ID extraction for instruction {instr_index} in tx {tx_index}")
        
        # Method 1: Check message header first (most reliable)
        if hasattr(instruction, 'message') and hasattr(instruction.message, 'header'):
            header = instruction.message.header
            if hasattr(header, 'program_ids') and header.program_ids:
                program_id = str(header.program_ids[0])  # First program ID is usually the main one
                logger.debug(f"Found program_id via message header: {program_id}")
            
        # Method 2: Direct program_id attribute
        if not program_id and hasattr(instruction, 'program_id'):
            try:
                program_id = str(instruction.program_id)
                logger.debug(f"Found program_id via direct attribute: {program_id}")
            except Exception as e:
                logger.debug(f"Error getting direct program_id: {e}")
            
        # Method 3: Parsed instruction program field
        if not program_id and hasattr(instruction, 'parsed'):
            try:
                parsed = instruction.parsed
                if isinstance(parsed, dict):
                    # Check direct program field
                    if 'program' in parsed:
                        program_id = str(parsed['program'])
                        logger.debug(f"Found program_id via parsed.program: {program_id}")
                    # Check nested info.program field
                    elif 'info' in parsed and isinstance(parsed['info'], dict):
                        info = parsed['info']
                        if 'program' in info:
                            program_id = str(info['program'])
                            logger.debug(f"Found program_id via parsed.info.program: {program_id}")
            except Exception as e:
                logger.debug(f"Error parsing instruction data: {e}")
            
        # Method 4: Program ID index in accounts
        if not program_id and hasattr(instruction, 'program_id_index'):
            try:
                idx = instruction.program_id_index
                if isinstance(idx, int) and idx < len(account_keys):
                    program_id = str(account_keys[idx])
                    logger.debug(f"Found program_id via program_id_index: {program_id}")
            except Exception as e:
                logger.debug(f"Error getting program_id from index: {e}")
                
        # Method 5: Last account in accounts array (common pattern)
        if not program_id and hasattr(instruction, 'accounts'):
            try:
                accounts = instruction.accounts
                if accounts and isinstance(accounts[-1], int) and accounts[-1] < len(account_keys):
                    program_id = str(account_keys[accounts[-1]])
                    logger.debug(f"Found program_id via last account: {program_id}")
            except Exception as e:
                logger.debug(f"Error getting program_id from accounts: {e}")
        
        # Method 6: Check inner instructions
        if not program_id and hasattr(instruction, 'inner_instructions'):
            try:
                inner_instructions = instruction.inner_instructions
                if inner_instructions and len(inner_instructions) > 0:
                    for inner in inner_instructions:
                        if hasattr(inner, 'program_id'):
                            program_id = str(inner.program_id)
                            logger.debug(f"Found program_id via inner instruction: {program_id}")
                            break
            except Exception as e:
                logger.debug(f"Error checking inner instructions: {e}")
        
        if not program_id:
            logger.debug(f"Could not determine program ID for instruction {instr_index} in tx {tx_index}")
            # Log detailed instruction data for debugging
            try:
                logger.debug(f"Instruction type: {type(instruction)}")
                logger.debug(f"Instruction attributes: {dir(instruction)}")
                if hasattr(instruction, '__dict__'):
                    logger.debug(f"Instruction dict: {instruction.__dict__}")
                if hasattr(instruction, 'data'):
                    logger.debug(f"Instruction data: {instruction.data}")
            except Exception as e:
                logger.debug(f"Error logging instruction details: {e}")
            return 0
        
        # Basic program ID validation
        if program_id:
            try:
                # Convert to string if needed
                if not isinstance(program_id, str):
                    program_id = str(program_id)
                
                # Basic format validation
                if len(program_id) < 32 or len(program_id) > 44:
                    logger.debug(f"Invalid program ID length: {len(program_id)}")
                    program_id = None
                elif not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in program_id):
                    logger.debug(f"Invalid program ID characters: {program_id}")
                    program_id = None
            except Exception as e:
                logger.debug(f"Error validating program ID: {e}")
                program_id = None
        
        logger.debug(f"Processing instruction {instr_index} in tx {tx_index}")
        logger.debug(f"Final Program ID: {program_id}")
        
        # Process token program instructions
        if program_id in ['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb']:
            # Token program typically has mint account as one of the first few accounts
            for i in range(min(3, len(account_keys))):  # Check first 3 accounts, safely
                account = account_keys[i]
                account_str = str(account)
                logger.debug(f"Checking token program account {i}: {account_str}")
                
                if process_mint_address(account_str, f"token program account {i}", tx_index):
                    found_mints += 1
                    
        # Process associated token program instructions
        elif program_id == 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL':
            accounts = getattr(instruction, 'accounts', []) or []
            if len(accounts) >= 3:  # Associated token accounts typically have mint as the 3rd account
                mint_index = accounts[2]
                if isinstance(mint_index, int) and mint_index < len(account_keys):
                    mint_account = str(account_keys[mint_index])
                    logger.debug(f"Found potential mint in ATA instruction: {mint_account}")
                    if process_mint_address(mint_account, "ATA program mint", tx_index):
                        found_mints += 1
                        
        # Process metadata program instructions
        elif program_id == 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s':
            accounts = getattr(instruction, 'accounts', []) or []
            if len(accounts) >= 2:  # Metadata accounts typically have mint as the 2nd account
                mint_index = accounts[1]
                if isinstance(mint_index, int) and mint_index < len(account_keys):
                    mint_account = str(account_keys[mint_index])
                    logger.debug(f"Found potential mint in metadata instruction: {mint_account}")
                    if process_mint_address(mint_account, "metadata program mint", tx_index):
                        found_mints += 1
                        
        # Process all accounts in the instruction for potential mint addresses
        accounts = getattr(instruction, 'accounts', []) or []
        for i, account_index in enumerate(accounts):
            if isinstance(account_index, int) and account_index < len(account_keys):
                account = account_keys[account_index]
                account_str = str(account)
                logger.debug(f"Processing account {i}: {account_str}")
                
                if process_mint_address(account_str, f"instruction account {i}", tx_index):
                    found_mints += 1
                    
        # Check instruction data for potential mint references
        data = getattr(instruction, 'data', None)
        if data and isinstance(data, (str, bytes)):
            try:
                data_str = str(data)
                # Look for potential Base58 encoded mint addresses in instruction data
                if len(data_str) >= 32 and len(data_str) <= 44:
                    if process_mint_address(data_str, "instruction data", tx_index):
                        found_mints += 1
            except:
                pass
                    
    except Exception as e:
        logger.error(f"Error processing instruction {instr_index} in tx {tx_index}: {str(e)}")
        return found_mints
            
    return found_mints

def process_mint_address(address: str, source: str, tx_index: int) -> bool:
    """Process and validate a potential mint address"""
    try:
        address_str = str(address)
        
        if not is_valid_mint_address(address_str):
            logger.debug(f"Filtered out invalid mint address: {address_str}")
            return False
                
        if address_str in processed_addresses:
            return False
                
        processed_addresses.add(address_str)
        
        # Check for pump tokens (case insensitive)
        if address_str.lower().endswith('pump'):
            unique_pump_tokens.add(address_str)
            logger.info(f"Found pump token: {address_str} in {source} (tx {tx_index})")
            return True
                
        # Add to mint addresses set
        mint_addresses.add(address_str)
        logger.info(f"Found mint in {source}: {address_str}")
        return True
            
    except Exception as e:
        logger.error(f"Error processing mint address {address}: {str(e)}")
        return False

def is_valid_mint_address(address: str) -> bool:
    """
    Validate if an address is likely to be a mint address
    
    Args:
        address: The address to validate
        
    Returns:
        bool: True if address appears to be a valid mint address
    """
    if not address:
        return False
            
    # Filter out known system addresses
    if address in ['So11111111111111111111111111111111111111112',  # Wrapped SOL
                   'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
                   'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',  # Associated Token Program
                   'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',  # Token Program 2022
                   '11111111111111111111111111111111',  # System Program
                   'ComputeBudget111111111111111111111111111111',  # Compute Budget
                   'Vote111111111111111111111111111111111111111',  # Vote Program
                   'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr',  # Memo Program
                   ]:
        return False
            
    # Filter out known program IDs
    if address in ['DCA265Vj8a9CEuX1eb1LWRnDT7uK6q1xMipnNyatn23M',  # DCA Program
                   'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4',  # Jupiter Program
                   'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc',  # Whirlpool Program
                   'SoLFiHG9TfgtdUXUjWAxi3LtvYuFyDLVhBWxdMZxyCe',  # SolFi Program
                   '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',  # Raydium Program
                   'AzHrwdCsEZotAjr7sjenHrHpf1ZKYoGBP6N7HVhEsyen',  # Azuro Program
                   'M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K',  # Magic Eden Program
                   'HYPERfwdTjyJ2SCaKHmpF2MtrXqWxrsotYDsTrshHWq8',  # Hyperspace Program
                   'mmm3XBJg5gk8XJxEKBvdgptZz6SgK4tXvn36sodowMc',  # Metamask Program
                   'So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo',  # Solend Program
                   'DjVE6JNiYqPL2QXyCUUh8rNjHrbz9hXHNYt99MQ59qw1',  # Orca Program
                   ]:
        return False
            
    # Basic format validation
    try:
        # Check length (should be 32-44 characters)
        if len(address) < 32 or len(address) > 44:
            return False
                
        # Should not contain special characters except base58 alphabet
        if not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address):
            return False
                
        # Additional heuristics for pump tokens
        if 'pump' in address.lower() and not address.endswith('pump'):
            return False
                
        return True
    except:
        return False

# Create FastAPI router
router = APIRouter(
    tags=["Soleco"]  # Use consistent capitalization
)

@router.get(
    "/extract",
    summary="Extract Mint Addresses",
    description="""
    Extract mint addresses from recent Solana blocks.
    
    This endpoint scans recent blocks on the Solana blockchain and extracts:
    - New mint addresses
    - Transaction statistics
    - Pump token detection
    - Processing metrics
    
    The response includes both block-specific data and overall summary statistics.
    """,
    response_description="Dictionary containing mint addresses and detailed statistics for each scanned block"
)
async def get_mints(
    limit: int = Query(
        default=1,
        description="Number of recent blocks to scan (1-10)",
        ge=1,
        le=10
    )
) -> Dict[str, Any]:
    """
    Extract mint addresses from recent Solana blocks.
    
    Args:
        limit: Number of recent blocks to scan (1-10)
        
    Returns:
        Dictionary containing:
        - blocks: List of dictionaries with block-specific data
            - mint_addresses: List of new mint addresses found
            - pump_token_addresses: List of potential pump tokens
            - transaction_stats: Breakdown of transaction types
            - processing_time: Time taken to process the block
        - summary: Overall statistics across all blocks
            - total_blocks_scanned: Number of blocks processed
            - total_transactions: Total number of transactions
            - total_mint_addresses: Total number of mint addresses found
            - unique_mint_addresses: Number of unique mint addresses
    
    Raises:
        HTTPException: If there's an error retrieving or processing the blocks
    """
    try:
        # Initialize handlers
        connection_pool = await get_connection_pool()
        query_handler = SolanaQueryHandler(connection_pool)
        mint_extractor = MintExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing blocks from {limit} recent blocks")
        blocks_data = await query_handler.process_blocks(limit)
        
        if not blocks_data:
            logger.error("No blocks_data returned from process_blocks")
            return {"success": False, "error": "Failed to get blocks data"}
            
        if not isinstance(blocks_data, dict) or not blocks_data.get("success", False):
            error = blocks_data.get("error", "Unknown error") if isinstance(blocks_data, dict) else "Invalid blocks data format"
            logger.error(f"Error in blocks_data: {error}")
            return {"success": False, "error": error}
            
        blocks_list = blocks_data.get("blocks", [])
        if not blocks_list:
            logger.warning("No blocks found in blocks_data")
            return {
                "success": True,
                "blocks": [],
                "summary": {
                    "total_blocks_scanned": 0,
                    "total_transactions": 0,
                    "total_mint_addresses": 0,
                    "unique_mint_addresses": 0
                }
            }
            
        # Process each block
        logger.info(f"Processing {len(blocks_list)} blocks")
        all_mint_addresses = set()
        all_pump_tokens = set()
        total_transactions = 0
        block_results = []
        
        for block in blocks_list:
            try:
                if not block:
                    logger.warning("Empty block data")
                    continue
                    
                logger.debug(f"Processing block with {len(block.get('transactions', []))} transactions")
                mint_extractor.process_block(block)
                
                # Get block-specific results
                results = mint_extractor.get_results()
                block_mint_addresses = results["new_mints"]
                
                # Add to overall results
                all_mint_addresses.update(block_mint_addresses)
                
                # Create block result
                block_slot = block.get('parentSlot', 'unknown')
                block_result = {
                    "slot": block_slot,
                    "mint_addresses": block_mint_addresses,
                    "pump_token_addresses": [],  # This would need additional logic to identify pump tokens
                    "transaction_stats": {
                        "total": len(block.get('transactions', [])),
                        "with_mints": len(block_mint_addresses)
                    },
                    "processing_time": 0  # This would need timing logic
                }
                
                block_results.append(block_result)
                total_transactions += len(block.get('transactions', []))
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Create summary
        summary = {
            "total_blocks_scanned": len(blocks_list),
            "total_transactions": total_transactions,
            "total_mint_addresses": len(all_mint_addresses),
            "unique_mint_addresses": len(all_mint_addresses)
        }
        
        return {
            "success": True,
            "blocks": block_results,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error in get_mints: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Example usage
if __name__ == "__main__":
    # Set logging to DEBUG for more detailed output
    logging.getLogger().setLevel(logging.DEBUG)
    
    async def main():
        recent_block_mints = await get_mints_from_recent_blocks()  # Default to 1 block
        logger.info("Mint Addresses per Block:")
        for block in recent_block_mints["blocks"]:
            logger.info(f"Block {block['slot']}: {len(block['mint_addresses'])} mints")
            logger.debug(f"Mints: {block['mint_addresses']}")
    
    asyncio.run(main())
