from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import RedirectResponse
import httpx
from pydantic import BaseModel
import logging
from datetime import datetime, timedelta
import asyncio
from app.database.sqlite import DatabaseCache

router = APIRouter(tags=["PumpFun"])

PUMP_API_BASE_URL = "https://frontend-api.pump.fun"

class PumpToken(BaseModel):
    mint: str
    name: Optional[str] = None
    symbol: Optional[str] = None
    description: Optional[str] = None
    image_uri: Optional[str] = None
    video_uri: Optional[str] = None
    metadata_uri: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    bonding_curve: Optional[str] = None
    associated_bonding_curve: Optional[str] = None
    creator: Optional[str] = None
    created_timestamp: Optional[int] = None
    raydium_pool: Optional[str] = None
    complete: Optional[bool] = False
    virtual_sol_reserves: Optional[int] = 0
    virtual_token_reserves: Optional[int] = 0
    total_supply: Optional[int] = 0
    website: Optional[str] = None
    show_name: Optional[bool] = True
    king_of_the_hill_timestamp: Optional[int] = None
    market_cap: Optional[float] = 0
    reply_count: Optional[int] = 0
    last_reply: Optional[int] = None
    nsfw: Optional[bool] = False
    market_id: Optional[str] = None
    inverted: Optional[bool] = False
    is_currently_live: Optional[bool] = False
    username: Optional[str] = None
    profile_image: Optional[str] = None
    usd_market_cap: Optional[float] = 0
    hidden: Optional[bool] = False
    last_trade_timestamp: Optional[int] = None
    real_sol_reserves: Optional[int] = 0
    livestream_ban_expiry: Optional[int] = 0
    is_banned: Optional[bool] = False
    initialized: Optional[bool] = True
    updated_at: Optional[int] = None
    real_token_reserves: Optional[int] = 0

class Trade(BaseModel):
    signature: Optional[str] = None
    mint: Optional[str] = None
    sol_amount: Optional[int] = 0
    token_amount: Optional[int] = 0
    is_buy: Optional[bool] = False
    user: Optional[str] = None
    timestamp: Optional[int] = None
    symbol: Optional[str] = None
    image_uri: Optional[str] = None
    slot: Optional[int] = 0

class SolPrice(BaseModel):
    price: Optional[float] = 0
    last_updated: Optional[int] = 0

class TokenAnalytics(BaseModel):
    token: Optional[PumpToken] = None
    trade_count: Optional[int] = 0
    price_data: Optional[List[Dict[str, Any]]] = []
    sol_price: Optional[float] = 0
    usd_price: Optional[float] = 0
    volume_24h: Optional[float] = 0
    market_cap_usd: Optional[float] = 0

class MarketOverview(BaseModel):
    king_of_the_hill: Optional[List[PumpToken]] = []
    latest_tokens: Optional[List[PumpToken]] = []
    sol_price: Optional[float] = 0
    total_tokens_tracked: Optional[int] = 0
    total_volume_24h: Optional[float] = 0

class Candlestick(BaseModel):
    mint: Optional[str] = None
    timestamp: Optional[int] = 0
    open: Optional[float] = 0
    high: Optional[float] = 0
    low: Optional[float] = 0
    close: Optional[float] = 0
    volume: Optional[float] = 0
    slot: Optional[int] = 0
    is_5_min: Optional[bool] = False
    is_1_min: Optional[bool] = False

