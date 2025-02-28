"""
Router for program ID analytics endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Dict, List, Optional, Any

from app.utils.programidextractor import ProgramIdExtractor
from app.utils.solana_query import SolanaQueryHandler
from app.utils.solana_rpc import get_connection_pool
from app.utils.logging_config import setup_logging

# Setup logging
logger = setup_logging('solana.analytics.programid')

# Create router
router = APIRouter(
    prefix="/analytics/programid",
    tags=["Solana Program Analytics"],
    responses={404: {"description": "Not found"}},
)

@router.get("/analyze/{program_id}")
async def analyze_program(
    program_id: str = Path(..., description="Program ID to analyze"),
    blocks: int = Query(10, description="Number of recent blocks to analyze", ge=1, le=100)
) -> Dict[str, Any]:
    """
    Analyze recent activity of a specific program ID.
    """
    try:
        pool = await get_connection_pool()
        query_handler = SolanaQueryHandler(pool)
        extractor = ProgramIdExtractor()
        
        # Get latest block
        latest_block = await query_handler.get_latest_block()
        if not latest_block:
            raise HTTPException(
                status_code=500,
                detail="Failed to get latest block"
            )
            
        start_slot = latest_block['slot']
        end_slot = start_slot - blocks + 1
        
        # Process blocks
        block_results = await query_handler.process_blocks(
            num_blocks=blocks,
            start_slot=start_slot,
            end_slot=end_slot
        )
        
        if not block_results.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process blocks: {block_results.get('error')}"
            )
            
        # Process transactions
        for block in block_results.get('blocks', []):
            if not block:
                continue
                
            for tx in block.get('transactions', []):
                if not tx:
                    continue
                try:
                    extractor.handle_transaction(tx)
                except Exception as e:
                    logger.error(f"Error processing transaction: {e}")
                    continue
                
        # Get program stats
        stats = extractor.get_program_stats(program_id)
        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"No activity found for program {program_id}"
            )
            
        return {
            "program_id": program_id,
            "stats": stats,
            "blocks_analyzed": len(block_results.get('blocks', []))
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing program {program_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze program: {str(e)}"
        )

@router.get("/discover")
async def discover_programs(
    blocks: int = Query(20, description="Number of blocks to analyze", ge=1, le=100),
    min_calls: int = Query(5, description="Minimum number of calls to be considered active")
) -> Dict[str, Any]:
    """
    Discover new or active programs by analyzing recent blocks.
    """
    try:
        pool = await get_connection_pool()
        query_handler = SolanaQueryHandler(pool)
        extractor = ProgramIdExtractor()
        
        # Get latest block
        latest_block = await query_handler.get_latest_block()
        if not latest_block:
            raise HTTPException(
                status_code=500,
                detail="Failed to get latest block"
            )
            
        start_slot = latest_block['slot']
        end_slot = start_slot - blocks + 1
        
        # Process blocks
        block_results = await query_handler.process_blocks(
            num_blocks=blocks,
            start_slot=start_slot,
            end_slot=end_slot
        )
        
        if not block_results.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process blocks: {block_results.get('error')}"
            )
            
        # Process transactions
        for block in block_results.get('blocks', []):
            if not block:
                continue
                
            for tx in block.get('transactions', []):
                if not tx:
                    continue
                try:
                    extractor.handle_transaction(tx)
                except Exception as e:
                    logger.error(f"Error processing transaction: {e}")
                    continue
                
        # Get active programs
        active_programs = extractor.get_active_programs(min_calls)
        
        if not active_programs:
            logger.warning("No active programs found")
            return {
                "programs": [],
                "total": 0,
                "blocks_analyzed": len(block_results.get('blocks', []))
            }
            
        return {
            "programs": active_programs,
            "total": len(active_programs),
            "blocks_analyzed": len(block_results.get('blocks', []))
        }
            
    except Exception as e:
        logger.error(f"Error discovering programs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to discover programs: {str(e)}"
        )

@router.get("/stats")
async def get_program_stats(
    timeframe: int = Query(
        24,
        description="Timeframe in hours to analyze",
        ge=1,
        le=168
    )
) -> Dict[str, Any]:
    """
    Get overall statistics about program usage across the network.
    """
    try:
        pool = await get_connection_pool()
        query_handler = SolanaQueryHandler(pool)
        extractor = ProgramIdExtractor()
        
        # Get latest block
        latest_block = await query_handler.get_latest_block()
        if not latest_block:
            raise HTTPException(
                status_code=500,
                detail="Failed to get latest block"
            )
            
        start_slot = latest_block['slot']
        # Estimate number of blocks in timeframe (assuming 2 blocks per second)
        blocks_in_timeframe = timeframe * 3600 * 2  # hours * seconds/hour * blocks/second
        end_slot = start_slot - blocks_in_timeframe + 1
        
        # Process blocks in batches
        block_results = await query_handler.process_blocks(
            num_blocks=blocks_in_timeframe,
            start_slot=start_slot,
            end_slot=end_slot,
            batch_size=100  # Process in batches of 100 blocks
        )
        
        if not block_results.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process blocks: {block_results.get('error')}"
            )
        
        # Process transactions
        for block in block_results.get('blocks', []):
            if not block:
                continue
                
            for tx in block.get('transactions', []):
                if not tx:
                    continue
                try:
                    extractor.handle_transaction(tx)
                except Exception as e:
                    logger.error(f"Error processing transaction: {e}")
                    continue
                
        # Get network stats
        stats = extractor.get_network_stats()
        
        return {
            'timeframe_hours': timeframe,
            'stats': stats,
            'blocks_analyzed': len(block_results.get('blocks', []))
        }
    except Exception as e:
        logger.error(f"Error getting program stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting program stats: {str(e)}"
        )

@router.get("/interactions/{program_id}")
async def analyze_program_interactions(
    program_id: str = Path(..., description="Program ID to analyze"),
    depth: int = Query(1, description="Depth of interaction analysis", ge=1, le=3),
    blocks: int = Query(50, description="Number of blocks to analyze", ge=1, le=100)
) -> Dict[str, Any]:
    """
    Analyze how a program interacts with other programs.
    """
    try:
        pool = await get_connection_pool()
        query_handler = SolanaQueryHandler(pool)
        extractor = ProgramIdExtractor()
        
        # Get latest block
        latest_block = await query_handler.get_latest_block()
        if not latest_block:
            raise HTTPException(
                status_code=500,
                detail="Failed to get latest block"
            )
            
        start_slot = latest_block['slot']
        end_slot = start_slot - blocks + 1
        
        # Process blocks
        block_results = await query_handler.process_blocks(
            num_blocks=blocks,
            start_slot=start_slot,
            end_slot=end_slot
        )
        
        if not block_results.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process blocks: {block_results.get('error')}"
            )
        
        # Process transactions
        for block in block_results.get('blocks', []):
            if not block:
                continue
                
            for tx in block.get('transactions', []):
                if not tx:
                    continue
                try:
                    extractor.handle_transaction(tx)
                except Exception as e:
                    logger.error(f"Error processing transaction: {e}")
                    continue
                
        # Get interaction analysis
        interactions = extractor.analyze_interactions(program_id, depth)
        
        if not interactions:
            return {
                "program_id": program_id,
                "interactions": [],
                "depth": depth,
                "blocks_analyzed": len(block_results.get('blocks', []))
            }
            
        return {
            "program_id": program_id,
            "interactions": interactions,
            "depth": depth,
            "blocks_analyzed": len(block_results.get('blocks', []))
        }
            
    except Exception as e:
        logger.error(f"Error analyzing program interactions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze program interactions: {str(e)}"
        )

@router.get("/errors/{program_id}")
async def get_program_errors(
    program_id: str = Path(..., description="Program ID to analyze"),
    blocks: int = Query(100, description="Number of blocks to analyze", ge=1, le=500)
) -> Dict[str, Any]:
    """
    Get error statistics for a specific program.
    """
    try:
        pool = await get_connection_pool()
        query_handler = SolanaQueryHandler(pool)
        extractor = ProgramIdExtractor()
        
        # Get latest block
        latest_block = await query_handler.get_latest_block()
        if not latest_block:
            raise HTTPException(
                status_code=500,
                detail="Failed to get latest block"
            )
            
        start_slot = latest_block['slot']
        end_slot = start_slot - blocks + 1
        
        # Process blocks
        block_results = await query_handler.process_blocks(
            num_blocks=blocks,
            start_slot=start_slot,
            end_slot=end_slot
        )
        
        if not block_results.get('success'):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process blocks: {block_results.get('error')}"
            )
        
        # Process transactions
        for block in block_results.get('blocks', []):
            if not block:
                continue
                
            for tx in block.get('transactions', []):
                if not tx:
                    continue
                try:
                    extractor.handle_transaction(tx)
                except Exception as e:
                    logger.error(f"Error processing transaction: {e}")
                    continue
                
        # Get error statistics
        error_stats = extractor.get_error_stats(program_id)
        
        return {
            "program_id": program_id,
            "error_stats": error_stats,
            "blocks_analyzed": len(block_results.get('blocks', []))
        }
            
    except Exception as e:
        logger.error(f"Error getting program error stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get program error stats: {str(e)}"
        )
