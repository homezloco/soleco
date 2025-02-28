"""
Account Analytics Module - Handles analysis of account activities on Solana
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from solana.rpc.commitment import Commitment

from app.utils.solana_query import SolanaQueryHandler
from app.utils.handlers.account_extractor import AccountExtractor
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/account",
    tags=["soleco"]
)

@router.get("/activity")
async def get_account_activity(
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
    Get account activity from recent blocks.
    
    Args:
        blocks: Number of recent blocks to analyze (default: 10)
        include_transactions: Whether to include transaction details
        
    Returns:
        Dict containing account activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        account_extractor = AccountExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing account activity from {blocks} recent blocks")
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
                "accounts": [],
                "stats": {
                    "total_accounts": 0,
                    "total_transactions": 0
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
                account_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = account_extractor.get_results()
            logger.info(f"Found {results['stats']['total_accounts']} accounts")
            
            # Remove transaction details if not requested
            if not include_transactions:
                for account in results['accounts']:
                    if 'transactions' in account:
                        del account['transactions']
                        
            return {
                "success": True,
                "accounts": results["accounts"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_account_activity: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/range")
async def get_account_range(
    start_slot: int = Query(..., description="Starting slot number"),
    end_slot: int = Query(..., description="Ending slot number"),
    include_transactions: bool = Query(
        default=False,
        description="Include transaction details in response"
    )
) -> Dict[str, Any]:
    """
    Get account activity for a range of slots.
    
    Args:
        start_slot: Starting slot number
        end_slot: Ending slot number
        include_transactions: Whether to include transaction details
        
    Returns:
        Dict containing account activity analysis for the slot range
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        account_extractor = AccountExtractor()
        
        # Initialize and get blocks
        await query_handler.initialize()
        logger.info(f"Analyzing account activity from slot {start_slot} to {end_slot}")
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
                "accounts": [],
                "stats": {
                    "total_accounts": 0,
                    "total_transactions": 0
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
                account_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = account_extractor.get_results()
            
            # Remove transaction details if not requested
            if not include_transactions:
                for account in results['accounts']:
                    if 'transactions' in account:
                        del account['transactions']
                        
            return {
                "success": True,
                "accounts": results["accounts"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_account_range: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/account/{address}")
async def get_account_details(
    address: str,
    blocks: int = Query(
        default=100,
        description="Number of recent blocks to analyze",
        ge=1,
        le=1000
    )
) -> Dict[str, Any]:
    """
    Get detailed analysis for a specific account.
    
    Args:
        address: Account address to analyze
        blocks: Number of recent blocks to analyze (default: 100)
        
    Returns:
        Dict containing detailed account analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        account_extractor = AccountExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing account {address} over {blocks} blocks")
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
                "account": None,
                "stats": {
                    "total_transactions": 0,
                    "balance_changes": {"total_sol_change": 0}
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
                account_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = account_extractor.get_results()
            
            # Find the specific account
            account_data = next(
                (acc for acc in results["accounts"] if acc["address"] == address),
                None
            )
            
            if not account_data:
                logger.warning(f"No activity found for account {address}")
                return {
                    "success": True,
                    "account": None,
                    "stats": {
                        "total_transactions": 0,
                        "balance_changes": {"total_sol_change": 0}
                    }
                }
                
            return {
                "success": True,
                "account": account_data,
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_account_details: {str(e)}")
        return {"success": False, "error": str(e)}
