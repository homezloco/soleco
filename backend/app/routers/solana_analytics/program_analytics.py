"""
Program Analytics Module - Handles analysis of program activities on Solana
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Query, HTTPException
from ..utils.solana_query import SolanaQueryHandler
from ..utils.handlers.program_extractor import ProgramExtractor
from ..utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)

# Create router
router = APIRouter(
    tags=["soleco"]
)

@router.get("/activity")
async def get_program_activity(
    blocks: int = Query(
        default=100,
        description="Number of recent blocks to analyze",
        ge=1,
        le=1000
    ),
    include_transactions: bool = Query(
        default=False,
        description="Include transaction details in response"
    ),
    program_ids: Optional[List[str]] = Query(
        default=None,
        description="Optional list of program IDs to filter by"
    )
) -> Dict[str, Any]:
    """
    Get program activity from recent blocks.
    
    Args:
        blocks: Number of recent blocks to analyze (default: 100)
        include_transactions: Whether to include transaction details
        program_ids: Optional list of program IDs to filter by
        
    Returns:
        Dict containing program activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        program_extractor = ProgramExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing program activity from {blocks} recent blocks")
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
                "program_operations": [],
                "stats": {
                    "total_program_ops": 0,
                    "operation_types": {
                        "invoke": 0,
                        "upgrade": 0,
                        "close": 0,
                        "initialize": 0,
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
                program_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = program_extractor.get_results()
            logger.info(f"Found {results['stats']['total_program_ops']} program operations")
            
            # Filter by program IDs if specified
            if program_ids:
                results['program_operations'] = [
                    op for op in results['program_operations']
                    if op['program_id'] in program_ids
                ]
                
                # Update stats for filtered operations
                filtered_stats = {
                    'total_program_ops': len(results['program_operations']),
                    'operation_types': {
                        op_type: sum(1 for op in results['program_operations']
                                   if op['operation_type'] == op_type)
                        for op_type in ['invoke', 'upgrade', 'close', 'initialize', 'other']
                    },
                    'program_stats': {
                        program_id: stats
                        for program_id, stats in results['stats']['program_stats'].items()
                        if program_id in program_ids
                    }
                }
                results['stats'].update(filtered_stats)
                
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['program_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "program_operations": results["program_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_program_activity: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/range")
async def get_program_range(
    start_slot: int = Query(..., description="Starting slot number"),
    end_slot: int = Query(..., description="Ending slot number"),
    include_transactions: bool = Query(
        default=False,
        description="Include transaction details in response"
    ),
    program_ids: Optional[List[str]] = Query(
        default=None,
        description="Optional list of program IDs to filter by"
    )
) -> Dict[str, Any]:
    """
    Get program activity for a range of slots.
    
    Args:
        start_slot: Starting slot number
        end_slot: Ending slot number
        include_transactions: Whether to include transaction details
        program_ids: Optional list of program IDs to filter by
        
    Returns:
        Dict containing program activity analysis for the slot range
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        program_extractor = ProgramExtractor()
        
        # Initialize and get blocks
        await query_handler.initialize()
        logger.info(f"Analyzing program activity from slot {start_slot} to {end_slot}")
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
                "program_operations": [],
                "stats": {
                    "total_program_ops": 0,
                    "operation_types": {
                        "invoke": 0,
                        "upgrade": 0,
                        "close": 0,
                        "initialize": 0,
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
                program_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = program_extractor.get_results()
            
            # Filter by program IDs if specified
            if program_ids:
                results['program_operations'] = [
                    op for op in results['program_operations']
                    if op['program_id'] in program_ids
                ]
                
                # Update stats for filtered operations
                filtered_stats = {
                    'total_program_ops': len(results['program_operations']),
                    'operation_types': {
                        op_type: sum(1 for op in results['program_operations']
                                   if op['operation_type'] == op_type)
                        for op_type in ['invoke', 'upgrade', 'close', 'initialize', 'other']
                    },
                    'program_stats': {
                        program_id: stats
                        for program_id, stats in results['stats']['program_stats'].items()
                        if program_id in program_ids
                    }
                }
                results['stats'].update(filtered_stats)
                
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['program_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "program_operations": results["program_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_program_range: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/program/{program_id}")
async def get_program_details(
    program_id: str,
    blocks: int = Query(
        default=1000,
        description="Number of recent blocks to analyze",
        ge=1,
        le=10000
    )
) -> Dict[str, Any]:
    """
    Get detailed activity for a specific program.
    
    Args:
        program_id: Program ID to analyze
        blocks: Number of recent blocks to analyze (default: 1000)
        
    Returns:
        Dict containing program activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        program_extractor = ProgramExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing program {program_id} over {blocks} blocks")
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
                "program": None,
                "stats": {
                    "total_invocations": 0,
                    "operation_types": {
                        "invoke": 0,
                        "upgrade": 0,
                        "close": 0,
                        "initialize": 0,
                        "other": 0
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
                program_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = program_extractor.get_results()
            
            # Filter operations for this program
            program_ops = [
                op for op in results["program_operations"]
                if op['program_id'] == program_id
            ]
            
            if not program_ops:
                logger.warning(f"No activity found for program {program_id}")
                return {
                    "success": True,
                    "program": None,
                    "stats": {
                        "total_invocations": 0,
                        "operation_types": {
                            "invoke": 0,
                            "upgrade": 0,
                            "close": 0,
                            "initialize": 0,
                            "other": 0
                        }
                    }
                }
                
            # Get program-specific stats
            program_stats = results['stats']['program_stats'].get(program_id, {})
            
            return {
                "success": True,
                "program": program_id,
                "program_operations": program_ops,
                "stats": {
                    "total_invocations": len(program_ops),
                    "operation_types": {
                        op_type: sum(1 for op in program_ops
                                   if op['operation_type'] == op_type)
                        for op_type in ['invoke', 'upgrade', 'close', 'initialize', 'other']
                    },
                    "unique_callers": len(program_stats.get('unique_callers', set())),
                    "error_count": program_stats.get('error_count', 0),
                    "performance": {
                        "compute_units": {
                            "total": sum(op['operation_details'].get('compute_units', 0)
                                       for op in program_ops),
                            "average": sum(op['operation_details'].get('compute_units', 0)
                                         for op in program_ops) / len(program_ops)
                            if program_ops else 0,
                            "max": max((op['operation_details'].get('compute_units', 0)
                                      for op in program_ops), default=0)
                        }
                    }
                },
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_program_details: {str(e)}")
        return {"success": False, "error": str(e)}
