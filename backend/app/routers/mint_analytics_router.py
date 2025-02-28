"""
FastAPI router for mint analytics endpoints.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException
import logging
from datetime import datetime, timezone
import time

from .solana_new_mints_extractor import NewMintAnalyzer
from ..utils.solana_query import SolanaQueryHandler
from ..utils.solana_response import SolanaResponseManager
from ..utils.solana_types import EndpointConfig

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(
    prefix="/analytics/mints",
    tags=["analytics", "mints"]
)

# Initialize components
endpoint_config = EndpointConfig(
    url="https://api.mainnet-beta.solana.com",
    requests_per_second=5.0,
    burst_limit=10,
    max_retries=3,
    retry_delay=2.0
)

@router.get("/recent")
async def get_recent_mints(
    blocks: int = Query(
        default=5,
        description="Number of recent blocks to analyze",
        ge=1,
        le=20
    )
) -> Dict[str, Any]:
    """Get newly created mint addresses from recent blocks"""
    try:
        # Initialize analyzer
        analyzer = NewMintAnalyzer()
        
        # Get latest block
        response_manager = SolanaResponseManager(endpoint_config)
        query_handler = SolanaQueryHandler(response_manager)
        latest_block = await query_handler.get_latest_block()
        
        if not latest_block:
            raise HTTPException(status_code=503, detail="Failed to get latest block")
            
        # Calculate block range
        start_block = latest_block['slot']
        end_block = max(0, start_block - blocks + 1)
        
        # Process blocks
        results = []
        for slot in range(start_block, end_block - 1, -1):
            block_data = await query_handler.get_block(slot)
            if block_data:
                result = await analyzer.process_block(block_data)
                if result['success']:
                    results.append(result)
                    
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "block_range": {
                "start": start_block,
                "end": end_block
            },
            "results": results,
            "summary": {
                "total_blocks": len(results),
                "total_mints": sum(len(r['mint_addresses']) for r in results if r['success']),
                "total_pump_tokens": sum(len(r['pump_token_addresses']) for r in results if r['success'])
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting recent mints: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/analyze/{mint_address}")
async def analyze_mint(
    mint_address: str,
    include_history: bool = Query(
        default=False,
        description="Include transaction history"
    )
) -> Dict[str, Any]:
    """Analyze a specific mint address"""
    try:
        # Initialize analyzer
        analyzer = NewMintAnalyzer()
        
        # Get mint info
        response_manager = SolanaResponseManager(endpoint_config)
        query_handler = SolanaQueryHandler(response_manager)
        
        mint_info = await query_handler.get_token_supply(mint_address)
        if not mint_info:
            raise HTTPException(status_code=404, detail="Mint address not found")
            
        # Get metadata if available
        metadata = await query_handler.get_token_metadata(mint_address)
        
        # Analyze for pump characteristics
        pump_analysis = analyzer.pump_detector.analyze_token(
            mint_address,
            metadata=metadata if metadata else None
        )
        
        result = {
            "success": True,
            "mint_address": mint_address,
            "supply": mint_info.get('amount'),
            "decimals": mint_info.get('decimals'),
            "metadata": metadata if metadata else None,
            "pump_analysis": pump_analysis,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Include transaction history if requested
        if include_history:
            history = await query_handler.get_token_largest_accounts(mint_address)
            if history:
                result['history'] = history
                
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing mint {mint_address}: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))

@router.get("/stats")
async def get_mint_statistics(
    timeframe: str = Query(
        default="24h",
        description="Timeframe for statistics (1h, 24h, 7d)",
        regex="^(1h|24h|7d)$"
    )
) -> Dict[str, Any]:
    """Get mint creation statistics for a specific timeframe"""
    try:
        # Initialize analyzer
        analyzer = NewMintAnalyzer()
        
        # Calculate time range
        now = int(time.time())
        if timeframe == "1h":
            start_time = now - 3600
        elif timeframe == "24h":
            start_time = now - 86400
        else:  # 7d
            start_time = now - 604800
            
        # Get blocks in time range
        response_manager = SolanaResponseManager(endpoint_config)
        query_handler = SolanaQueryHandler(response_manager)
        
        blocks = await query_handler.get_blocks_in_time_range(start_time, now)
        if not blocks:
            raise HTTPException(status_code=503, detail="Failed to get blocks")
            
        # Process blocks
        results = []
        for block in blocks:
            block_data = await query_handler.get_block(block)
            if block_data:
                result = await analyzer.process_block(block_data)
                if result['success']:
                    results.append(result)
                    
        # Calculate statistics
        total_mints = sum(len(r['mint_addresses']) for r in results if r['success'])
        total_pump = sum(len(r['pump_token_addresses']) for r in results if r['success'])
        
        return {
            "success": True,
            "timeframe": timeframe,
            "range": {
                "start": start_time,
                "end": now
            },
            "statistics": {
                "total_blocks_analyzed": len(results),
                "total_new_mints": total_mints,
                "total_pump_tokens": total_pump,
                "mints_per_hour": (total_mints * 3600) / (now - start_time),
                "pump_ratio": total_pump / total_mints if total_mints > 0 else 0
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting mint statistics: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))
