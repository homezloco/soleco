"""
Router for DeFi analytics endpoints.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from app.utils.solana_query import SolanaQueryHandler
from app.utils.handlers.defi_extractor import DefiExtractor
from app.utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)

# Create router
router = APIRouter(
    prefix="/analytics/defi",
    tags=["defi-analytics"],
    responses={404: {"description": "Not found"}},
)

@router.get("/activity")
async def get_defi_activity(
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
    Get DeFi activity from recent blocks.
    
    Args:
        blocks: Number of recent blocks to analyze (default: 10)
        include_transactions: Whether to include transaction details
        
    Returns:
        Dict containing DeFi activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        defi_extractor = DefiExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing DeFi activity from {blocks} recent blocks")
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
                "defi_operations": [],
                "stats": {
                    "total_defi_ops": 0,
                    "operation_types": {
                        "swap": 0,
                        "provide_liquidity": 0,
                        "remove_liquidity": 0,
                        "stake": 0,
                        "unstake": 0,
                        "borrow": 0,
                        "repay": 0,
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
                defi_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = defi_extractor.get_results()
            logger.info(f"Found {results['stats']['total_defi_ops']} DeFi operations")
            
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['defi_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "defi_operations": results["defi_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_defi_activity: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/range")
async def get_defi_range(
    start_slot: int = Query(
        default=...,
        description="Starting slot number"
    ),
    end_slot: int = Query(
        default=...,
        description="Ending slot number"
    ),
    include_transactions: bool = Query(
        default=False,
        description="Include transaction details in response"
    )
) -> Dict[str, Any]:
    """
    Get DeFi activity for a range of slots.
    
    Args:
        start_slot: Starting slot number
        end_slot: Ending slot number
        include_transactions: Whether to include transaction details
        
    Returns:
        Dict containing DeFi activity analysis for the slot range
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        defi_extractor = DefiExtractor()
        
        # Initialize and get blocks
        await query_handler.initialize()
        logger.info(f"Analyzing DeFi activity from slot {start_slot} to {end_slot}")
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
                "defi_operations": [],
                "stats": {
                    "total_defi_ops": 0,
                    "operation_types": {
                        "swap": 0,
                        "provide_liquidity": 0,
                        "remove_liquidity": 0,
                        "stake": 0,
                        "unstake": 0,
                        "borrow": 0,
                        "repay": 0,
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
                defi_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = defi_extractor.get_results()
            
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['defi_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "defi_operations": results["defi_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_defi_range: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/protocol/{protocol}")
async def get_protocol_activity(
    protocol: str,
    blocks: int = Query(
        default=100,
        description="Number of recent blocks to analyze",
        ge=1,
        le=1000
    )
) -> Dict[str, Any]:
    """
    Get DeFi activity for a specific protocol.
    
    Args:
        protocol: Protocol name to analyze
        blocks: Number of recent blocks to analyze (default: 100)
        
    Returns:
        Dict containing protocol activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        defi_extractor = DefiExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing protocol {protocol} over {blocks} blocks")
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
                "protocol": None,
                "stats": {
                    "total_defi_ops": 0,
                    "operation_types": {
                        "swap": 0,
                        "provide_liquidity": 0,
                        "remove_liquidity": 0,
                        "stake": 0,
                        "unstake": 0,
                        "borrow": 0,
                        "repay": 0,
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
                defi_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = defi_extractor.get_results()
            
            # Filter operations for this protocol
            protocol_ops = [
                op for op in results["defi_operations"]
                if op.get("protocol") == protocol
            ]
            
            if not protocol_ops:
                logger.warning(f"No activity found for protocol {protocol}")
                return {
                    "success": True,
                    "protocol": None,
                    "stats": {
                        "total_defi_ops": 0,
                        "operation_types": {
                            "swap": 0,
                            "provide_liquidity": 0,
                            "remove_liquidity": 0,
                            "stake": 0,
                            "unstake": 0,
                            "borrow": 0,
                            "repay": 0,
                            "other": 0
                        }
                    }
                }
                
            # Calculate protocol-specific stats
            protocol_stats = {
                "total_defi_ops": len(protocol_ops),
                "operation_types": {
                    "swap": sum(1 for op in protocol_ops if op["operation_type"] == "swap"),
                    "provide_liquidity": sum(1 for op in protocol_ops if op["operation_type"] == "provide_liquidity"),
                    "remove_liquidity": sum(1 for op in protocol_ops if op["operation_type"] == "remove_liquidity"),
                    "stake": sum(1 for op in protocol_ops if op["operation_type"] == "stake"),
                    "unstake": sum(1 for op in protocol_ops if op["operation_type"] == "unstake"),
                    "borrow": sum(1 for op in protocol_ops if op["operation_type"] == "borrow"),
                    "repay": sum(1 for op in protocol_ops if op["operation_type"] == "repay"),
                    "other": sum(1 for op in protocol_ops if op["operation_type"] == "other")
                }
            }
            
            # Add volume stats if available
            if protocol in results["stats"]["volume_stats"]["by_protocol"]:
                protocol_stats["volume"] = {
                    "total_volume_usd": results["stats"]["volume_stats"]["by_protocol"][protocol]
                }
                
            return {
                "success": True,
                "protocol": protocol,
                "defi_operations": protocol_ops,
                "stats": protocol_stats,
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_protocol_activity: {str(e)}")
        return {"success": False, "error": str(e)}