async def validate_token_exists(mint: str) -> bool:
    """Validate that a token exists and is accessible."""
    try:
        # Try to get the token details
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PUMP_API_BASE_URL}/coins/{mint}", headers={"accept": "*/*"})
            return response.status_code == 200
    except:
        return False

async def make_http_request(url: str, required: bool = True) -> dict:
    """Make HTTP request to Pump.fun API."""
    max_retries = 3
    retry_delay = 2  # seconds
    
    for retry in range(max_retries):
        try:
            logging.info(f"Making request to: {url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers={"accept": "*/*"}, timeout=30.0)
                logging.info(f"Response status: {response.status_code}")
                
                if response.status_code == 404:
                    if required:
                        raise HTTPException(status_code=404, detail="Resource not found")
                    return None
                elif response.status_code == 429:
                    # Rate limited, wait and retry
                    if retry < max_retries - 1:
                        wait_time = retry_delay * (retry + 1)
                        logging.warning(f"Rate limited. Waiting {wait_time}s before retry {retry + 1}/{max_retries}")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logging.error(f"Rate limited after {max_retries} retries")
                        if required:
                            raise HTTPException(status_code=429, detail="Rate limited by Pump.fun API")
                        return None
                elif response.status_code == 500:
                    if required:
                        raise HTTPException(status_code=502, detail="Pump.fun API error")
                    return None
                    
                response.raise_for_status()
                data = response.json()
                return data
        except httpx.HTTPError as e:
            logging.error(f"HTTP error occurred while fetching from Pump.fun: {e}")
            if retry < max_retries - 1 and "timeout" in str(e).lower():
                # Retry on timeout
                wait_time = retry_delay * (retry + 1)
                logging.warning(f"Request timed out. Waiting {wait_time}s before retry {retry + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                continue
            if required:
                raise HTTPException(status_code=502, detail=f"Error fetching data from Pump.fun: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error occurred while fetching from Pump.fun: {e}")
            if required:
                raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
            return None
    
    # If we get here, all retries failed
    if required:
        raise HTTPException(status_code=503, detail="Failed to fetch data after multiple retries")
    return None

@router.get("/coins/latest", response_model=List[PumpToken])
async def get_latest_tokens(qty: int = Query(default=1, ge=1, le=50, description="Number of latest tokens to retrieve")):
    """Get the latest tokens from Pump.fun. Returns up to 50 most recent tokens."""
    try:
        logging.info(f"Getting {qty} latest tokens")
        # First get the latest token to get its timestamp
        latest_token = await make_http_request(f"{PUMP_API_BASE_URL}/coins/latest")
        tokens = [latest_token]
        
        # If qty > 1, make additional requests with before parameter
        if qty > 1:
            before_timestamp = latest_token['created_timestamp']
            for i in range(qty - 1):
                try:
                    logging.info(f"Fetching token {i+2} of {qty} with timestamp {before_timestamp}")
                    next_token = await make_http_request(f"{PUMP_API_BASE_URL}/coins/latest?before={before_timestamp}")
                    if not next_token:
                        logging.warning("No more tokens available")
                        break
                    tokens.append(next_token)
                    before_timestamp = next_token['created_timestamp']
                except Exception as e:
                    logging.warning(f"Error fetching additional token: {e}")
                    break

        logging.info(f"Retrieved {len(tokens)} latest tokens from Pump.fun")
        return tokens
    except Exception as e:
        logging.error(f"Error getting latest tokens from Pump.fun: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades/latest", response_model=List[Trade])
async def get_latest_trades(
    qty: int = Query(default=1, ge=1, le=15, description="Number of latest trades to retrieve"),
    include_nsfw: bool = Query(default=True, description="Whether to include NSFW tokens"),
    include_all: bool = Query(default=True, description="Whether to include all tokens")
):
    """Get the latest trades from Pump.fun. Returns up to 15 most recent trades."""
    try:
        logging.info(f"Getting {qty} latest trades with include_nsfw={include_nsfw}, include_all={include_all}")
        
        # Make separate requests for each trade
        trades = []
        seen_signatures = set()
        duplicate_count = 0
        max_duplicates = 5  # Maximum number of consecutive duplicates before trying a different approach
        
        for i in range(qty):
            try:
                # Add a small delay between requests to avoid rate limiting and get different trades
                if i > 0:
                    await asyncio.sleep(0.5)  # 500ms delay
                
                logging.info(f"Fetching trade {i+1} of {qty}")
                trade = await make_http_request(
                    f"{PUMP_API_BASE_URL}/trades/latest?includeNsfw={'true' if include_nsfw else 'false'}&includeAll={'true' if include_all else 'false'}"
                )
                
                # Only add the trade if we haven't seen its signature before
                signature = trade.get('signature')
                if signature and signature not in seen_signatures:
                    seen_signatures.add(signature)
                    trades.append(trade)
                    logging.info(f"Added trade with signature: {signature}")
                    duplicate_count = 0  # Reset duplicate counter
                elif signature:
                    logging.info(f"Skipping duplicate trade with signature: {signature}")
                    duplicate_count += 1
                    
                    # If we've seen too many duplicates, try a different approach
                    if duplicate_count >= max_duplicates:
                        logging.warning(f"Too many duplicate trades ({duplicate_count}). Trying a different approach.")
                        break
                    
                    # Try to get a different trade by waiting a bit longer
                    await asyncio.sleep(1)  # Wait an additional second
                    continue
                else:
                    # Include trades without signatures (shouldn't happen, but just in case)
                    trades.append(trade)
                    duplicate_count = 0  # Reset duplicate counter
                    
            except Exception as e:
                logging.warning(f"Error fetching trade {i+1}: {e}")
                continue
        
        # If we didn't get enough trades or had too many duplicates, try a different approach
        if len(trades) < qty and duplicate_count >= max_duplicates:
            logging.info(f"Only got {len(trades)} trades with too many duplicates. Trying to fetch all trades at once.")
            
            # Try to get all trades at once using a different endpoint
            try:
                all_trades = await make_http_request(
                    f"{PUMP_API_BASE_URL}/trades?includeNsfw={'true' if include_nsfw else 'false'}&includeAll={'true' if include_all else 'false'}&limit={qty}"
                )
                
                if isinstance(all_trades, list) and len(all_trades) > 0:
                    # Deduplicate based on signature
                    unique_trades = []
                    seen_sigs = set()
                    
                    for trade in all_trades:
                        sig = trade.get('signature')
                        if sig and sig not in seen_sigs:
                            seen_sigs.add(sig)
                            unique_trades.append(trade)
                    
                    # Only use these trades if we got more than we had before
                    if len(unique_trades) > len(trades):
                        logging.info(f"Got {len(unique_trades)} trades from alternative endpoint. Using these instead.")
                        return unique_trades[:qty]  # Limit to requested quantity
            except Exception as e:
                logging.warning(f"Error fetching trades from alternative endpoint: {e}")

        logging.info(f"Retrieved {len(trades)} unique trades from Pump.fun")
        return trades
    except Exception as e:
        logging.error(f"Error getting latest trades from Pump.fun: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/coins/king-of-the-hill", response_model=Optional[PumpToken])
async def get_king_of_the_hill(
    include_nsfw: bool = Query(default=True, description="Whether to include NSFW tokens")
):
    """Get the current King of the Hill token from Pump.fun."""
    try:
        logging.info(f"Getting king of the hill token with include_nsfw={include_nsfw}")
        response = await make_http_request(
            f"{PUMP_API_BASE_URL}/coins/king-of-the-hill?includeNsfw={'true' if include_nsfw else 'false'}",
            required=False
        )
        
        if not response:
            logging.info("No king of the hill token found")
            return None
            
        logging.info(f"Retrieved king of the hill token from Pump.fun: {response.get('symbol')}")
        return response
    except Exception as e:
        logging.error(f"Error getting king of the hill token from Pump.fun: {e}", exc_info=True)
        return None

@router.get("/king-of-the-hill", response_model=Optional[PumpToken])
async def get_king_of_the_hill_legacy(
    include_nsfw: bool = Query(default=True, description="Whether to include NSFW tokens")
):
    """Legacy endpoint for backward compatibility. Redirects to the correct endpoint."""
    logging.warning("Legacy king-of-the-hill endpoint called. This should be updated to use /coins/king-of-the-hill")
    return await get_king_of_the_hill(include_nsfw)

@router.get("/search", response_model=List[PumpToken])
async def search_tokens(
    query: str = Query(..., min_length=1, description="Search query for token name or symbol"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of results to return"),
    include_nsfw: bool = Query(default=False, description="Whether to include NSFW tokens")
):
    """Search for tokens by name or symbol."""
    try:
        logging.info(f"Searching for tokens with query '{query}' and limit {limit} and include_nsfw={include_nsfw}")
        response = await make_http_request(
            f"{PUMP_API_BASE_URL}/coins/search?q={query}&limit={limit}&includeNsfw={'true' if include_nsfw else 'false'}"
        )
        logging.info(f"Found {len(response)} tokens matching query '{query}'")
        return response
    except Exception as e:
        logging.error(f"Error searching for tokens with query '{query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sol-price", response_model=SolPrice)
async def get_sol_price():
    """Get current SOL price."""
    try:
        response = await make_http_request(f"{PUMP_API_BASE_URL}/sol-price")
        # Transform the response to match our model
        if response and "solPrice" in response:
            return {
                "price": response["solPrice"],
                "last_updated": int(datetime.now().timestamp())
            }
        return {"price": 0, "last_updated": 0}
    except Exception as e:
        logging.error(f"Error getting SOL price: {e}", exc_info=True)
        return {"price": 0, "last_updated": 0}

@router.get("/candlesticks/{mint}", response_model=List[Candlestick])
async def get_candlesticks(
    mint: str,
    interval: str = Query(default="1h", description="Candlestick interval (e.g., '1h', '4h', '1d')")
):
    """Get candlestick data for a specific token"""
    try:
        candlesticks = await make_http_request(
            f"{PUMP_API_BASE_URL}/candlesticks/{mint}?interval={interval}",
            required=False
        )
        return candlesticks if candlesticks else []
    except Exception as e:
        logging.error(f"Error getting candlesticks for {mint}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades/all/{mint}", response_model=List[Trade])
async def get_all_trades(
    mint: str,
    limit: int = Query(default=50, ge=1, le=100)
):
    """Get all trades for a specific token."""
    try:
        response = await make_http_request(f"{PUMP_API_BASE_URL}/trades/all/{mint}?limit={limit}")
        return response
    except Exception as e:
        logging.error(f"Error getting trades for {mint}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades/count/{mint}", response_model=int)
async def get_trade_count(mint: str):
    """Get total number of trades for a token."""
    try:
        response = await make_http_request(f"{PUMP_API_BASE_URL}/trades/count/{mint}")
        return response
    except Exception as e:
        logging.error(f"Error getting trade count for {mint}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/coins/{mint}", response_model=PumpToken)
async def get_token_details(mint: str):
    """Get detailed information about a specific token by its mint address."""
    try:
        response = await make_http_request(f"{PUMP_API_BASE_URL}/coins/{mint}")
        return response
    except Exception as e:
        logging.error(f"Error getting token details for {mint}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/{mint}", response_model=TokenAnalytics)
async def get_token_analytics(
    mint: str,
    candlestick_interval: str = Query(default="1h", description="Interval for price data")
):
    """
    Get comprehensive analytics for a specific token, combining:
    - Token details
    - Trade count
    - Price history
    - Current SOL price
    - Calculated USD price
    - 24h volume
    - USD market cap
    """
    # First validate the token exists
    if not await validate_token_exists(mint):
        raise HTTPException(
            status_code=404,
            detail=f"Token with mint address {mint} not found or is not accessible"
        )
    
    try:
        # Fetch all data concurrently, with non-critical data marked as non-required
        token_data = await make_http_request(f"{PUMP_API_BASE_URL}/coins/{mint}", required=True)
        trade_count = await make_http_request(f"{PUMP_API_BASE_URL}/trades/count/{mint}", required=False)
        candlesticks = await make_http_request(f"{PUMP_API_BASE_URL}/candlesticks/{mint}?interval={candlestick_interval}", required=False)
        sol_price_data = await make_http_request(f"{PUMP_API_BASE_URL}/sol-price", required=False)
        
        # Create token model with defaults for missing fields
        token = PumpToken(**token_data)
        
        # Calculate derived metrics with safe fallbacks
        sol_price = sol_price_data.get("price", 0) if sol_price_data else 0
        latest_price = candlesticks[-1]["close"] if candlesticks and len(candlesticks) > 0 else 0
        usd_price = latest_price * sol_price if latest_price and sol_price else 0
        
        # Calculate 24h volume from candlesticks with safe fallback
        volume_24h = sum(stick.get("volume", 0) for stick in (candlesticks[-24:] if candlesticks else [])) if candlestick_interval == "1h" else 0
        
        # Calculate USD market cap with safe fallback
        market_cap_usd = token.market_cap * sol_price if token.market_cap and sol_price else 0
        
        return TokenAnalytics(
            token=token,
            trade_count=trade_count if isinstance(trade_count, int) else 0,
            price_data=candlesticks if candlesticks else [],
            sol_price=sol_price,
            usd_price=usd_price,
            volume_24h=volume_24h,
            market_cap_usd=market_cap_usd
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting token analytics for {mint}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing analytics for token {mint}. Some data may be unavailable."
        )

async def get_top_tokens(limit: int = 5) -> List[Dict[str, Any]]:
    """Get top tokens by using trending metas sorted by volume"""
    try:
        # Get trending keywords
        trending_metas = await make_http_request(
            f"{PUMP_API_BASE_URL}/metas/current",
            required=False
        )
        if not trending_metas:
            return []
            
        # Sort by total volume and take top keywords
        sorted_metas = sorted(trending_metas, key=lambda x: x.get('total_vol', 0), reverse=True)
        top_keywords = sorted_metas[:limit]
        
        # For each keyword, try to get matching tokens from the latest ones
        tokens = []
        latest_tokens = []
        
        # Get multiple latest tokens to increase chances of finding matches
        for i in range(10):  # Try up to 10 latest tokens
            try:
                latest = await make_http_request(
                    f"{PUMP_API_BASE_URL}/coins/latest?qty=1&offset={i}",
                    required=False
                )
                if latest and isinstance(latest, dict) and 'mint' in latest:
                    latest_tokens.append(latest)
            except Exception as e:
                logging.warning(f"Failed to get latest token with offset {i}: {e}")
                continue
        
        # Try to match keywords with tokens
        for meta in top_keywords:
            keyword = meta['word'].lower()
            # Try to find a matching token
            for token in latest_tokens:
                name = token.get('name', '').lower()
                symbol = token.get('symbol', '').lower()
                if keyword in name or keyword in symbol:
                    tokens.append(token)
                    break  # Found a match for this keyword, move to next
        
        return tokens[:limit]
        
    except Exception as e:
        logging.error(f"Error getting top tokens: {e}", exc_info=True)
        return []

@router.get("/market-overview", response_model=MarketOverview)
async def get_market_overview(
    include_nsfw: bool = Query(default=True, description="Whether to include NSFW tokens"),
    latest_limit: int = Query(default=5, description="Number of latest tokens to fetch")
):
    """Get market overview including king of the hill and latest tokens"""
    try:
        logging.info("Fetching king of the hill")
        king_of_the_hill = await make_http_request(
            f"{PUMP_API_BASE_URL}/coins/king-of-the-hill?includeNsfw={'true' if include_nsfw else 'false'}",
            required=False
        )
        
        logging.info(f"Fetching latest tokens with limit {latest_limit}")
        latest_tokens = await make_http_request(
            f"{PUMP_API_BASE_URL}/coins/latest?qty={latest_limit}&includeNsfw={'true' if include_nsfw else 'false'}",
            required=False
        )
        
        logging.info("Fetching SOL price")
        sol_price_data = await make_http_request(
            f"{PUMP_API_BASE_URL}/sol-price",
            required=False
        )
        
        # Extract SOL price from response
        sol_price = sol_price_data.get("solPrice", 0) if sol_price_data and isinstance(sol_price_data, dict) else 0
        logging.info(f"SOL price: {sol_price}")
        
        # Ensure king_of_the_hill and latest_tokens are lists
        king_of_the_hill = [king_of_the_hill] if king_of_the_hill and isinstance(king_of_the_hill, dict) else king_of_the_hill or []
        latest_tokens = latest_tokens if isinstance(latest_tokens, list) else [latest_tokens] if latest_tokens else []
        
        logging.info(f"King of the hill count: {len(king_of_the_hill)}")
        logging.info(f"Latest tokens count: {len(latest_tokens)}")
        
        # Prepare response
        response = {
            "king_of_the_hill": [PumpToken(**token) for token in king_of_the_hill],
            "latest_tokens": [PumpToken(**token) for token in latest_tokens],
            "sol_price": sol_price,
            "total_tokens_tracked": 0,
            "total_volume_24h": 0
        }
        
        logging.info("Successfully prepared market overview response")
        return response
        
    except Exception as e:
        logging.error(f"Error getting market overview: {e}", exc_info=True)
        # Return default values to avoid breaking the UI
        return {
            "king_of_the_hill": [],
            "latest_tokens": [],
            "sol_price": 0,
            "total_tokens_tracked": 0,
            "total_volume_24h": 0
        }

@router.get("/token-history/{mint}")
async def get_token_history(
    mint: str,
    time_range: str = Query(default="24h", description="Time range to fetch history for (24h, 7d, 30d)"),
    trade_limit: int = Query(default=50, ge=1, le=100)
):
    """
    Get comprehensive token history combining:
    - Recent trades
    - Price history
    - Trading volume
    - Price changes
    Returns both raw data and calculated metrics like:
    - Price change percentage
    - Volume trends
    - Trade frequency
    """
    try:
        # Fetch trade and price data
        trades = await make_http_request(f"{PUMP_API_BASE_URL}/trades/all/{mint}?limit={trade_limit}")
        candlesticks = await make_http_request(f"{PUMP_API_BASE_URL}/candlesticks/{mint}?interval=1h")
        
        # Calculate metrics
        if candlesticks:
            latest_price = candlesticks[-1]["close"]
            start_price = candlesticks[0]["close"]
            price_change_pct = ((latest_price - start_price) / start_price) * 100 if start_price else 0
            
            # Calculate volume trends
            recent_volume = sum(stick["volume"] for stick in candlesticks[-24:])
            older_volume = sum(stick["volume"] for stick in candlesticks[-48:-24])
            volume_change_pct = ((recent_volume - older_volume) / older_volume) * 100 if older_volume else 0
        else:
            price_change_pct = 0
            volume_change_pct = 0
            
        # Calculate trade frequency (trades per hour)
        if trades:
            time_span = (trades[0]["timestamp"] - trades[-1]["timestamp"]) / 3600  # Convert to hours
            trades_per_hour = len(trades) / time_span if time_span > 0 else 0
        else:
            trades_per_hour = 0
            
        return {
            "trades": trades,
            "price_history": candlesticks,
            "metrics": {
                "price_change_percentage": price_change_pct,
                "volume_change_percentage": volume_change_pct,
                "trades_per_hour": trades_per_hour,
                "total_trades": len(trades),
                "unique_traders": len(set(trade["user"] for trade in trades))
            }
        }
    except Exception as e:
        logging.error(f"Error getting token history for {mint}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-performers", response_model=List[PumpToken])
async def get_top_performers(
    metric: str = Query(default="volume_24h", description="Metric to sort by"),
    limit: int = Query(default=10, ge=1, le=50, description="Number of tokens to return"),
    hours: int = Query(default=24, ge=1, le=168, description="Time window in hours"),
    include_nsfw: bool = Query(default=True, description="Whether to include NSFW tokens"),
    refresh: bool = Query(default=False, description="Force refresh from Pump.fun API")
):
    """
    Get top performing tokens based on different metrics.
    """
    try:
        logging.info(f"Getting top performers with metric={metric}, limit={limit}, hours={hours}, include_nsfw={include_nsfw}, refresh={refresh}")
        
        db = DatabaseCache()
        
        # If not forcing a refresh, try to get from the database
        if not refresh:
            top_tokens = db.get_top_performing_tokens(metric, limit, hours)
            if top_tokens and len(top_tokens) > 0:
                logging.info(f"Retrieved {len(top_tokens)} top performing tokens from database")
                return [PumpToken.parse_obj(token["data"]) for token in top_tokens]
        
        # If we're here, either refresh was requested or no data was found in the database
        # Get the latest tokens from Pump.fun and store them in the database
        logging.info("Fetching latest tokens from Pump.fun API for top performers")
        latest_tokens = await get_latest_tokens(qty=50)
        
        # Store each token in the database
        stored_count = 0
        for token in latest_tokens:
            if db.store_token_performance(token):
                stored_count += 1
        
        logging.info(f"Stored {stored_count} tokens in the database")
        
        # Now get the top performers from the database
        top_tokens = db.get_top_performing_tokens(metric, limit, hours)
        
        if not top_tokens or len(top_tokens) == 0:
            # If still no data, sort the latest tokens by the requested metric
            logging.info(f"No top performers found in database, sorting latest tokens by {metric}")
            
            # No need to convert, tokens are already dictionaries
            token_dicts = latest_tokens
            
            # Sort by the requested metric
            if metric == "volume_24h":
                sorted_tokens = sorted(token_dicts, key=lambda x: x.get("real_sol_reserves", 0), reverse=True)
            elif metric == "market_cap":
                sorted_tokens = sorted(token_dicts, key=lambda x: x.get("market_cap", 0), reverse=True)
            elif metric == "price_change_24h":
                # This would require historical data which we don't have yet
                sorted_tokens = token_dicts
            else:
                sorted_tokens = token_dicts
            
            # Limit the results
            result_tokens = sorted_tokens[:limit]
            logging.info(f"Returning {len(result_tokens)} top performers sorted by {metric}")
            
            # Convert dictionaries to PumpToken objects
            return [PumpToken.parse_obj(token) for token in result_tokens]
        
        # Return the top tokens from the database
        logging.info(f"Returning {len(top_tokens)} top performers from database")
        return [PumpToken.parse_obj(token["data"]) for token in top_tokens]
        
    except Exception as e:
        logging.error(f"Error getting top performers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
