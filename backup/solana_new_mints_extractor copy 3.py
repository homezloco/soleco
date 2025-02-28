"""
Solana New Mints Extractor - Focused on detecting and analyzing newly created mint addresses
"""

from typing import Dict, List, Optional, Any, Union, Set
import logging
import time
import asyncio
from fastapi import APIRouter, Query, HTTPException
from solders.pubkey import Pubkey
import json

from ..utils.solana_query import SolanaQueryHandler
from ..utils.solana_response import SolanaResponseManager
from ..utils.solana_helpers import DEFAULT_COMMITMENT
from ..utils.handlers.base_handler import BaseHandler
from ..utils.solana_types import EndpointConfig
from ..utils.solana_errors import RPCError, RetryableError
from ..utils.solana_rpc import AdaptiveRateConfig, SolanaRateLimiter

# Configure logging
logger = logging.getLogger(__name__)

# Constants
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"

# Token program IDs
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

# Known token mints to exclude
KNOWN_TOKEN_MINTS = {
    "So11111111111111111111111111111111111111112",  # Wrapped SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "7i5KKsX2weiTkry7jA4ZwSJ4zRWqW2PPkiupCAMMQCLQ",  # PYTH
}

# Rate limiting configuration
rate_config = AdaptiveRateConfig(
    initial_rate=5,      # Start conservatively
    min_rate=2,         # Lower bound for rate
    max_rate=10,        # Upper bound for rate
    increase_threshold=0.6,  # When to increase rate
    decrease_threshold=0.4,  # When to decrease rate
    adjustment_factor=1.1    # How much to adjust by
)

# Endpoint configuration
endpoint_config = EndpointConfig(
    url="https://api.mainnet-beta.solana.com",
    requests_per_second=5.0,
    burst_limit=10,
    max_retries=3,
    retry_delay=2.0
)

# Create FastAPI router
router = APIRouter(
    prefix="/solana/new-mints",
    tags=["solana", "mints"]
)

