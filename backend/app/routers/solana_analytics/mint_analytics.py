"""
Mint Analytics Module - Handles analysis of mint activities including Token2022 program
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException
from solana.rpc.commitment import Commitment

from app.utils.solana_query import SolanaQueryHandler
from app.utils.handlers.mint_response_handler import MintResponseHandler
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/mint",
    tags=["Soleco"]
)

@router.get("/activity", response_model=Dict[str, Any])
async def get_mint_activity(
    num_blocks: Optional[int] = 100,
    include_transactions: Optional[bool] = False
) -> Dict[str, Any]:
    """
    Get mint activity from recent blocks.
    
    Args:
        num_blocks: Number of recent blocks to analyze
        include_transactions: Whether to include transaction details
        
    Returns:
        Dict containing mint analytics data
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        mint_extractor = MintResponseHandler()
        
        # Initialize and get recent blocks
        mint_data = await query_handler.get_mint_activity(
            num_blocks=num_blocks,
            include_transactions=include_transactions
        )
        
        return {
            "status": "success",
            "data": mint_data,
            "message": "Successfully retrieved mint activity"
        }
        
    except Exception as e:
        logger.error(f"Failed to get mint activity: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get mint activity: {str(e)}"
        )

@router.get("/range", response_model=Dict[str, Any])
async def get_mint_range(
    start_slot: int,
    end_slot: int,
    include_transactions: Optional[bool] = False
) -> Dict[str, Any]:
    """
    Get mint activity for a range of slots.
    
    Args:
        start_slot: Starting slot number
        end_slot: Ending slot number
        include_transactions: Whether to include transaction details
        
    Returns:
        Dict containing mint activity analysis for the slot range
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        mint_extractor = MintResponseHandler()
        
        # Initialize and get blocks
        mint_data = await query_handler.get_mint_activity(
            start_slot=start_slot,
            end_slot=end_slot,
            include_transactions=include_transactions
        )
        
        return {
            "status": "success",
            "data": mint_data,
            "message": "Successfully retrieved mint activity"
        }
        
    except Exception as e:
        logger.error(f"Failed to get mint activity: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get mint activity: {str(e)}"
        )
