"""
Token Analytics Module - Handles analysis of token activities on Solana
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Query, HTTPException
from ..utils.solana_query import SolanaQueryHandler
from ..utils.handlers.token_extractor import TokenExtractor
from ..utils.logging_config import setup_logging

# Configure logging
logger = setup_logging(__name__)

# Create router
router = APIRouter(
    tags=["soleco"]
)

@router.get("/activity")
async def get_token_activity(
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
    token_addresses: Optional[List[str]] = Query(
        default=None,
        description="Optional list of token addresses to filter by"
    )
) -> Dict[str, Any]:
    """
    Get token activity from recent blocks.
    
    Args:
        blocks: Number of recent blocks to analyze (default: 100)
        include_transactions: Whether to include transaction details
        token_addresses: Optional list of token addresses to filter by
        
    Returns:
        Dict containing token activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        token_extractor = TokenExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing token activity from {blocks} recent blocks")
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
                "token_operations": [],
                "stats": {
                    "total_token_ops": 0,
                    "operation_types": {
                        "transfer": 0,
                        "mint": 0,
                        "burn": 0,
                        "freeze": 0,
                        "thaw": 0,
                        "approve": 0,
                        "revoke": 0,
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
                token_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = token_extractor.get_results()
            logger.info(f"Found {results['stats']['total_token_ops']} token operations")
            
            # Filter by token addresses if specified
            if token_addresses:
                results['token_operations'] = [
                    op for op in results['token_operations']
                    if op['token'] in token_addresses
                ]
                
                # Update stats for filtered operations
                filtered_stats = {
                    'total_token_ops': len(results['token_operations']),
                    'operation_types': {
                        op_type: sum(1 for op in results['token_operations']
                                   if op['operation_type'] == op_type)
                        for op_type in ['transfer', 'mint', 'burn', 'freeze', 'thaw', 'approve', 'revoke', 'other']
                    },
                    'token_stats': {
                        token: stats
                        for token, stats in results['stats']['token_stats'].items()
                        if token in token_addresses
                    }
                }
                results['stats'].update(filtered_stats)
                
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['token_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "token_operations": results["token_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_token_activity: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/range")
async def get_token_range(
    start_slot: int = Query(..., description="Starting slot number"),
    end_slot: int = Query(..., description="Ending slot number"),
    include_transactions: bool = Query(
        default=False,
        description="Include transaction details in response"
    ),
    token_addresses: Optional[List[str]] = Query(
        default=None,
        description="Optional list of token addresses to filter by"
    )
) -> Dict[str, Any]:
    """
    Get token activity for a range of slots.
    
    Args:
        start_slot: Starting slot number
        end_slot: Ending slot number
        include_transactions: Whether to include transaction details
        token_addresses: Optional list of token addresses to filter by
        
    Returns:
        Dict containing token activity analysis for the slot range
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        token_extractor = TokenExtractor()
        
        # Initialize and get blocks
        await query_handler.initialize()
        logger.info(f"Analyzing token activity from slot {start_slot} to {end_slot}")
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
                "token_operations": [],
                "stats": {
                    "total_token_ops": 0,
                    "operation_types": {
                        "transfer": 0,
                        "mint": 0,
                        "burn": 0,
                        "freeze": 0,
                        "thaw": 0,
                        "approve": 0,
                        "revoke": 0,
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
                token_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = token_extractor.get_results()
            
            # Filter by token addresses if specified
            if token_addresses:
                results['token_operations'] = [
                    op for op in results['token_operations']
                    if op['token'] in token_addresses
                ]
                
                # Update stats for filtered operations
                filtered_stats = {
                    'total_token_ops': len(results['token_operations']),
                    'operation_types': {
                        op_type: sum(1 for op in results['token_operations']
                                   if op['operation_type'] == op_type)
                        for op_type in ['transfer', 'mint', 'burn', 'freeze', 'thaw', 'approve', 'revoke', 'other']
                    },
                    'token_stats': {
                        token: stats
                        for token, stats in results['stats']['token_stats'].items()
                        if token in token_addresses
                    }
                }
                results['stats'].update(filtered_stats)
                
            # Remove transaction details if not requested
            if not include_transactions:
                for op in results['token_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "token_operations": results["token_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_token_range: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/token/{token_address}")
async def get_token_details(
    token_address: str,
    blocks: int = Query(
        default=1000,
        description="Number of recent blocks to analyze",
        ge=1,
        le=10000
    )
) -> Dict[str, Any]:
    """
    Get detailed activity for a specific token.
    
    Args:
        token_address: Token address to analyze
        blocks: Number of recent blocks to analyze (default: 1000)
        
    Returns:
        Dict containing token activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        token_extractor = TokenExtractor()
        
        # Initialize and get recent blocks
        await query_handler.initialize()
        logger.info(f"Analyzing token {token_address} over {blocks} blocks")
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
                "token": None,
                "stats": {
                    "total_operations": 0,
                    "operation_types": {
                        "transfer": 0,
                        "mint": 0,
                        "burn": 0,
                        "freeze": 0,
                        "thaw": 0,
                        "approve": 0,
                        "revoke": 0,
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
                token_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = token_extractor.get_results()
            
            # Filter operations for this token
            token_ops = [
                op for op in results["token_operations"]
                if op['token'] == token_address
            ]
            
            if not token_ops:
                logger.warning(f"No activity found for token {token_address}")
                return {
                    "success": True,
                    "token": None,
                    "stats": {
                        "total_operations": 0,
                        "operation_types": {
                            "transfer": 0,
                            "mint": 0,
                            "burn": 0,
                            "freeze": 0,
                            "thaw": 0,
                            "approve": 0,
                            "revoke": 0,
                            "other": 0
                        }
                    }
                }
                
            # Get token-specific stats
            token_stats = results['stats']['token_stats'].get(token_address, {})
            
            return {
                "success": True,
                "token": token_address,
                "token_operations": token_ops,
                "stats": {
                    "total_operations": len(token_ops),
                    "operation_types": token_stats.get('operation_types', {}),
                    "total_volume": token_stats.get('total_volume', 0),
                    "holders": token_stats.get('holders', 0),
                    "supply": token_stats.get('supply', 0),
                    "mint_authority": token_stats.get('mint_authority'),
                    "freeze_authority": token_stats.get('freeze_authority'),
                    "transfer_history": [
                        transfer for transfer in results['stats']['transfer_stats']['transfer_history']
                        if transfer['token'] == token_address
                    ],
                    "supply_changes": [
                        change for change in results['stats']['mint_stats']['total_supply_changes']
                        if change['token'] == token_address
                    ]
                },
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_token_details: {str(e)}")
        return {"success": False, "error": str(e)}