class NewMintsResponseHandler(BaseHandler):
    """Handler for new mints responses"""
    
    def __init__(self, response_manager: SolanaResponseManager):
        """Initialize with response manager"""
        super().__init__()  # Call BaseHandler's init without args
        self.response_manager = response_manager
    
    async def process_result(self, result: Any) -> Dict[str, Any]:
        """Process new mints data"""
        try:
            # Initialize statistics
            stats = self._get_empty_stats()
            mint_addresses = []
            
            # Get transactions from block
            transactions = result.get("transactions", [])
            if not transactions:
                logger.debug("No transactions found in block")
                return {"success": True, "mint_addresses": [], "statistics": stats}
                
            # Update transaction count
            stats["total_transactions"] = len(transactions)
            
            # Process transactions
            for tx in transactions:
                try:
                    # Get transaction data
                    if isinstance(tx, str):
                        logger.debug("Skipping base58 encoded transaction")
                        continue
                        
                    # Get message and meta
                    message = tx.get("transaction", {}).get("message", {})
                    meta = tx.get("meta", {})
                    
                    if not message or not meta:
                        logger.debug("Missing message or meta data")
                        continue
                        
                    # Get account keys and instructions
                    account_keys = message.get("accountKeys", [])
                    instructions = message.get("instructions", [])
                    inner_instructions = meta.get("innerInstructions", [])
                    
                    if not account_keys:
                        logger.debug("No account keys found")
                        continue
                        
                    # Update instruction count
                    stats["total_instructions"] += len(instructions)
                    for inner_ix_group in inner_instructions:
                        stats["total_instructions"] += len(inner_ix_group.get("instructions", []))
                        
                    # Check for token program
                    if not self._has_token_program(tx):
                        continue
                        
                    stats["token_program_txs"] += 1
                    
                    # Check main instructions
                    for ix in instructions:
                        program_id = ix.get("programId")
                        if program_id not in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                            continue
                            
                        if self._is_initialize_mint(ix):
                            mint_address = self._extract_mint_address(ix, account_keys)
                            if mint_address:
                                mint_addresses.append({
                                    "address": mint_address,
                                    "program": "Token2022" if program_id == TOKEN_2022_PROGRAM_ID else "Token",
                                    "slot": tx.get("slot"),
                                    "timestamp": int(time.time()),
                                    "location": "main"
                                })
                                stats["new_mints"] += 1
                                
                    # Check inner instructions
                    for inner_ix_group in inner_instructions:
                        for inner_ix in inner_ix_group.get("instructions", []):
                            program_id = inner_ix.get("programId")
                            if program_id not in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                                continue
                                
                            if self._is_initialize_mint(inner_ix):
                                mint_address = self._extract_mint_address(inner_ix, account_keys)
                                if mint_address:
                                    mint_addresses.append({
                                        "address": mint_address,
                                        "program": "Token2022" if program_id == TOKEN_2022_PROGRAM_ID else "Token",
                                        "slot": tx.get("slot"),
                                        "timestamp": int(time.time()),
                                        "location": "inner"
                                    })
                                    stats["new_mints"] += 1
                                    
                except Exception as e:
                    logger.error(f"Error processing transaction: {str(e)}")
                    continue
                    
            # Log detailed statistics
            logger.info("Block Processing Statistics:")
            logger.info(f"  Total Transactions: {stats['total_transactions']}")
            logger.info(f"  Total Instructions: {stats['total_instructions']}")
            logger.info(f"  Token Program Txs: {stats['token_program_txs']}")
            logger.info(f"  New Mints Found: {stats['new_mints']}")
            
            return {
                "success": True,
                "mint_addresses": mint_addresses,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Error processing result: {str(e)}")
            return {"success": False, "error": str(e), "statistics": self._get_empty_stats()}
            
    def _get_empty_stats(self) -> Dict[str, int]:
        """Get empty statistics dictionary"""
        return {
            "total_transactions": 0,
            "total_instructions": 0,
            "token_program_txs": 0,
            "new_mints": 0,
            "timestamp": int(time.time())
        }
        
    def _has_token_program(self, tx: Dict[str, Any]) -> bool:
        """Check if transaction involves token program"""
        try:
            # Get parsed transaction data
            parsed_tx = tx.get("transaction", {})
            if isinstance(parsed_tx, str):
                # Handle base58 encoded transaction
                logger.debug("Found base58 encoded transaction")
                return False
                
            message = parsed_tx.get("message", {})
            if not message:
                logger.debug("No message found in transaction")
                return False
                
            # Check account keys
            account_keys = message.get("accountKeys", [])
            if not account_keys:
                logger.debug("No account keys found")
                return False
                
            # Check for token program in account keys
            for key in account_keys:
                if isinstance(key, dict):
                    pubkey = key.get("pubkey")
                else:
                    pubkey = key
                if str(pubkey) in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                    logger.debug(f"Found token program in account keys: {pubkey}")
                    return True
            
            # Check program IDs in instructions
            instructions = message.get("instructions", [])
            for ix in instructions:
                program_id = None
                if isinstance(ix, dict):
                    program_id = ix.get("programId")
                elif hasattr(ix, "program_id"):
                    program_id = str(ix.program_id)
                
                if str(program_id) in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                    logger.debug(f"Found token program in instructions: {program_id}")
                    return True
                    
            # Check inner instructions if available
            meta = tx.get("meta", {})
            inner_instructions = meta.get("innerInstructions", [])
            for inner_ix_group in inner_instructions:
                for inner_ix in inner_ix_group.get("instructions", []):
                    program_id = None
                    if isinstance(inner_ix, dict):
                        program_id = inner_ix.get("programId")
                    elif hasattr(inner_ix, "program_id"):
                        program_id = str(inner_ix.program_id)
                    
                    if str(program_id) in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                        logger.debug(f"Found token program in inner instructions: {program_id}")
                        return True
            
            logger.debug("No token program found in transaction")
            return False
            
        except Exception as e:
            logger.debug(f"Error checking token program: {str(e)}")
            return False
            
    def _is_initialize_mint(self, instruction: Dict[str, Any]) -> bool:
        """Check if instruction is InitializeMint"""
        try:
            # Log instruction for debugging
            logger.debug(f"Checking instruction: {json.dumps(instruction, indent=2)}")
            
            # Check program ID first
            program_id = instruction.get("programId")
            if not program_id:
                logger.debug("No program ID found")
                return False
                
            program_id = str(program_id)
            if program_id not in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                logger.debug(f"Not a token program instruction: {program_id}")
                return False
                
            # Check instruction data
            data = instruction.get("data")
            if not data:
                logger.debug("No instruction data found")
                return False
                
            # For Token Program:
            # InitializeMint instruction has discriminator 0
            # Format: [0, decimals, mint_authority, freeze_authority_option, freeze_authority]
            if program_id == TOKEN_PROGRAM_ID:
                # Check for initialize_mint instruction
                if data.startswith("0"):
                    logger.debug("Found InitializeMint instruction (Token)")
                    return True
                    
            # For Token-2022 Program:
            # initialize_mint2 has discriminator 8
            # Format: [8, decimals, mint_authority, freeze_authority_option, freeze_authority]
            elif program_id == TOKEN_2022_PROGRAM_ID:
                # Check for initialize_mint2 instruction
                if data.startswith("8"):
                    logger.debug("Found InitializeMint2 instruction (Token-2022)")
                    return True
                    
            # Check parsed instruction data if available
            parsed = instruction.get("parsed", {})
            if parsed:
                if isinstance(parsed, dict):
                    program = parsed.get("program")
                    type_ = parsed.get("type")
                    if (program == "spl-token" and type_ == "initializeMint") or \
                       (program == "spl-token-2022" and type_ == "initializeMint2"):
                        logger.debug(f"Found initialize mint in parsed data: {program} - {type_}")
                        return True
            
            logger.debug("Not an InitializeMint instruction")
            return False
            
        except Exception as e:
            logger.debug(f"Error checking initialize mint: {str(e)}")
            return False
            
    def _is_valid_mint_address(self, address: str) -> bool:
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
        
        # Filter out known program IDs
        PROGRAM_IDS = {
            'DCA265Vj8a9CEuX1eb1LWRnDT7uK6q1xMipnNyatn23M',  # DCA Program
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
        }
        
        if address in SYSTEM_ADDRESSES or address in PROGRAM_IDS:
            logger.debug(f"Address {address} is a known system/program address")
            return False
            
        # Basic format validation
        try:
            # Check length (should be 32-44 characters)
            if len(address) < 32 or len(address) > 44:
                logger.debug(f"Invalid address length: {len(address)}")
                return False
                
            # Should not contain special characters except base58 alphabet
            if not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address):
                logger.debug(f"Invalid address characters: {address}")
                return False
                
            return True
            
        except Exception as e:
            logger.debug(f"Error validating address: {str(e)}")
            return False
            
    def _extract_mint_address(self, instruction: Dict[str, Any], account_keys: List[str]) -> Optional[str]:
        """Extract mint address from instruction"""
        try:
            # Log inputs
            logger.debug(f"Extracting mint address from instruction: {json.dumps(instruction, indent=2)}")
            logger.debug(f"Account keys: {json.dumps(account_keys, indent=2)}")
            
            # Get program ID and accounts
            program_id = instruction.get("programId")
            accounts = instruction.get("accounts", [])
            
            if not program_id or not accounts:
                logger.debug("Missing program ID or accounts")
                return None
                
            # For Token/Token-2022 InitializeMint:
            # accounts[0] = mint account being initialized
            # accounts[1] = rent sysvar
            if program_id in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                if not accounts:
                    logger.debug("No accounts in instruction")
                    return None
                    
                # Get mint account index
                mint_idx = accounts[0]
                if isinstance(mint_idx, (str, dict)):
                    mint_address = mint_idx.get("pubkey") if isinstance(mint_idx, dict) else mint_idx
                elif isinstance(mint_idx, int) and mint_idx < len(account_keys):
                    mint_address = account_keys[mint_idx]
                else:
                    logger.debug(f"Invalid mint index type: {type(mint_idx)}")
                    return None
                    
                # Convert to string if needed
                mint_address = str(mint_address)
                logger.debug(f"Found potential mint address: {mint_address}")
                
                # Validate mint address
                if not self._is_valid_mint_address(mint_address):
                    return None
                    
                if mint_address in KNOWN_TOKEN_MINTS:
                    logger.debug(f"Mint address {mint_address} is in known token mints, skipping")
                    return None
                    
                logger.info(f"Found valid mint address: {mint_address}")
                return mint_address
                
            # Check instruction data for potential mint references
            data = instruction.get("data")
            if data and isinstance(data, (str, bytes)):
                try:
                    data_str = str(data)
                    # Look for potential Base58 encoded mint addresses in instruction data
                    if len(data_str) >= 32 and len(data_str) <= 44:
                        if self._is_valid_mint_address(data_str) and data_str not in KNOWN_TOKEN_MINTS:
                            logger.info(f"Found mint in instruction data: {data_str}")
                            return data_str
                except Exception as e:
                    logger.debug(f"Error checking instruction data: {str(e)}")
                    pass
                    
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting mint address: {str(e)}")
            return None

