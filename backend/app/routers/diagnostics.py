"""
Diagnostics router for the Soleco API.
"""
import logging
import platform
import psutil
import os
import sys
import time
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database.utils import export_database_stats, cleanup_database
from app.utils.comprehensive_solana_diagnostic import run_full_health_check
from app.utils.solana_import_diagnostic import validate_imports
from app.dependencies.rate_limiter import create_rate_limiter

router = APIRouter(
    prefix="",  # Remove prefix since it's added by main.py
    tags=["Soleco Diagnostics"]
)

@router.get("/solana-health")
async def get_solana_health() -> Dict[str, Any]:
    """Get comprehensive Solana node health status"""
    return await run_full_health_check()

@router.get("/dependency-validation")
async def validate_dependencies() -> Dict[str, Any]:
    """Validate all Solana and local module dependencies"""
    return await validate_imports()

@router.get("/memory-usage", dependencies=[Depends(create_rate_limiter(times=2, seconds=5))])
async def get_memory_usage() -> Dict[str, float]:
    """Get current memory usage statistics"""
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        "rss": memory_info.rss,  # Resident Set Size
        "vms": memory_info.vms,  # Virtual Memory Size
        "percent": process.memory_percent()  # Memory usage as percentage
    }

@router.get("/database")
async def get_database_diagnostics(
    cleanup: bool = Query(False, description="Whether to clean up old records from the database")
) -> Dict[str, Any]:
    """
    Get database diagnostics.
    
    Args:
        cleanup: Whether to clean up old records from the database
        
    Returns:
        Database diagnostics
    """
    logger = logging.getLogger("app.routers.diagnostics")
    logger.info("Getting database diagnostics")
    
    # Clean up database if requested
    cleanup_result = None
    if cleanup:
        logger.info("Cleaning up database")
        cleanup_result = cleanup_database()
    
    # Get database stats
    stats = export_database_stats()
    
    # Add cleanup result to stats
    if cleanup_result is not None:
        stats['cleanup_result'] = cleanup_result
    
    return stats
