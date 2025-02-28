"""
Router for Solana block analytics endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, Query, Path, HTTPException
from app.utils.solana_query import SolanaQueryHandler
from app.utils.handlers.block_extractor import BlockExtractor
from app.utils.logging_config import setup_logging
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/block",
    tags=["soleco"]
)

@router.get("/recent")
async def get_recent_blocks(
    limit: int = Query(
        default=10,
        description="Number of recent blocks to analyze",
        ge=1,
        le=100
    )
) -> Dict[str, Any]:
    """
    Get data from recent blocks.
    
    Args:
        limit: Number of recent blocks to analyze (default: 10)
        
    Returns:
        Dict containing block data and analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        block_extractor = BlockExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing {limit} recent blocks")
        blocks_data = await query_handler.process_blocks(limit)
        
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
                "blocks": [],
                "stats": {"total_transactions": 0, "avg_transactions": 0},
                "blocks_processed": 0
            }
            
        # Process each block
        logger.info(f"Processing {len(blocks_list)} blocks")
        for block in blocks_list:
            try:
                if not block:
                    logger.warning("Empty block data")
                    continue
                    
                logger.debug(f"Processing block with {len(block.get('transactions', []))} transactions")
                block_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = block_extractor.get_results()
            logger.info(f"Processed {results['blocks_processed']} blocks")
            
            return {
                "success": True,
                "blocks": results["blocks"],
                "stats": results["stats"],
                "blocks_processed": results["blocks_processed"]
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_recent_blocks: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/block/{slot}")
async def get_block_details(
    slot: int = Path(..., description="Block slot number to analyze")
) -> Dict[str, Any]:
    """
    Get detailed information about a specific block.
    
    Args:
        slot: Block slot number to analyze
        
    Returns:
        Dict containing block details and analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        block_extractor = BlockExtractor()
        
        # Initialize and get block
        await query_handler.initialize()
        logger.info(f"Analyzing block at slot {slot}")
        block = await query_handler.get_block(slot)
        
        if not block:
            logger.error(f"No block found at slot {slot}")
            return {"success": False, "error": f"Block not found at slot {slot}"}
            
        # Process block
        try:
            block_extractor.process_block(block)
            results = block_extractor.get_results()
            
            return {
                "success": True,
                "block": results["blocks"][0] if results["blocks"] else None,
                "stats": results["stats"]
            }
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_block_details: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/range")
async def get_block_range(
    start_slot: int = Query(..., description="Starting slot number"),
    end_slot: int = Query(..., description="Ending slot number"),
    include_transactions: bool = Query(False, description="Include transaction details")
) -> Dict[str, Any]:
    """
    Get block data for a range of slots.
    
    Args:
        start_slot: Starting slot number
        end_slot: Ending slot number
        include_transactions: Whether to include transaction details
        
    Returns:
        Dict containing block range data and analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        block_extractor = BlockExtractor()
        
        # Initialize and get blocks
        await query_handler.initialize()
        logger.info(f"Analyzing blocks from slot {start_slot} to {end_slot}")
        blocks_data = await query_handler.process_blocks(
            start_slot=start_slot,
            end_slot=end_slot
        )
        
        if not blocks_data:
            logger.error("No blocks_data returned from process_blocks")
            return {"success": False, "error": "Failed to get blocks data"}
            
        if not blocks_data.get("success"):
            error = blocks_data.get("error", "Unknown error")
            logger.error(f"Error in blocks_data: {error}")
            return {"success": False, "error": error}
            
        blocks_list = blocks_data.get("blocks", [])
        if not blocks_list:
            logger.warning("No blocks found in range")
            return {
                "success": True,
                "blocks": [],
                "stats": {"total_transactions": 0, "avg_transactions": 0},
                "blocks_processed": 0
            }
            
        # Process blocks
        logger.info(f"Processing {len(blocks_list)} blocks")
        for block in blocks_list:
            try:
                if not block:
                    logger.warning("Empty block data")
                    continue
                    
                logger.debug(f"Processing block with {len(block.get('transactions', []))} transactions")
                block_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = block_extractor.get_results()
            
            # Remove transaction details if not requested
            if not include_transactions:
                for block in results["blocks"]:
                    if "transactions" in block:
                        del block["transactions"]
                        
            return {
                "success": True,
                "blocks": results["blocks"],
                "stats": results["stats"],
                "blocks_processed": results["blocks_processed"]
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_block_range: {str(e)}")
        return {"success": False, "error": str(e)}