class NewMintAnalyzer:
    """Analyzes blocks for new mint addresses"""
    
    def __init__(self):
        self.mint_handler = MintHandler()
        
        # Initialize response handler with config
        response_manager = SolanaResponseManager(endpoint_config)
        self.response_handler = NewMintsResponseHandler(response_manager=response_manager)
        
    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block to find new mint addresses"""
        try:
            if not block_data or not isinstance(block_data, dict):
                return {"success": False, "error": "Invalid block data"}
                
            # Use the mint handler to process the block
            result = self.mint_handler.handle_block(block_data)
            
            # Format the response
            return {
                "success": True,
                "block_number": block_data.get("parentSlot", 0) + 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mint_addresses": list(self.mint_handler.mint_addresses),
                "errors": self.mint_handler.errors
            }
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            return {"success": False, "error": str(e)}

async def get_query_handler() -> SolanaQueryHandler:
    """Get or create query handler with proper response handler"""
    try:
        # Create response manager with config
        response_manager = SolanaResponseManager(endpoint_config)
        
        # Create new mints response handler with manager
        response_handler = NewMintsResponseHandler(response_manager=response_manager)
        
        # Initialize query handler with our response handler
        query_handler = SolanaQueryHandler(response_handler=response_handler)
        await query_handler.initialize()
        
        return query_handler
        
    except Exception as e:
        logger.error(f"Failed to initialize query handler: {str(e)}")
        raise

async def extract_new_mints(
    start_block: Optional[int] = None,
    end_block: Optional[int] = None,
    batch_size: int = 10
) -> Dict[str, Any]:
    """Extract new mint addresses from specified blocks"""
    try:
        # Get query handler
        query_handler = await get_query_handler()
        if not query_handler:
            return {"error": "Failed to initialize query handler"}
            
        # Get current block
        current_block = await get_current_block()
        if not current_block:
            return {"error": "Failed to get current block"}
            
        # Initialize analyzer
        analyzer = NewMintAnalyzer()
        
        # Process blocks with mint response handler
        results = await query_handler.process_blocks(
            num_blocks=end_block - start_block + 1,
            start_slot=start_block,    # Lower slot (older)
            end_slot=end_block,        # Higher slot (newer)
            handlers=[analyzer.response_handler],  # Use analyzer's response handler
            batch_size=batch_size
        )
        
        # Extract new mints from results
        new_mints = []
        if results.get("success", False):
            for handler_name, handler_result in results.items():
                if handler_name not in ("success", "processed_blocks", "total_blocks", "start_slot", "end_slot", "errors"):
                    if isinstance(handler_result, dict) and "mint_addresses" in handler_result:
                        new_mints.extend(handler_result["mint_addresses"])
        
        return {
            "success": True,
            "start_block": results.get("start_slot"),
            "end_block": results.get("end_slot"),
            "blocks_processed": results.get("processed_blocks", 0),
            "blocks_failed": len(results.get("errors", [])),
            "new_mints": new_mints,
            "stats": {
                "total_blocks_analyzed": results.get("processed_blocks", 0),
                "total_new_mints": len(new_mints),
                "success_rate": results.get("processed_blocks", 0) / (end_block - start_block + 1) if end_block - start_block + 1 > 0 else 0
            },
            "errors": results.get("errors", [])
        }
        
    except Exception as e:
        logger.error(f"Error extracting new mints: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/recent")
async def get_recent_new_mints(
    blocks: int = Query(
        default=5,
        description="Number of recent blocks to analyze",
        ge=1,
        le=20
    )
) -> Dict[str, Any]:
    """
    Get newly created mint addresses from recent blocks
    
    Args:
        blocks: Number of recent blocks to analyze (default: 5)
        
    Returns:
        Dict containing new mint addresses and analysis
    """
    try:
        # Get query handler
        query_handler = await get_query_handler()
        
        # Get latest block height
        client = await query_handler.connection_pool.get_client()
        if not client:
            raise HTTPException(status_code=500, detail="Failed to get Solana client")
            
        latest_block = await client.get_block_height()
        if latest_block is None:
            raise HTTPException(status_code=500, detail="Failed to get latest block")
            
        # Calculate block range
        start_block = latest_block
        end_block = max(0, start_block - blocks + 1)
        
        logger.info(f"Analyzing blocks from {start_block} (newer) to {end_block} (older)")
        
        # Process blocks
        results = []
        total_stats = {
            "total_transactions": 0,
            "total_instructions": 0,
            "token_program_txs": 0,
            "new_mints": 0,
            "blocks_processed": 0,
            "start_time": int(time.time())
        }
        
        for slot in range(start_block, end_block - 1, -1):
            try:
                # Get block data
                block_data = await query_handler.get_block(slot)
                if not block_data:
                    raise HTTPException(status_code=500, detail=f"Failed to get block {slot}")
                    
                # Process block
                result = await query_handler.process_block(block_data)
                if result and result.get("success"):
                    results.append(result)
                    
                    # Update statistics
                    stats = result.get("statistics", {})
                    total_stats["total_transactions"] += stats.get("total_transactions", 0)
                    total_stats["total_instructions"] += stats.get("total_instructions", 0)
                    total_stats["token_program_txs"] += stats.get("token_program_txs", 0)
                    total_stats["new_mints"] += stats.get("new_mints", 0)
                    total_stats["blocks_processed"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing block {slot}: {str(e)}")
                continue
                
        # Calculate processing duration
        total_stats["duration_seconds"] = int(time.time()) - total_stats["start_time"]
        
        # Log summary statistics
        logger.info("\nProcessing Summary:")
        logger.info(f"  Blocks Processed: {total_stats['blocks_processed']}/{blocks}")
        logger.info(f"  Total Transactions: {total_stats['total_transactions']}")
        logger.info(f"  Total Instructions: {total_stats['total_instructions']}")
        logger.info(f"  Token Program Txs: {total_stats['token_program_txs']}")
        logger.info(f"  New Mints Found: {total_stats['new_mints']}")
        logger.info(f"  Processing Time: {total_stats['duration_seconds']}s")
        
        return {
            "success": True,
            "results": results,
            "statistics": total_stats,
            "block_range": {
                "start": start_block,
                "end": end_block,
                "requested": blocks
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_recent_new_mints: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitor")
async def monitor_new_mints(
    interval: int = Query(
        default=60,
        description="Monitoring interval in seconds",
        ge=10,
        le=300
    ),
    duration: int = Query(
        default=3600,
        description="Total monitoring duration in seconds",
        ge=60,
        le=86400
    )
) -> Dict[str, Any]:
    """
    Monitor for new mint addresses over a specified duration
    
    Args:
        interval: Seconds between each check (10-300)
        duration: Total monitoring duration in seconds (60-86400)
        
    Returns:
        Dict containing monitored new mint addresses and statistics
    """
    query_handler = await get_query_handler()
    if not query_handler:
        raise HTTPException(
            status_code=503,
            detail="Failed to initialize Solana connection"
        )
        
    try:
        analyzer = NewMintAnalyzer()
        start_time = time.time()
        end_time = start_time + duration
        
        monitored_mints = []
        last_block = None
        
        while time.time() < end_time:
            try:
                # Get latest block
                client = await query_handler.connection_pool.get_client()
                current_block = await client.get_block_height()
                
                if current_block and (last_block is None or current_block > last_block):
                    # Process new blocks
                    start_block = last_block + 1 if last_block else current_block
                    
                    results = await query_handler.process_blocks(
                        num_blocks=current_block - start_block + 1,
                        start_slot=start_block,    # Lower slot (older)
                        end_slot=current_block,    # Higher slot (newer)
                        handlers=[analyzer.response_handler],  # Use analyzer's response handler
                        batch_size=5
                    )
                    
                    # Process results
                    new_mints = []
                    if results.get("success", False):
                        for handler_name, handler_result in results.items():
                            if handler_name not in ("success", "processed_blocks", "total_blocks", "start_slot", "end_slot", "errors"):
                                if isinstance(handler_result, dict) and "mint_addresses" in handler_result:
                                    new_mints.extend(handler_result["mint_addresses"])
                    
                    monitored_mints.extend(new_mints)
                    
                    last_block = current_block
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                
            # Wait for next interval
            remaining_time = end_time - time.time()
            if remaining_time > 0:
                await asyncio.sleep(min(interval, remaining_time))
            else:
                break
                
        # Sort monitored mints by block time (newest first)
        monitored_mints.sort(key=lambda x: x.get("block_time", 0), reverse=True)
        
        return {
            "success": True,
            "monitoring_duration": duration,
            "actual_duration": int(time.time() - start_time),
            "new_mints": monitored_mints,
            "stats": {
                "total_blocks_analyzed": 0,
                "total_new_mints": len(monitored_mints),
                "total_pump_tokens": 0,
                "mints_per_minute": (len(monitored_mints) * 60) / duration
            },
            "errors": []
        }
        
    except Exception as e:
        logger.error(f"Error in mint monitoring: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Internal server error in mint monitoring: {str(e)}"
        )
