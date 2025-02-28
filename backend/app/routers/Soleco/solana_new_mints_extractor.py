"""
Solana New Mints Extractor - Focused on detecting and analyzing newly created mint addresses
"""

from typing import Dict, Any
import logging
from fastapi import APIRouter, Query, HTTPException
from ..utils.solana_query import SolanaQueryHandler
from ..utils.handlers.mint_extractor import MintExtractor

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(
    tags=["soleco"]
)

@router.get("/recent")
async def get_recent_new_mints(
    blocks: int = Query(
        default=1,
        description="Number of recent blocks to analyze",
        ge=1,
        le=10
    )
) -> Dict[str, Any]:
    """
    Get newly created mint addresses from recent blocks.
    
    Args:
        blocks: Number of recent blocks to analyze (default: 1)
        
    Returns:
        Dict containing new mint addresses and analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
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
                "stats": {"total_mints": 0, "mint_operations": 0},
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
                mint_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = mint_extractor.get_results()
            logger.info(f"Found {len(results['new_mints'])} new mints")
            
            return {
                "success": True,
                "new_mints": results["new_mints"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_recent_new_mints: {str(e)}")
        return {"success": False, "error": str(e)}
