"""
Validator Analytics Module - Handles analysis of validator activities on Solana
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Query, HTTPException
from ..utils.solana_query import SolanaQueryHandler
from ..utils.handlers.validator_extractor import ValidatorExtractor
from ..utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)

# Create router
router = APIRouter(
    tags=["soleco"]
)

@router.get("/activity")
async def get_validator_activity(
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
    validator_ids: Optional[List[str]] = Query(
        default=None,
        description="Optional list of validator IDs to filter by"
    )
) -> Dict[str, Any]:
    """
    Get validator activity from recent blocks.
    
    Args:
        blocks: Number of recent blocks to analyze (default: 100)
        include_transactions: Whether to include transaction details
        validator_ids: Optional list of validator IDs to filter by
        
    Returns:
        Dict containing validator activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        validator_extractor = ValidatorExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing validator activity from {blocks} recent blocks")
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
                "validator_operations": [],
                "stats": {
                    "total_validator_ops": 0,
                    "operation_types": {
                        "vote": 0,
                        "stake": 0,
                        "unstake": 0,
                        "commission_change": 0,
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
                validator_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = validator_extractor.get_results()
            logger.info(f"Found {results['stats']['total_validator_ops']} validator operations")
            
            # Filter by validator IDs if specified
            if validator_ids:
                results['validator_operations'] = [
                    op for op in results['validator_operations']
                    if op['validator'] in validator_ids
                ]
                
                # Update stats for filtered operations
                filtered_stats = {
                    'total_validator_ops': len(results['validator_operations']),
                    'operation_types': {
                        op_type: sum(1 for op in results['validator_operations']
                                   if op['operation_type'] == op_type)
                        for op_type in ['vote', 'stake', 'unstake', 'commission_change', 'other']
                    },
                    'validator_stats': {
                        validator_id: stats
                        for validator_id, stats in results['stats']['validator_stats'].items()
                        if validator_id in validator_ids
                    }
                }
                results['stats'].update(filtered_stats)
                
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['validator_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "validator_operations": results["validator_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_validator_activity: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/range")
async def get_validator_range(
    start_slot: int = Query(..., description="Starting slot number"),
    end_slot: int = Query(..., description="Ending slot number"),
    include_transactions: bool = Query(
        default=False,
        description="Include transaction details in response"
    ),
    validator_ids: Optional[List[str]] = Query(
        default=None,
        description="Optional list of validator IDs to filter by"
    )
) -> Dict[str, Any]:
    """
    Get validator activity for a range of slots.
    
    Args:
        start_slot: Starting slot number
        end_slot: Ending slot number
        include_transactions: Whether to include transaction details
        validator_ids: Optional list of validator IDs to filter by
        
    Returns:
        Dict containing validator activity analysis for the slot range
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        validator_extractor = ValidatorExtractor()
        
        # Initialize and get blocks
        await query_handler.initialize()
        logger.info(f"Analyzing validator activity from slot {start_slot} to {end_slot}")
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
                "validator_operations": [],
                "stats": {
                    "total_validator_ops": 0,
                    "operation_types": {
                        "vote": 0,
                        "stake": 0,
                        "unstake": 0,
                        "commission_change": 0,
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
                validator_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = validator_extractor.get_results()
            
            # Filter by validator IDs if specified
            if validator_ids:
                results['validator_operations'] = [
                    op for op in results['validator_operations']
                    if op['validator'] in validator_ids
                ]
                
                # Update stats for filtered operations
                filtered_stats = {
                    'total_validator_ops': len(results['validator_operations']),
                    'operation_types': {
                        op_type: sum(1 for op in results['validator_operations']
                                   if op['operation_type'] == op_type)
                        for op_type in ['vote', 'stake', 'unstake', 'commission_change', 'other']
                    },
                    'validator_stats': {
                        validator_id: stats
                        for validator_id, stats in results['stats']['validator_stats'].items()
                        if validator_id in validator_ids
                    }
                }
                results['stats'].update(filtered_stats)
                
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['validator_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "validator_operations": results["validator_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_validator_range: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/validator/{validator_id}")
async def get_validator_details(
    validator_id: str,
    blocks: int = Query(
        default=1000,
        description="Number of recent blocks to analyze",
        ge=1,
        le=10000
    )
) -> Dict[str, Any]:
    """
    Get detailed activity for a specific validator.
    
    Args:
        validator_id: Validator ID to analyze
        blocks: Number of recent blocks to analyze (default: 1000)
        
    Returns:
        Dict containing validator activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        validator_extractor = ValidatorExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing validator {validator_id} over {blocks} blocks")
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
                "validator": None,
                "stats": {
                    "total_operations": 0,
                    "operation_types": {
                        "vote": 0,
                        "stake": 0,
                        "unstake": 0,
                        "commission_change": 0,
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
                validator_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = validator_extractor.get_results()
            
            # Filter operations for this validator
            validator_ops = [
                op for op in results["validator_operations"]
                if op['validator'] == validator_id
            ]
            
            if not validator_ops:
                logger.warning(f"No activity found for validator {validator_id}")
                return {
                    "success": True,
                    "validator": None,
                    "stats": {
                        "total_operations": 0,
                        "operation_types": {
                            "vote": 0,
                            "stake": 0,
                            "unstake": 0,
                            "commission_change": 0,
                            "other": 0
                        }
                    }
                }
                
            # Get validator-specific stats
            validator_stats = results['stats']['validator_stats'].get(validator_id, {})
            
            return {
                "success": True,
                "validator": validator_id,
                "validator_operations": validator_ops,
                "stats": {
                    "total_operations": len(validator_ops),
                    "operation_types": validator_stats.get('operation_types', {}),
                    "stake_accounts": len(validator_stats.get('stake_accounts', set())),
                    "vote_accounts": len(validator_stats.get('vote_accounts', set())),
                    "performance": validator_stats.get('performance', {}),
                    "stake_history": [
                        change for change in results['stats']['stake_stats']['stake_changes']
                        if change['validator'] == validator_id
                    ],
                    "vote_history": [
                        vote for vote in results['stats']['vote_stats']['vote_history']
                        if vote['validator'] == validator_id
                    ]
                },
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_validator_details: {str(e)}")
        return {"success": False, "error": str(e)}
