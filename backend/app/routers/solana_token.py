"""
Solana Token Router - Handles endpoints related to Solana tokens
"""
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query
from app.utils.handlers.token_handler import TokenHandler
from app.utils.solana_query import SolanaQueryHandler
from ..database.sqlite import db_cache

# Configure logging
import logging
logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(
    tags=["Soleco"],
    responses={404: {"description": "Not found"}},
)

# Initialize handlers
token_handler = None

async def initialize_handlers():
    """Initialize handlers if they haven't been initialized yet."""
    global token_handler
    
    if token_handler is None:
        try:
            # Get connection pool
            pool = await get_connection_pool()
            solana_query_handler = SolanaQueryHandler(pool)
            token_handler = TokenHandler(solana_query_handler)
            await token_handler.initialize()
        except Exception as e:
            logger.error(f"Error initializing token handler: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@router.on_event("startup")
async def startup_event():
    await initialize_handlers()

@router.get("/token/{token_address}")
async def get_token_info(
    token_address: str,
    refresh: bool = Query(False, description="Force refresh the cache")
) -> Dict[str, Any]:
    """
    Get information about a specific token.
    
    Args:
        token_address: The token address to look up
        refresh: Whether to force refresh the cache
    
    Returns:
        Dict containing token information
    """
    # Check cache first if not forcing refresh
    if not refresh:
        cached_data = db_cache.get_cache(f"token-info-{token_address}")
        if cached_data:
            return cached_data

    try:
        # Get token info
        token_info = await token_handler.get_token_info(token_address)

        # Add timestamp
        response = {
            "token_info": token_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Update cache
        db_cache.set_cache(f"token-info-{token_address}", response)

        return response
    except Exception as e:
        logger.error(f"Error fetching token info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
