"""
Analytics router for historical data.
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query

from app.database.sqlite import db_cache

# Configure logging
logger = logging.getLogger("app.routers.analytics")

# Create router
router = APIRouter(
    prefix="",  # Remove prefix since it's added in main.py
    tags=["analytics"],
    responses={404: {"description": "Not found"}},
)

@router.get("/network/status/history")
@router.get("/network/history")  # Add alias endpoint to match frontend
async def get_network_status_history(
    limit: int = Query(24, description="Maximum number of records to return"),
    hours: int = Query(24, description="Number of hours to look back")
) -> List[Dict[str, Any]]:
    """
    Get network status history.
    
    Args:
        limit: Maximum number of records to return
        hours: Number of hours to look back
        
    Returns:
        List of network status records
    """
    logger.info(f"Getting network status history for the past {hours} hours (limit: {limit})")
    return db_cache.get_network_status_history(limit, hours)

@router.get("/mint/history")
async def get_mint_analytics_history(
    blocks: int = Query(2, description="Number of blocks analyzed"),
    limit: int = Query(24, description="Maximum number of records to return"),
    hours: int = Query(24, description="Number of hours to look back")
) -> List[Dict[str, Any]]:
    """
    Get mint analytics history.
    
    Args:
        blocks: Number of blocks analyzed
        limit: Maximum number of records to return
        hours: Number of hours to look back
        
    Returns:
        List of mint analytics records
    """
    logger.info(f"Getting mint analytics history for {blocks} blocks for the past {hours} hours (limit: {limit})")
    return db_cache.get_mint_analytics_history(blocks, limit, hours)

@router.get("/pump/tokens/history")
@router.get("/pump/history")  # Add alias endpoint to match frontend
async def get_pump_tokens_history(
    timeframe: str = Query("24h", description="Timeframe (1h, 24h, 7d)"),
    sort_metric: str = Query("volume", description="Sort metric (volume, price_change, holder_growth)"),
    limit: int = Query(24, description="Maximum number of records to return"),
    hours: int = Query(24, description="Number of hours to look back")
) -> List[Dict[str, Any]]:
    """
    Get pump tokens history.
    
    Args:
        timeframe: Timeframe (1h, 24h, 7d)
        sort_metric: Sort metric (volume, price_change, holder_growth)
        limit: Maximum number of records to return
        hours: Number of hours to look back
        
    Returns:
        List of pump tokens records
    """
    logger.info(f"Getting pump tokens history for {timeframe} timeframe and {sort_metric} sort metric for the past {hours} hours (limit: {limit})")
    return db_cache.get_pump_tokens_history(timeframe, sort_metric, limit, hours)

@router.get("/rpc/nodes/history")
@router.get("/rpc/history")  # Add alias endpoint to match frontend
async def get_rpc_nodes_history(
    limit: int = Query(24, description="Maximum number of records to return"),
    hours: int = Query(24, description="Number of hours to look back")
) -> List[Dict[str, Any]]:
    """
    Get RPC nodes history.
    
    Args:
        limit: Maximum number of records to return
        hours: Number of hours to look back
        
    Returns:
        List of RPC nodes history records
    """
    logger.info(f"Getting RPC nodes history for the past {hours} hours (limit: {limit})")
    return db_cache.get_rpc_nodes_history(limit, hours)

@router.get("/performance/metrics/history")
@router.get("/performance/history")  # Add alias endpoint to match frontend
async def get_performance_metrics_history(
    limit: int = Query(24, description="Maximum number of records to return"),
    hours: int = Query(24, description="Number of hours to look back")
) -> List[Dict[str, Any]]:
    """
    Get performance metrics history.
    
    Args:
        limit: Maximum number of records to return
        hours: Number of hours to look back
        
    Returns:
        List of performance metrics history records
    """
    logger.info(f"Getting performance metrics history for the past {hours} hours (limit: {limit})")
    return db_cache.get_performance_metrics_history(limit, hours)
