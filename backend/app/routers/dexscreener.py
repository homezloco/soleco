from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import aiohttp
import os
from datetime import datetime

router = APIRouter(tags=["DexScreener"])

DEXSCREENER_BASE_URL = "https://api.dexscreener.com/latest/dex"

class TokenPair(BaseModel):
    chain_id: str
    dex_id: str
    pair_address: str
    base_token: Dict[str, str]
    quote_token: Dict[str, str]
    price_usd: Optional[float] = None
    price_native: Optional[float] = None
    volume_usd_24h: Optional[float] = None
    liquidity_usd: Optional[float] = None
    fdv: Optional[float] = Field(None, description="Fully Diluted Valuation")
    price_change_percentage_24h: Optional[float] = None

class TokenProfile(BaseModel):
    chain_id: str
    dex_id: str
    pair_address: str
    base_token: Dict[str, str]
    quote_token: Dict[str, str]
    price_usd: Optional[float] = None
    volume_usd_24h: Optional[float] = None
    liquidity_usd: Optional[float] = None
    price_change_percentage_24h: Optional[float] = None
    transactions_24h: Optional[Dict[str, int]] = None
    last_updated: Optional[datetime] = None

class TokenChart(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

class TokenMarketData(BaseModel):
    price_usd: float
    price_change_percentage_24h: float
    volume_usd_24h: float
    liquidity_usd: float
    market_cap: Optional[float] = None
    total_supply: Optional[float] = None
    circulating_supply: Optional[float] = None

class PairAnalytics(BaseModel):
    pair_address: str
    base_token: Dict[str, str]
    quote_token: Dict[str, str]
    price_usd: float
    volume_usd_24h: float
    volume_change_percentage_24h: float
    liquidity_usd: float
    transactions_24h: Dict[str, int]
    price_change_percentage_24h: float

class TokenInsights(BaseModel):
    token_address: str
    symbol: str
    name: str
    market_data: TokenMarketData
    top_pairs: List[PairAnalytics]
    chart_data: List[TokenChart]

async def make_dexscreener_request(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Make a request to DEX Screener API with error handling"""
    try:
        url = f"{DEXSCREENER_BASE_URL}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 429:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                elif response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"DEX Screener API error: {await response.text()}"
                    )
                return await response.json()
                
    except aiohttp.ClientError as e:
        logging.error(f"Error making DEX Screener request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/token/{address}", response_model=List[TokenPair])
async def get_token_pairs(
    address: str,
    chain_id: Optional[str] = Query(default=None, description="Filter by specific chain (e.g., 'solana')")
):
    """
    Get all trading pairs for a specific token.
    Supports filtering by chain ID.
    """
    try:
        params = {"q": address}
        if chain_id:
            params["chain"] = chain_id
        
        response = await make_dexscreener_request("/search", params=params)
        return response.get("pairs", [])
    except Exception as e:
        logging.error(f"Error getting token pairs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pairs/top", response_model=List[TokenProfile])
async def get_top_pairs(
    chain_id: Optional[str] = Query(default="solana", description="Chain ID to filter"),
    sort_by: str = Query(
        default="volume_usd_24h", 
        enum=["volume_usd_24h", "liquidity_usd", "price_change_percentage_24h"]
    ),
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Get top trading pairs sorted by various metrics.
    Defaults to Solana chain and sorting by 24h volume.
    """
    try:
        params = {
            "chain": chain_id,
            "sort": sort_by,
            "limit": limit
        }
        
        response = await make_dexscreener_request("/top/pairs", params=params)
        return response.get("pairs", [])
    except Exception as e:
        logging.error(f"Error getting top pairs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tokens/gainers", response_model=List[TokenProfile])
async def get_top_gainers(
    chain_id: Optional[str] = Query(default="solana", description="Chain ID to filter"),
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Get top token pairs with highest price gains in the last 24h.
    Defaults to Solana chain.
    """
    try:
        params = {
            "chain": chain_id,
            "sort": "price_change_percentage_24h",
            "order": "desc",
            "limit": limit
        }
        
        response = await make_dexscreener_request("/top/pairs", params=params)
        return response.get("pairs", [])
    except Exception as e:
        logging.error(f"Error getting top gainers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/token/{address}/insights", response_model=TokenInsights)
async def get_token_insights(
    address: str,
    chain_id: Optional[str] = Query(default="solana", description="Chain ID")
):
    """
    Get comprehensive insights for a token:
    - Market data
    - Top trading pairs
    - Price chart data
    """
    try:
        # Fetch token pairs
        pairs_response = await make_dexscreener_request("/search", params={"q": address, "chain": chain_id})
        pairs = pairs_response.get("pairs", [])
        
        if not pairs:
            raise HTTPException(status_code=404, detail="Token not found")
        
        # Select primary pair (first pair)
        primary_pair = pairs[0]
        
        # Fetch chart data
        chart_response = await make_dexscreener_request(f"/charts/pair/{primary_pair['pair_address']}")
        chart_data = chart_response.get("chart", [])
        
        return TokenInsights(
            token_address=address,
            symbol=primary_pair['base_token']['symbol'],
            name=primary_pair['base_token']['name'],
            market_data=TokenMarketData(
                price_usd=primary_pair['price_usd'],
                price_change_percentage_24h=primary_pair.get('price_change_percentage_24h', 0),
                volume_usd_24h=primary_pair.get('volume_usd_24h', 0),
                liquidity_usd=primary_pair.get('liquidity_usd', 0)
            ),
            top_pairs=[PairAnalytics(**pair) for pair in pairs[:5]],
            chart_data=[TokenChart(**candle) for candle in chart_data]
        )
    except Exception as e:
        logging.error(f"Error getting token insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tokens/new", response_model=List[TokenProfile])
async def get_new_tokens(
    chain_id: Optional[str] = Query(default="solana", description="Chain ID to filter"),
    limit: int = Query(default=10, ge=1, le=100),
    min_liquidity: float = Query(default=1000, ge=0, description="Minimum liquidity in USD")
):
    """
    Find newly created tokens with minimum liquidity.
    Helps discover potential new trading opportunities.
    """
    try:
        # This is a simulated endpoint as DEX Screener might not have a direct "new tokens" endpoint
        params = {
            "chain": chain_id,
            "sort": "creation_date",
            "order": "desc",
            "min_liquidity": min_liquidity,
            "limit": limit
        }
        
        response = await make_dexscreener_request("/tokens/new", params=params)
        return response.get("tokens", [])
    except Exception as e:
        logging.error(f"Error getting new tokens: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tokens/losers", response_model=List[TokenProfile])
async def get_top_losers(
    chain_id: Optional[str] = Query(default="solana", description="Chain ID to filter"),
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Get top token pairs with highest price drops in the last 24h.
    Helps identify tokens experiencing significant sell pressure.
    """
    try:
        params = {
            "chain": chain_id,
            "sort": "price_change_percentage_24h",
            "order": "asc",
            "limit": limit
        }
        
        response = await make_dexscreener_request("/top/pairs", params=params)
        return response.get("pairs", [])
    except Exception as e:
        logging.error(f"Error getting top losers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/overview")
async def get_market_overview(
    chain_id: Optional[str] = Query(default="solana", description="Chain ID to filter")
):
    """
    Get a comprehensive overview of the DEX market.
    Includes total volume, top tokens, market trends.
    """
    try:
        # Fetch top gainers
        gainers_response = await get_top_gainers(chain_id, limit=5)
        
        # Fetch top losers
        losers_response = await get_top_losers(chain_id, limit=5)
        
        # Fetch total market volume
        top_pairs_response = await get_top_pairs(chain_id, limit=50)
        total_volume = sum(pair.get('volume_usd_24h', 0) for pair in top_pairs_response)
        
        return {
            "chain": chain_id,
            "total_volume_24h": total_volume,
            "top_gainers": gainers_response,
            "top_losers": losers_response,
            "market_sentiment": "bullish" if total_volume > 0 else "bearish"
        }
    except Exception as e:
        logging.error(f"Error getting market overview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
