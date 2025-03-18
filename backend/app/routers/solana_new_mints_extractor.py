"""
Solana New Mints Extractor - Focused on detecting and analyzing newly created mint addresses
"""

from typing import Dict, Any
import logging
import asyncio
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from ..utils.solana_query import SolanaQueryHandler
from ..utils.handlers.mint_extractor import MintExtractor
from ..utils.solana_rpc import get_connection_pool
from ..utils.solana_connection_pool import mint_analytics_cache

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(
    tags=["Soleco"]
)

# Global variable to store the last result and processing status
_processing_lock = asyncio.Lock()
_is_processing = False
_last_result = {}
_last_blocks_processed = 0

@router.get("/recent")
async def get_recent_new_mints(
    blocks: int = Query(
        default=1,
        description="Number of recent blocks to analyze",
        ge=1,
        le=10
    ),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Get newly created mint addresses from recent blocks.
    
    Args:
        blocks: Number of recent blocks to analyze (default: 1)
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict containing new mint addresses and analysis
    """
    global _is_processing, _last_result, _last_blocks_processed
    
    try:
        # Check cache first
        cache_key = f"recent_mints_{blocks}"
        cached_result = mint_analytics_cache.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached mint analytics for {blocks} blocks")
            return cached_result
        
        # If blocks requested is less than or equal to what we've already processed,
        # and we have a result, return it immediately
        if blocks <= _last_blocks_processed and _last_result:
            logger.info(f"Returning last result for {blocks} blocks (already processed {_last_blocks_processed})")
            result = _last_result.copy()
            # Cache the result
            mint_analytics_cache.set(cache_key, result)
            return result
            
        # If already processing, return a status message with partial data if available
        async with _processing_lock:
            if _is_processing:
                if _last_result:
                    logger.info("Already processing, returning last available result")
                    result = _last_result.copy()
                    result["message"] = "Processing more blocks in background, partial results shown"
                    return result
                else:
                    logger.info("Processing in progress, no previous results available")
                    return {
                        "success": True,
                        "message": "Processing in progress, please try again in a few seconds",
                        "new_mints": [],
                        "pump_tokens": [],
                        "stats": {"total_mints": 0, "total_pump_tokens": 0, "mint_operations": 0},
                        "blocks_processed": 0
                    }
            
            # Set processing flag
            _is_processing = True
        
        # Function to process blocks in background
        async def process_blocks_background():
            global _is_processing, _last_result, _last_blocks_processed
            try:
                result = await _process_blocks(blocks)
                async with _processing_lock:
                    _last_result = result
                    _last_blocks_processed = blocks
                    _is_processing = False
                # Cache the result
                mint_analytics_cache.set(cache_key, result)
            except Exception as e:
                logger.error(f"Background processing error: {str(e)}")
                async with _processing_lock:
                    _is_processing = False
        
        # For small block counts (1-2), process synchronously
        if blocks <= 2:
            logger.info(f"Processing {blocks} blocks synchronously")
            result = await _process_blocks(blocks)
            
            async with _processing_lock:
                _last_result = result
                _last_blocks_processed = blocks
                _is_processing = False
                
            # Cache the result
            mint_analytics_cache.set(cache_key, result)
            return result
        else:
            # For larger block counts, start background processing and return immediately
            # with a status message or partial results
            if background_tasks:
                logger.info(f"Starting background processing for {blocks} blocks")
                background_tasks.add_task(process_blocks_background)
                
                if _last_result:
                    result = _last_result.copy()
                    result["message"] = "Processing more blocks in background, partial results shown"
                    return result
                else:
                    return {
                        "success": True,
                        "message": "Processing started in background, please try again in a few seconds",
                        "new_mints": [],
                        "pump_tokens": [],
                        "stats": {"total_mints": 0, "total_pump_tokens": 0, "mint_operations": 0},
                        "blocks_processed": 0
                    }
            else:
                # If background_tasks is not available, process synchronously
                logger.info(f"Processing {blocks} blocks synchronously (no background tasks available)")
                result = await _process_blocks(blocks)
                
                async with _processing_lock:
                    _last_result = result
                    _last_blocks_processed = blocks
                    _is_processing = False
                    
                # Cache the result
                mint_analytics_cache.set(cache_key, result)
                return result
            
    except Exception as e:
        logger.error(f"Error in get_recent_new_mints: {str(e)}")
        async with _processing_lock:
            _is_processing = False
        return {"success": False, "error": str(e)}

async def _process_blocks(blocks: int) -> Dict[str, Any]:
    """
    Process blocks and extract mint information.
    
    Args:
        blocks: Number of blocks to process
        
    Returns:
        Dict containing mint information
    """
    try:
        # Initialize handlers
        connection_pool = await get_connection_pool()
        query_handler = SolanaQueryHandler(connection_pool)
        mint_extractor = MintExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing blocks from {blocks} recent blocks")
        blocks_data = await query_handler.process_blocks(blocks)
        
        if not blocks_data:
            logger.error("No blocks_data returned from process_blocks")
            return {"success": False, "error": "Failed to get blocks data"}
            
        if not blocks_data.get("success"):
            error = blocks_data.get("error", "Unknown error")
            logger.error(f"Error in blocks_data: {error}")
            return {"success": False, "error": error}
            
        blocks_list = blocks_data.get("blocks", [])
        if not blocks_list:
            logger.warning("No blocks found in blocks_data")
            return {
                "success": True,
                "new_mints": [],
                "pump_tokens": [],
                "stats": {"total_mints": 0, "total_pump_tokens": 0, "mint_operations": 0},
                "blocks_processed": 0
            }
            
        # Process each block
        logger.info(f"Processing {len(blocks_list)} blocks")
        blocks_processed = len(blocks_list)
        for block in blocks_list:
            try:
                if not block:
                    logger.warning("Empty block data")
                    continue
                    
                logger.debug(f"Processing block with {len(block.get('transactions', []))} transactions")
                mint_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = mint_extractor.get_results()
            logger.debug(f"Results from mint_extractor.get_results(): {results}")
            
            # Get new mints and pump tokens
            new_mints = results["new_mints"]
            pump_tokens = results["pump_tokens"]
            logger.info(f"Found {len(new_mints)} new mints and {len(pump_tokens)} pump tokens")
            
            # Log pump tokens for debugging
            if pump_tokens:
                logger.debug(f"Pump tokens found: {pump_tokens}")
            else:
                logger.debug("No pump tokens found")
                
            result = {
                "success": True,
                "summary": {
                    "total_new_mints": len(new_mints),
                    "total_pump_tokens": len(pump_tokens),
                    "blocks_processed": blocks_processed
                },
                "new_mints": new_mints,
                "pump_tokens": list(pump_tokens),
                "stats": results["stats"]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in _process_blocks: {str(e)}")
        return {"success": False, "error": str(e)}
