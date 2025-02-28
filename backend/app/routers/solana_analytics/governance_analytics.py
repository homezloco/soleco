"""
Governance Analytics Module - Handles analysis of governance activities on Solana
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException
from ..utils.solana_query import SolanaQueryHandler
from ..utils.handlers.governance_extractor import GovernanceExtractor
from ..utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)

# Create router
router = APIRouter(
    tags=["soleco"]
)

@router.get("/activity")
async def get_governance_activity(
    blocks: int = Query(
        default=100,
        description="Number of recent blocks to analyze",
        ge=1,
        le=1000
    ),
    include_transactions: bool = Query(
        default=False,
        description="Include transaction details in response"
    )
) -> Dict[str, Any]:
    """
    Get governance activity from recent blocks.
    
    Args:
        blocks: Number of recent blocks to analyze (default: 100)
        include_transactions: Whether to include transaction details
        
    Returns:
        Dict containing governance activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        governance_extractor = GovernanceExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing governance activity from {blocks} recent blocks")
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
                "governance_operations": [],
                "stats": {
                    "total_governance_ops": 0,
                    "operation_types": {
                        "proposal_create": 0,
                        "vote_cast": 0,
                        "comment": 0,
                        "execution": 0,
                        "config_change": 0,
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
                governance_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = governance_extractor.get_results()
            logger.info(f"Found {results['stats']['total_governance_ops']} governance operations")
            
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['governance_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "governance_operations": results["governance_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_governance_activity: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/range")
async def get_governance_range(
    start_slot: int = Query(..., description="Starting slot number"),
    end_slot: int = Query(..., description="Ending slot number"),
    include_transactions: bool = Query(
        default=False,
        description="Include transaction details in response"
    )
) -> Dict[str, Any]:
    """
    Get governance activity for a range of slots.
    
    Args:
        start_slot: Starting slot number
        end_slot: Ending slot number
        include_transactions: Whether to include transaction details
        
    Returns:
        Dict containing governance activity analysis for the slot range
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        governance_extractor = GovernanceExtractor()
        
        # Initialize and get blocks
        await query_handler.initialize()
        logger.info(f"Analyzing governance activity from slot {start_slot} to {end_slot}")
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
                "governance_operations": [],
                "stats": {
                    "total_governance_ops": 0,
                    "operation_types": {
                        "proposal_create": 0,
                        "vote_cast": 0,
                        "comment": 0,
                        "execution": 0,
                        "config_change": 0,
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
                governance_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = governance_extractor.get_results()
            
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['governance_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "governance_operations": results["governance_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_governance_range: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/proposal/{proposal_id}")
async def get_proposal_activity(
    proposal_id: str,
    blocks: int = Query(
        default=1000,
        description="Number of recent blocks to analyze",
        ge=1,
        le=10000
    )
) -> Dict[str, Any]:
    """
    Get governance activity for a specific proposal.
    
    Args:
        proposal_id: Proposal ID to analyze
        blocks: Number of recent blocks to analyze (default: 1000)
        
    Returns:
        Dict containing proposal activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        governance_extractor = GovernanceExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing proposal {proposal_id} over {blocks} blocks")
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
                "proposal": None,
                "stats": {
                    "total_votes": 0,
                    "vote_distribution": {
                        "yes": 0,
                        "no": 0,
                        "abstain": 0
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
                governance_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = governance_extractor.get_results()
            
            # Filter operations for this proposal
            proposal_ops = [
                op for op in results["governance_operations"]
                if op.get("governance_details", {}).get("proposal_id") == proposal_id
            ]
            
            if not proposal_ops:
                logger.warning(f"No activity found for proposal {proposal_id}")
                return {
                    "success": True,
                    "proposal": None,
                    "stats": {
                        "total_votes": 0,
                        "vote_distribution": {
                            "yes": 0,
                            "no": 0,
                            "abstain": 0
                        }
                    }
                }
                
            # Calculate proposal-specific stats
            vote_ops = [op for op in proposal_ops if op["operation_type"] == "vote_cast"]
            vote_distribution = {
                "yes": sum(1 for op in vote_ops if op["governance_details"]["vote_type"] == "yes"),
                "no": sum(1 for op in vote_ops if op["governance_details"]["vote_type"] == "no"),
                "abstain": sum(1 for op in vote_ops if op["governance_details"]["vote_type"] == "abstain")
            }
            
            proposal_stats = {
                "total_votes": len(vote_ops),
                "vote_distribution": vote_distribution,
                "unique_voters": len({
                    op["governance_details"]["voter"]
                    for op in vote_ops
                }),
                "execution_status": next(
                    (op["governance_details"]["execution_status"]
                     for op in reversed(proposal_ops)
                     if op["operation_type"] == "execution"),
                    None
                )
            }
            
            return {
                "success": True,
                "proposal": proposal_id,
                "governance_operations": proposal_ops,
                "stats": proposal_stats,
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_proposal_activity: {str(e)}")
        return {"success": False, "error": str(e)}
