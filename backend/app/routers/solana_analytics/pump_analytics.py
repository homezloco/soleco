"""
Pump Analytics Module - Handles analysis of pump and dump activities on Solana
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException
from solana.rpc.commitment import Commitment

from app.utils.solana_query import SolanaQueryHandler
from app.utils.handlers.pump_response_handler import PumpResponseHandler
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    tags=["soleco"]
)

@router.get("/activity")
async def get_pump_activity(
    blocks: int = 1000,
    include_transactions: bool = False,
    token_addresses: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get pump and dump activity from recent blocks.
    
    Args:
        blocks: Number of recent blocks to analyze (default: 1000)
        include_transactions: Whether to include transaction details
        token_addresses: Optional list of token addresses to filter by
        
    Returns:
        Dict containing pump and dump activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        pump_extractor = PumpResponseHandler()
        
        # Initialize and get recent blocks
        logger.info(f"Analyzing pump activity from {blocks} recent blocks")
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
                "pump_operations": [],
                "stats": {
                    "total_pump_indicators": 0,
                    "indicator_types": {
                        "volume_spike": 0,
                        "price_spike": 0,
                        "holder_concentration": 0,
                        "wash_trading": 0,
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
                pump_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = pump_extractor.get_results()
            logger.info(f"Found {results['stats']['total_pump_indicators']} pump indicators")
            
            # Filter by token addresses if specified
            if token_addresses:
                results['pump_operations'] = [
                    op for op in results['pump_operations']
                    if op['token'] in token_addresses
                ]
                
                # Update stats for filtered operations
                filtered_stats = {
                    'total_pump_indicators': sum(
                        len(op['indicators'])
                        for op in results['pump_operations']
                    ),
                    'indicator_types': {
                        indicator: sum(
                            1 for op in results['pump_operations']
                            if indicator in op['indicators']
                        )
                        for indicator in [
                            'volume_spike',
                            'price_spike',
                            'holder_concentration',
                            'wash_trading',
                            'other'
                        ]
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
                for op in results['pump_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "pump_operations": results["pump_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_pump_activity: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/range")
async def get_pump_range(
    start_slot: int,
    end_slot: int,
    include_transactions: bool = False,
    token_addresses: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get pump and dump activity for a range of slots.
    
    Args:
        start_slot: Starting slot number
        end_slot: Ending slot number
        include_transactions: Whether to include transaction details
        token_addresses: Optional list of token addresses to filter by
        
    Returns:
        Dict containing pump and dump activity analysis for the slot range
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        pump_extractor = PumpResponseHandler()
        
        # Initialize and get blocks
        logger.info(f"Analyzing pump activity from slot {start_slot} to {end_slot}")
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
                "pump_operations": [],
                "stats": {
                    "total_pump_indicators": 0,
                    "indicator_types": {
                        "volume_spike": 0,
                        "price_spike": 0,
                        "holder_concentration": 0,
                        "wash_trading": 0,
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
                pump_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = pump_extractor.get_results()
            
            # Filter by token addresses if specified
            if token_addresses:
                results['pump_operations'] = [
                    op for op in results['pump_operations']
                    if op['token'] in token_addresses
                ]
                
                # Update stats for filtered operations
                filtered_stats = {
                    'total_pump_indicators': sum(
                        len(op['indicators'])
                        for op in results['pump_operations']
                    ),
                    'indicator_types': {
                        indicator: sum(
                            1 for op in results['pump_operations']
                            if indicator in op['indicators']
                        )
                        for indicator in [
                            'volume_spike',
                            'price_spike',
                            'holder_concentration',
                            'wash_trading',
                            'other'
                        ]
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
                for op in results['pump_operations']:
                    if 'transaction' in op:
                        del op['transaction']
                        
            return {
                "success": True,
                "pump_operations": results["pump_operations"],
                "stats": results["stats"],
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_pump_range: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/token/{token_address}")
async def get_pump_details(
    token_address: str,
    blocks: int = 10000
) -> Dict[str, Any]:
    """
    Get detailed pump and dump activity for a specific token.
    
    Args:
        token_address: Token address to analyze
        blocks: Number of recent blocks to analyze (default: 10000)
        
    Returns:
        Dict containing pump and dump activity analysis
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        pump_extractor = PumpResponseHandler()
        
        # Initialize and get recent blocks
        logger.info(f"Analyzing pump activity for token {token_address} over {blocks} blocks")
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
                    "total_indicators": 0,
                    "indicator_types": {
                        "volume_spike": 0,
                        "price_spike": 0,
                        "holder_concentration": 0,
                        "wash_trading": 0,
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
                pump_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
                
        # Get results
        try:
            results = pump_extractor.get_results()
            
            # Filter operations for this token
            token_ops = [
                op for op in results["pump_operations"]
                if op['token'] == token_address
            ]
            
            if not token_ops:
                logger.warning(f"No pump activity found for token {token_address}")
                return {
                    "success": True,
                    "token": None,
                    "stats": {
                        "total_indicators": 0,
                        "indicator_types": {
                            "volume_spike": 0,
                            "price_spike": 0,
                            "holder_concentration": 0,
                            "wash_trading": 0,
                            "other": 0
                        }
                    }
                }
                
            # Get token-specific stats
            token_stats = results['stats']['token_stats'].get(token_address, {})
            
            return {
                "success": True,
                "token": token_address,
                "pump_operations": token_ops,
                "stats": {
                    "total_indicators": sum(len(op['indicators']) for op in token_ops),
                    "indicator_types": token_stats.get('indicators', {}),
                    "volume_stats": {
                        "total_volume": token_stats.get('total_volume', 0),
                        "volume_history": token_stats.get('volume_history', []),
                        "volume_spikes": [
                            spike for spike in results['stats']['volume_stats']['volume_spikes']
                            if spike['token'] == token_address
                        ]
                    },
                    "price_stats": {
                        "price_history": token_stats.get('price_history', []),
                        "price_spikes": [
                            spike for spike in results['stats']['price_stats']['price_spikes']
                            if spike['token'] == token_address
                        ]
                    },
                    "trading_stats": {
                        "total_trades": token_stats.get('total_trades', 0),
                        "unique_traders": token_stats.get('unique_traders', 0),
                        "wash_trading_indicators": [
                            indicator
                            for indicator in results['stats']['trading_stats']['wash_trading_indicators']
                            if indicator['token'] == token_address
                        ]
                    }
                },
                "blocks_processed": len(blocks_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting results: {str(e)}")
            return {"success": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"Error in get_pump_details: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/new")
async def detect_new_pumps(
    blocks: int = 1,
    min_volume_change: float = 200.0,  # 200% volume increase
    min_price_change: float = 20.0,    # 20% price increase
    min_transactions: int = 3          # Minimum transactions to consider
) -> Dict[str, Any]:
    """
    Detect new pump activities from very recent blocks.
    
    Args:
        blocks: Number of most recent blocks to analyze (default: 1)
        min_volume_change: Minimum volume increase percentage to flag (default: 200%)
        min_price_change: Minimum price increase percentage to flag (default: 20%)
        min_transactions: Minimum number of transactions to consider (default: 3)
        
    Returns:
        Dict containing newly detected pump activities
    """
    try:
        # Initialize handlers
        query_handler = SolanaQueryHandler()
        pump_extractor = PumpResponseHandler()
        
        # Configure pump detection parameters
        pump_extractor.configure_detection(
            min_volume_change=min_volume_change,
            min_price_change=min_price_change,
            min_transactions=min_transactions
        )
        
        # Get recent blocks
        logger.info(f"Analyzing {blocks} most recent blocks for new pump activities")
        blocks_data = await query_handler.process_blocks(blocks)
        
        if not blocks_data or not blocks_data.get("success"):
            error = blocks_data.get("error", "Failed to get blocks data")
            logger.error(f"Error getting blocks data: {error}")
            return {
                "success": False,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        blocks_list = blocks_data.get("blocks", [])
        if not blocks_list:
            logger.warning("No blocks found in blocks_data")
            return {
                "success": True,
                "new_pumps": [],
                "stats": {
                    "blocks_processed": 0,
                    "transactions_analyzed": 0,
                    "tokens_monitored": 0
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Process blocks for pump detection
        transactions_analyzed = 0
        for block in blocks_list:
            try:
                if not block:
                    continue
                    
                transactions = block.get('transactions', [])
                transactions_analyzed += len(transactions)
                logger.debug(f"Processing block with {len(transactions)} transactions")
                pump_extractor.process_block(block)
                
            except Exception as e:
                logger.error(f"Error processing block: {str(e)}")
                continue
        
        # Get pump detection results
        results = pump_extractor.get_results()
        
        # Filter and format pump activities
        new_pumps = []
        for pump in results.get('pump_operations', []):
            # Only include pumps that meet our thresholds
            if (pump['volume_change_pct'] >= min_volume_change or 
                pump['price_change_pct'] >= min_price_change) and \
                pump['transaction_count'] >= min_transactions:
                
                new_pumps.append({
                    'token_address': pump['token'],
                    'token_name': pump.get('token_name', 'Unknown'),
                    'volume_change_pct': pump['volume_change_pct'],
                    'price_change_pct': pump['price_change_pct'],
                    'transaction_count': pump['transaction_count'],
                    'detected_at': datetime.utcnow().isoformat(),
                    'confidence_score': pump.get('confidence_score', 0),
                    'indicators': pump.get('indicators', []),
                    'recent_transactions': pump.get('recent_transactions', [])[:5]  # Last 5 transactions
                })
        
        response = {
            "success": True,
            "new_pumps": new_pumps,
            "stats": {
                "blocks_processed": len(blocks_list),
                "transactions_analyzed": transactions_analyzed,
                "tokens_monitored": len(results.get('monitored_tokens', [])),
                "detection_thresholds": {
                    "min_volume_change": min_volume_change,
                    "min_price_change": min_price_change,
                    "min_transactions": min_transactions
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Detected {len(new_pumps)} new pump activities")
        return response
        
    except Exception as e:
        logger.error(f"Error in detect_new_pumps: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
