"""
Solana dependencies module.
Provides shared instances of Solana-related services.
"""
from typing import Optional
from fastapi import Depends

from ..utils.solana_rpc import get_connection_pool, SolanaConnectionPool
from ..utils.solana_query import SolanaQueryHandler
from ..utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)

# Global instances
_query_handler: Optional[SolanaQueryHandler] = None

async def get_query_handler() -> SolanaQueryHandler:
    """
    Get or create a shared SolanaQueryHandler instance.
    This ensures we only have one instance across the application.
    """
    global _query_handler
    
    if _query_handler is None:
        # Get connection pool
        pool = await get_connection_pool()
        if not pool._initialized:
            from app.utils.solana_rpc import DEFAULT_RPC_ENDPOINTS
            await pool.initialize(DEFAULT_RPC_ENDPOINTS)
            
        # Create query handler
        _query_handler = SolanaQueryHandler(pool)
        await _query_handler.initialize()
        logger.info("Created and initialized shared SolanaQueryHandler instance")
        
    return _query_handler
