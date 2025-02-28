"""
NFT Analytics Module - Handles analysis of NFT activities on Solana
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException
from ..utils.solana_query import SolanaQueryHandler
from ..utils.handlers.nft_extractor import NFTExtractor
from ..utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)

# Create router
router = APIRouter(
    tags=["soleco"]
)

@router.get("/activity")
async def get_nft_activity(
    blocks: int = Query(
        default=10,
        description="Number of recent blocks to analyze",
        ge=1,
        le=100
    ),
    include_transactions: bool = Query(
        default=False,
        description="Include transaction details in response"
    )
) -> Dict[str, Any]:
    """
    Get NFT activity from recent blocks.
    
    Args:
        blocks: Number of recent blocks to analyze (default: 10)
        include_transactions: Whether to include transaction details
        
    Returns:
        Dict containing NFT activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        nft_extractor = NFTExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing NFT activity from {blocks} recent blocks")
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
                "nft_operations": [],
                "stats": {
                    "total_nft_ops": 0,
                    "operation_types": {
                        "mint": 0,
                        "transfer": 0,
                        "burn": 0,
                        "metadata_update": 0,
                        "other": 0
                    }
                },
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
                nft_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = nft_extractor.get_results()
            logger.info(f"Found {results['stats']['total_nft_ops']} NFT operations")
            
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['nft_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "nft_operations": results["nft_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_nft_activity: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/range")
async def get_nft_range(
    start_slot: int = Query(..., description="Starting slot number"),
    end_slot: int = Query(..., description="Ending slot number"),
    include_transactions: bool = Query(
        default=False,
        description="Include transaction details in response"
    )
) -> Dict[str, Any]:
    """
    Get NFT activity for a range of slots.
    
    Args:
        start_slot: Starting slot number
        end_slot: Ending slot number
        include_transactions: Whether to include transaction details
        
    Returns:
        Dict containing NFT activity analysis for the slot range
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        nft_extractor = NFTExtractor()
        
        # Initialize and get blocks
        await query_handler.initialize()
        logger.info(f"Analyzing NFT activity from slot {start_slot} to {end_slot}")
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
                "nft_operations": [],
                "stats": {
                    "total_nft_ops": 0,
                    "operation_types": {
                        "mint": 0,
                        "transfer": 0,
                        "burn": 0,
                        "metadata_update": 0,
                        "other": 0
                    }
                },
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
                nft_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = nft_extractor.get_results()
            
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['nft_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "nft_operations": results["nft_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_nft_range: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/collection/{collection}")
async def get_collection_activity(
    collection: str,
    blocks: int = Query(
        default=100,
        description="Number of recent blocks to analyze",
        ge=1,
        le=1000
    )
) -> Dict[str, Any]:
    """
    Get NFT activity for a specific collection.
    
    Args:
        collection: Collection address to analyze
        blocks: Number of recent blocks to analyze (default: 100)
        
    Returns:
        Dict containing collection activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        nft_extractor = NFTExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing collection {collection} over {blocks} blocks")
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
            logger.warning("No blocks found")
            return {
                "success": True,
                "collection": None,
                "stats": {
                    "total_nft_ops": 0,
                    "operation_types": {
                        "mint": 0,
                        "transfer": 0,
                        "burn": 0,
                        "metadata_update": 0,
                        "other": 0
                    }
                }
            }
            
        # Process blocks
        logger.info(f"Processing {len(blocks_list)} blocks")
        for block in blocks_list:
            try:
                if not block:
                    logger.warning("Empty block data")
                    continue
                    
                logger.debug(f"Processing block with {len(block.get('transactions', []))} transactions")
                nft_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = nft_extractor.get_results()
            
            # Filter operations for this collection
            collection_ops = [
                op for op in results["nft_operations"]
                if op.get("collection") == collection
            ]
            
            if not collection_ops:
                logger.warning(f"No activity found for collection {collection}")
                return {
                    "success": True,
                    "collection": None,
                    "stats": {
                        "total_nft_ops": 0,
                        "operation_types": {
                            "mint": 0,
                            "transfer": 0,
                            "burn": 0,
                            "metadata_update": 0,
                            "other": 0
                        }
                    }
                }
                
            # Calculate collection-specific stats
            collection_stats = {
                "total_nft_ops": len(collection_ops),
                "operation_types": {
                    "mint": sum(1 for op in collection_ops if op["operation_type"] == "mint"),
                    "transfer": sum(1 for op in collection_ops if op["operation_type"] == "transfer"),
                    "burn": sum(1 for op in collection_ops if op["operation_type"] == "burn"),
                    "metadata_update": sum(1 for op in collection_ops if op["operation_type"] == "metadata_update"),
                    "other": sum(1 for op in collection_ops if op["operation_type"] == "other")
                }
            }
            
            return {
                "success": True,
                "collection": collection,
                "nft_operations": collection_ops,
                "stats": collection_stats,
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_collection_activity: {str(e)}")
        return {"success": False, "error": str(e)}
