"""
Solana Network Router - Handles endpoints related to Solana network status and performance
"""
from typing import Dict, Any, Optional
import logging
import asyncio
import traceback
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime

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
        # Set a timeout for the entire operation
        try:
            # Get network status from handler with timeout
            status_data = await asyncio.wait_for(
                network_status_handler.get_network_status(summary_only=summary_only),
                timeout=10.0  # 10 second timeout for the entire operation
            )
            
            # Cache the result
            cache_key = f"network_status:{summary_only}"
            await db_cache.set(cache_key, status_data, ttl=NETWORK_STATUS_CACHE_TTL)
            
            logger.info(f"Successfully retrieved and cached network status (summary_only={summary_only})")
            return status_data
            
        except asyncio.TimeoutError:
            logger.error("Network status endpoint timed out after 10 seconds")
            
            # Try to get cached data as fallback, even if refresh was requested
            cache_key = f"network_status:{summary_only}"
            cached_data = await db_cache.get(cache_key)
            
            if cached_data:
                logger.info("Returning cached data due to timeout")
                # Add error information to the cached data
                if "errors" not in cached_data:
                    cached_data["errors"] = []
                    
                cached_data["errors"].append({
                    "type": "timeout",
                    "message": "Request timed out, returning cached data",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Update status to indicate degraded service
                cached_data["status"] = "degraded"
                cached_data["message"] = "Data retrieval timed out, showing cached data"
                
                return cached_data
            else:
                # No cached data available, return error
                logger.error("No cached data available after timeout")
                return {
                    "status": "error",
                    "message": "Network status retrieval timed out and no cached data available",
                    "timestamp": datetime.now().isoformat(),
                    "errors": [{
                        "type": "timeout",
                        "message": "Network status endpoint timed out after 10 seconds",
                        "timestamp": datetime.now().isoformat()
                    }]
                }
                
    except Exception as e:
        logger.error(f"Error getting network status: {str(e)}", exc_info=True)
        
        # Try to get cached data as fallback
        try:
            cache_key = f"network_status:{summary_only}"
            cached_data = await db_cache.get(cache_key)
            
            if cached_data:
                logger.info("Returning cached data due to error")
                # Add error information to the cached data
                if "errors" not in cached_data:
                    cached_data["errors"] = []
                    
                cached_data["errors"].append({
                    "type": "retrieval_error",
                    "message": f"Error retrieving fresh data: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Update status to indicate degraded service
                cached_data["status"] = "degraded"
                cached_data["message"] = "Error retrieving fresh data, showing cached data"
                
                return cached_data
        except Exception as cache_error:
            logger.error(f"Error accessing cache after primary error: {str(cache_error)}")
            
        # If we get here, both the primary request and cache fallback failed
        return {
            "status": "error",
            "message": f"Error retrieving network status: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "errors": [{
                "type": "network_status_error",
                "message": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            }]
        }


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
        
        # Cache the result
        await db_cache.set("performance_metrics", metrics_data, ttl=PERFORMANCE_METRICS_CACHE_TTL)
        
        return metrics_data
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance metrics: {str(e)}")
