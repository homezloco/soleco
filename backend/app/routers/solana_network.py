"""
Solana Network Router - Handles endpoints related to Solana network status and performance
"""
from typing import Dict, Any, Optional
import logging
import asyncio
import traceback
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
import pytz

from ..utils.solana_rpc import get_connection_pool
from ..utils.solana_query import SolanaQueryHandler
from ..utils.handlers.network_status_handler import NetworkStatusHandler
from ..constants.cache import (
    NETWORK_STATUS_CACHE_TTL,
    PERFORMANCE_METRICS_CACHE_TTL
)
from ..database.sqlite import db_cache

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(
    tags=["Soleco"],
    responses={404: {"description": "Not found"}},
)

# Initialize handlers
solana_query_handler = None
network_status_handler = None

async def initialize_handlers():
    """Initialize handlers if they haven't been initialized yet."""
    global solana_query_handler, network_status_handler
    
    if solana_query_handler is None:
        # Get connection pool
        pool = await get_connection_pool()
        solana_query_handler = SolanaQueryHandler(pool)
    
    if network_status_handler is None:
        network_status_handler = NetworkStatusHandler(solana_query_handler)


@router.get("/network/status", response_model=Dict[str, Any])
async def get_network_status(
    summary_only: bool = Query(False, description="Return only the network summary without detailed node information"),
    refresh: bool = Query(False, description="Force refresh from Solana RPC")
) -> Dict[str, Any]:
    """
    Retrieve comprehensive Solana network status with robust error handling.
    
    This endpoint provides a detailed overview of the current Solana network status,
    including health, node information, version distribution, and performance metrics.
    
    - **summary_only**: When true, returns only summary information without the detailed node list
    - **refresh**: When true, forces a refresh from the Solana RPC instead of using cached data
    
    Returns a JSON object containing:
    
    - **status**: Overall network health status (healthy, degraded, error)
    - **errors**: Any errors encountered during data collection
    - **timestamp**: When the data was retrieved
    - **network_summary**: Summary statistics including:
      - **total_nodes**: Total number of nodes in the network
      - **rpc_nodes_available**: Number of nodes providing RPC services
      - **rpc_availability_percentage**: Percentage of nodes providing RPC services
      - **latest_version**: Latest Solana version detected in the network
      - **nodes_on_latest_version_percentage**: Percentage of nodes on the latest version
      - **version_distribution**: Distribution of node versions (top 5)
      - **total_versions_in_use**: Total number of different versions in use
      - **total_feature_sets_in_use**: Total number of different feature sets in use
    - **cluster_nodes**: Information about cluster nodes
    - **network_version**: Current network version information
    - **epoch_info**: Current epoch information
    - **performance_metrics**: Network performance metrics
    """
    await initialize_handlers()
    
    # Check cache first if not forcing refresh
    if not refresh:
        cache_key = f"network_status:{summary_only}"
        cached_data = await db_cache.get(cache_key)
        if cached_data:
            logger.info(f"Using cached network status data (summary_only={summary_only})")
            return cached_data
    
    try:
        status_data = await network_status_handler.get_network_status(summary_only=summary_only)
        status_data["timestamp"] = datetime.now(pytz.utc).isoformat()

        response = {
            "network_status": status_data,
            "timestamp": datetime.now(pytz.utc).isoformat()
        }

        if not refresh:
            cache_key = f"network_status:{summary_only}"
            await db_cache.set(cache_key, response, ttl=NETWORK_STATUS_CACHE_TTL)

        return response
    except Exception as e:
        logger.error(f"Error getting network status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/metrics", response_model=Dict[str, Any])
async def get_performance_metrics(
    refresh: bool = Query(False, description="Force refresh from Solana RPC")
) -> Dict[str, Any]:
    """
    Retrieve current Solana network performance metrics
    - Transaction processing speed
    - Block production rate
    - Network congestion indicators
    - Summary statistics for both performance samples and block production
    
    Args:
        refresh: Force refresh from Solana RPC
        
    Returns:
        Dict[str, Any]: Performance metrics data
    """
    await initialize_handlers()
    
    # Check cache first if not forcing refresh
    if not refresh:
        cache_key = "performance_metrics"
        cached_data = await db_cache.get(cache_key)
        if cached_data:
            return cached_data
    
    try:
        # Get performance metrics from handler
        metrics_data = await network_status_handler.get_performance_metrics()
        
        # Add current timestamp
        response = {
            "performance_metrics": metrics_data,
            "timestamp": datetime.now(pytz.utc).isoformat()
        }
        
        # Cache the result
        await db_cache.set("performance_metrics", response, ttl=PERFORMANCE_METRICS_CACHE_TTL)
        
        return response
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance metrics: {str(e)}")
