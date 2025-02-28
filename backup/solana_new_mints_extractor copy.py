"""
Solana New Mints Extractor - Focused on detecting and analyzing newly created mint addresses
"""

from typing import Dict, List, Optional, Any, Union, Set
import logging
import time
import asyncio
from fastapi import APIRouter, Query, HTTPException
from solders.pubkey import Pubkey

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
            if not result:
                logger.debug("Empty result")
                return {"success": True, "mint_addresses": [], "statistics": self._get_empty_stats()}
                
            # Get transactions from block data
            transactions = []
            if isinstance(result, dict):
                transactions = result.get("transactions", [])
            elif isinstance(result, list):
                transactions = result
                
            logger.info(f"Processing {len(transactions)} transactions")
            
            if not transactions:
                return {"success": True, "mint_addresses": [], "statistics": self._get_empty_stats()}
                
            mint_addresses = await self._process_transactions(transactions)
            
            # Collect statistics
            stats = {
                "total_transactions": len(transactions),
                "total_instructions": sum(len(tx.get("transaction", {}).get("message", {}).get("instructions", [])) 
                                       for tx in transactions if isinstance(tx, dict)),
                "token_program_txs": sum(1 for tx in transactions 
                                       if isinstance(tx, dict) and self._has_token_program(tx)),
                "new_mints": len(mint_addresses),
                "timestamp": int(time.time())
            }
            
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
            message = tx.get("transaction", {}).get("message", {})
            instructions = message.get("instructions", [])
            
            for ix in instructions:
                program_id = ix.get("programId")
                if program_id in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                    return True
            return False
        except Exception:
            return False
        
    async def _process_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process transactions to find new mint addresses"""
        mint_addresses = []
        
        for tx_idx, tx in enumerate(transactions):
            if not tx or not isinstance(tx, dict):
                continue
                
            # Handle both raw and parsed transaction formats
            if "transaction" in tx:
                message = tx["transaction"].get("message", {})
                meta = tx.get("meta", {})
            else:
                message = tx.get("message", {})
                meta = tx.get("meta", {})
            
            if not message or not meta:
                continue
                
            logger.debug(f"Processing transaction {tx_idx + 1}")
            mint_info = await self._extract_mint_info(message, meta)
            if mint_info:
                logger.info(f"Found new mint address: {mint_info['address']}")
                mint_addresses.append(mint_info)
                
        return mint_addresses
        
    async def _extract_mint_info(self, message: Dict[str, Any], meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract mint information from a transaction"""
        try:
            # Get account keys
            account_keys = message.get("accountKeys", [])
            if not account_keys:
                return None
                
            # Get instructions
            instructions = message.get("instructions", [])
            if not instructions:
                return None
                
            # Look for mint creation instructions
            for idx, instruction in enumerate(instructions):
                program_id = instruction.get("programId")
                if not program_id:
                    continue
                    
                # Check if it's a token program instruction
                if program_id in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                    # Extract mint address
                    accounts = instruction.get("accounts", [])
                    if len(accounts) >= 2:  # Mint account is typically the first or second account
                        mint_address = accounts[1] if len(accounts) > 1 else accounts[0]
                        if mint_address not in KNOWN_TOKEN_MINTS:
                            return {
                                "address": mint_address,
                                "program": program_id,
                                "timestamp": int(time.time())
                            }
                            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting mint info: {str(e)}")
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
                result = await query_handler.process_block(slot)
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
