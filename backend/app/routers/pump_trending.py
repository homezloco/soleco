"""
Pump Trending Router - Handles trending pump token analytics
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
import logging
import random

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/pump",
    tags=["pump", "analytics"]
)

@router.get("/trending")
async def get_trending_pump_tokens(
    timeframe: str = Query(
        default="24h",
        description="Time period for trending data",
        regex="^(1h|24h|7d)$"
    ),
    sort_by: str = Query(
        default="volume",
        description="Metric to sort by",
        regex="^(volume|price_change|holders)$"
    ),
    limit: int = Query(
        default=10,
        description="Maximum number of tokens to return",
        ge=1,
        le=50
    )
) -> Dict[str, Any]:
    """
    Get trending pump tokens based on various metrics.
    
    Args:
        timeframe: Time period for trending data (1h, 24h, 7d)
        sort_by: Metric to sort by (volume, price_change, holders)
        limit: Maximum number of tokens to return
        
    Returns:
        Dict containing trending pump tokens
    """
    try:
        # In a real implementation, this would query a database or other data source
        # For now, we'll generate mock data
        tokens = generate_mock_pump_tokens(limit, timeframe, sort_by)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "tokens": tokens
        }
    except Exception as e:
        logger.error(f"Error getting trending pump tokens: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trending pump tokens: {str(e)}"
        )

def generate_mock_pump_tokens(limit: int, timeframe: str, sort_by: str) -> List[Dict[str, Any]]:
    """Generate mock pump token data for testing"""
    tokens = []
    
    # Define timeframe multipliers for price changes
    multipliers = {
        "1h": 1,
        "24h": 5,
        "7d": 15
    }
    
    multiplier = multipliers.get(timeframe, 1)
    
    # Generate random tokens
    for i in range(limit):
        # Create more realistic token names with "pump" suffix
        name_options = [
            f"Rocket{i}Pump", f"Moon{i}Pump", f"Lambo{i}Pump", 
            f"Diamond{i}Pump", f"Degen{i}Pump", f"Pepe{i}Pump",
            f"Solana{i}Pump", f"Meme{i}Pump", f"Ape{i}Pump"
        ]
        name = random.choice(name_options)
        symbol = name.replace("Pump", "").upper()
        
        # Generate creation time within the timeframe
        hours_ago = 1
        if timeframe == "24h":
            hours_ago = random.randint(1, 24)
        elif timeframe == "7d":
            hours_ago = random.randint(1, 168)  # 7 days in hours
            
        created_at = (datetime.now() - timedelta(hours=hours_ago)).isoformat()
        
        # Generate metrics with some correlation to make it more realistic
        # Higher volume tends to correlate with higher price changes and holder count
        base_volume = random.uniform(100, 10000)
        volume_factor = random.uniform(0.8, 1.2)  # Add some randomness
        volume_24h = base_volume * volume_factor
        
        price_change_factor = random.uniform(0.5, 1.5)  # Add some randomness
        price_change_24h = (random.uniform(5, 50) * multiplier * price_change_factor) * (1 if random.random() > 0.3 else -1)
        
        holder_factor = random.uniform(0.7, 1.3)  # Add some randomness
        holder_count = int(base_volume / 100 * holder_factor)
        
        # Ensure minimum values
        holder_count = max(10, holder_count)
        volume_24h = max(100, volume_24h)
        
        token = {
            "address": f"pump{i}{random.randint(10000, 99999)}",
            "name": name,
            "symbol": symbol,
            "price": round(random.uniform(0.0001, 0.1), 6),
            "price_change_24h": round(price_change_24h, 2),
            "volume_24h": round(volume_24h, 2),
            "holder_count": holder_count,
            "created_at": created_at
        }
        tokens.append(token)
    
    # Sort based on the requested metric
    if sort_by == "volume":
        tokens.sort(key=lambda x: x["volume_24h"], reverse=True)
    elif sort_by == "price_change":
        tokens.sort(key=lambda x: abs(x["price_change_24h"]), reverse=True)
    elif sort_by == "holders":
        tokens.sort(key=lambda x: x["holder_count"], reverse=True)
    
    return tokens
