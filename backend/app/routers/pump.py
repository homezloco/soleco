from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import RedirectResponse
import httpx
from pydantic import BaseModel
import logging
from datetime import datetime, timedelta
import asyncio
import random
import time
from app.database.sqlite import DatabaseCache, db_cache
from ..constants.cache import (
    MARKET_OVERVIEW_CACHE_TTL,
    SOL_PRICE_CACHE_TTL,
    LATEST_TOKENS_CACHE_TTL,
    TOKEN_DETAILS_CACHE_TTL,
    TOKEN_ANALYTICS_CACHE_TTL,
    TOKEN_HISTORY_CACHE_TTL,
    LATEST_TRADES_CACHE_TTL,
    TOP_PERFORMERS_CACHE_TTL,
    KING_OF_THE_HILL_CACHE_TTL,
    SEARCH_TOKENS_CACHE_TTL
)

router = APIRouter(tags=["PumpFun"])

PUMP_API_BASE_URL = "https://frontend-api.pump.fun"

# Request throttling for Pump.fun API
class RequestThrottler:
    """
    Request throttler to limit concurrent requests to the Pump.fun API.
    This helps prevent rate limiting by ensuring we don't overwhelm the API.
    """
    def __init__(self, max_concurrent=3, rate_limit=10, time_window=60):
        """
        Initialize the request throttler.
        
        Args:
            max_concurrent: Maximum number of concurrent requests
            rate_limit: Maximum number of requests in time_window
            time_window: Time window in seconds for rate limiting
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.request_timestamps = []
        self.lock = asyncio.Lock()
        
    async def acquire(self):
        """
        Acquire permission to make a request.
        This will block if we've reached the maximum concurrent requests
        or if we've exceeded the rate limit.
        """
        # First check rate limiting
        async with self.lock:
            now = datetime.now().timestamp()
            # Remove timestamps older than the time window
            self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < self.time_window]
            
            # Check if we've exceeded the rate limit
            if len(self.request_timestamps) >= self.rate_limit:
                # Calculate time to wait
                oldest = min(self.request_timestamps)
                wait_time = self.time_window - (now - oldest) + 0.1  # Add a small buffer
                logging.warning(f"Rate limit reached, waiting {wait_time:.2f}s before making request")
                await asyncio.sleep(wait_time)
                
                # Recursively try again after waiting
                return await self.acquire()
            
            # Add current timestamp
            self.request_timestamps.append(now)
        
        # Now acquire the semaphore for concurrent request limiting
        await self.semaphore.acquire()
        
    def release(self):
        """Release the semaphore."""
        self.semaphore.release()
        
    async def __aenter__(self):
        await self.acquire()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()

# Create global throttler instance
pump_throttler = RequestThrottler(max_concurrent=3, rate_limit=10, time_window=60)

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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the PumpToken to a dictionary for JSON serialization."""
        return {
            "mint": self.mint,
            "name": self.name,
            "symbol": self.symbol,
            "description": self.description,
            "image_uri": self.image_uri,
            "video_uri": self.video_uri,
            "metadata_uri": self.metadata_uri,
            "twitter": self.twitter,
            "telegram": self.telegram,
            "bonding_curve": self.bonding_curve,
            "associated_bonding_curve": self.associated_bonding_curve,
            "creator": self.creator,
            "created_timestamp": self.created_timestamp,
            "raydium_pool": self.raydium_pool,
            "complete": self.complete,
            "virtual_sol_reserves": self.virtual_sol_reserves,
            "virtual_token_reserves": self.virtual_token_reserves,
            "total_supply": self.total_supply,
            "website": self.website,
            "show_name": self.show_name,
            "king_of_the_hill_timestamp": self.king_of_the_hill_timestamp,
            "market_cap": self.market_cap,
            "reply_count": self.reply_count,
            "last_reply": self.last_reply,
            "nsfw": self.nsfw,
            "market_id": self.market_id,
            "inverted": self.inverted,
            "is_currently_live": self.is_currently_live,
            "username": self.username,
            "profile_image": self.profile_image,
            "usd_market_cap": self.usd_market_cap,
            "hidden": self.hidden,
            "last_trade_timestamp": self.last_trade_timestamp,
            "real_sol_reserves": self.real_sol_reserves,
            "livestream_ban_expiry": self.livestream_ban_expiry,
            "is_banned": self.is_banned,
            "initialized": self.initialized,
            "updated_at": self.updated_at,
            "real_token_reserves": self.real_token_reserves
        }

class PumpTrade(BaseModel):
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the PumpTrade to a dictionary for JSON serialization."""
        return {
            "signature": self.signature,
            "mint": self.mint,
            "sol_amount": self.sol_amount,
            "token_amount": self.token_amount,
            "is_buy": self.is_buy,
            "user": self.user,
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "image_uri": self.image_uri,
            "slot": self.slot
        }

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
    top_tokens: Optional[List[PumpToken]] = []
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

import random

async def make_http_request(url: str, required: bool = True) -> dict:
    """
    Make HTTP request to Pump.fun API with rate limiting protection.
    
    Args:
        url: The URL to request
        required: Whether the request is required (if False, returns None instead of raising an exception)
        
    Returns:
        The JSON response data or None if not required and an error occurred
    """
    max_retries = 5  
    base_delay = 2.0  
    
    # Extract endpoint from URL for logging
    endpoint = url.split("/")[-1].split("?")[0]
    
    for retry in range(max_retries):
        try:
            # Calculate exponential backoff delay if this is a retry
            delay = base_delay * (2 ** retry) if retry > 0 else 0
            if retry > 0:
                logging.info(f"Retry {retry}/{max_retries} for {endpoint} with {delay:.1f}s delay")
                await asyncio.sleep(delay)
            
            logging.info(f"Making request to: {url}")
            
            # Add a small random delay between requests to avoid hitting rate limits
            if retry == 0:
                jitter = random.uniform(0.1, 0.5)
                await asyncio.sleep(jitter)
            
            async with pump_throttler:
                async with httpx.AsyncClient(timeout=45.0) as client:  
                    start_time = time.time()
                    response = await client.get(
                        url, 
                        headers={
                            "accept": "*/*",
                            "User-Agent": "Soleco/1.0 (https://github.com/homezloco/soleco)"
                        }
                    )
                    
                    request_time = time.time() - start_time
                    logging.info(f"Response status for {endpoint}: {response.status_code} (took {request_time:.2f}s)")
                    
                    if response.status_code == 404:
                        if required:
                            raise HTTPException(status_code=404, detail="Resource not found")
                        return None
                    elif response.status_code == 429:
                        # Rate limited, use exponential backoff
                        if retry < max_retries - 1:
                            # Extract retry-after header if available
                            retry_after = response.headers.get('retry-after')
                            if retry_after and retry_after.isdigit():
                                wait_time = int(retry_after) + random.uniform(0.5, 2.0)  
                            else:
                                wait_time = base_delay * (2 ** retry) + random.uniform(1, 3)  
                                
                            logging.warning(f"Rate limited on {endpoint}. Waiting {wait_time:.1f}s before retry {retry + 1}/{max_retries}")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logging.error(f"Rate limited after {max_retries} retries on {endpoint}")
                            if required:
                                raise HTTPException(
                                    status_code=429, 
                                    detail=f"Rate limited by Pump.fun API after {max_retries} retries. Please try again later."
                                )
                            return None
                    elif response.status_code == 500:
                        if retry < max_retries - 1:
                            wait_time = base_delay * (2 ** retry) + random.uniform(0.5, 1.5)
                            logging.warning(f"Server error (500) on {endpoint}. Retrying in {wait_time:.1f}s")
                            await asyncio.sleep(wait_time)
                            continue
                        elif required:
                            raise HTTPException(status_code=502, detail="Pump.fun API server error")
                        return None
                        
                    response.raise_for_status()
                    data = response.json()
                    return data
        except httpx.TimeoutException as e:
            logging.error(f"Timeout error occurred while fetching {endpoint} from Pump.fun: {e}")
            if retry < max_retries - 1:
                wait_time = base_delay * (2 ** retry) + random.uniform(0.5, 1.5)
                logging.warning(f"Timeout error on {endpoint}. Waiting {wait_time:.1f}s before retry {retry + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                continue
            if required:
                raise HTTPException(status_code=504, detail=f"Timeout error fetching data from Pump.fun: {str(e)}")
            return None
        except httpx.ConnectError as e:
            logging.error(f"Connection error occurred while fetching {endpoint} from Pump.fun: {e}")
            if retry < max_retries - 1:
                wait_time = base_delay * (2 ** retry) + random.uniform(0.5, 1.5)
                logging.warning(f"Connection error on {endpoint}. Waiting {wait_time:.1f}s before retry {retry + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                continue
            if required:
                raise HTTPException(status_code=503, detail=f"Connection error fetching data from Pump.fun: {str(e)}")
            return None
        except httpx.HTTPError as e:
            logging.error(f"HTTP error occurred while fetching {endpoint} from Pump.fun: {e}")
            if retry < max_retries - 1:
                wait_time = base_delay * (2 ** retry) + random.uniform(0.5, 1.5)
                logging.warning(f"HTTP error on {endpoint}. Waiting {wait_time:.1f}s before retry {retry + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                continue
            if required:
                raise HTTPException(status_code=502, detail=f"Error fetching data from Pump.fun: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error occurred while fetching {endpoint} from Pump.fun: {e}")
            if retry < max_retries - 1:
                wait_time = base_delay * (2 ** retry) + random.uniform(0.5, 1.5)
                logging.warning(f"Unexpected error on {endpoint}. Waiting {wait_time:.1f}s before retry {retry + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                continue
            if required:
                raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
            return None
    
    # If we get here, all retries failed
    if required:
        raise HTTPException(status_code=503, detail=f"Failed to fetch {endpoint} data after {max_retries} retries")
    return None

@router.get("/coins/latest", response_model=List[PumpToken])
async def get_latest_tokens(
    qty: int = Query(default=1, ge=1, le=50, description="Number of latest tokens to retrieve"),
    refresh: bool = Query(default=False, description="Force refresh from Pump.fun API")
):
    """
    Get the latest tokens from Pump.fun. Returns up to 50 most recent tokens.
    
    Args:
        qty: Number of latest tokens to retrieve (1-50)
        refresh: Whether to force a refresh from the Pump.fun API
        
    Returns:
        List of latest tokens
    """
    try:
        logging.info(f"Getting {qty} latest tokens with refresh={refresh}")
        
        # Create cache key based on parameters
        params = {
            "qty": qty
        }
        
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data("latest-tokens", params, LATEST_TOKENS_CACHE_TTL)
            if cached_data:
                logging.info(f"Retrieved {len(cached_data)} latest tokens from cache")
                return [PumpToken.parse_obj(token) for token in cached_data]
        
        # If not in cache or forcing refresh, fetch from API
        logging.info(f"Fetching {qty} latest tokens from Pump.fun API")
        
        # The new approach: query the same endpoint multiple times with a delay
        all_tokens = []
        seen_mints = set()  # To track unique tokens
        
        # Keep querying until we have the requested number of unique tokens
        max_attempts = qty * 3  # Allow for some duplicates by trying up to 3x the requested quantity
        attempt = 0
        
        while len(all_tokens) < qty and attempt < max_attempts:
            attempt += 1
            logging.info(f"Fetching token attempt {attempt}/{max_attempts}, have {len(all_tokens)}/{qty} so far")
            
            # Use the correct endpoint without offset parameters
            response = await make_http_request(f"{PUMP_API_BASE_URL}/coins/latest")
            
            if response:
                # Check if this is a new token we haven't seen yet
                if isinstance(response, dict) and 'mint' in response:
                    mint = response['mint']
                    if mint not in seen_mints:
                        seen_mints.add(mint)
                        all_tokens.append(response)
                        logging.info(f"Added new token: {response.get('name', 'Unknown')} ({mint})")
                    else:
                        logging.info(f"Skipping duplicate token with mint: {mint}")
                else:
                    logging.warning(f"Unexpected response format: {type(response)}")
            
            # Add a small delay between requests to avoid rate limiting and to get different tokens
            if len(all_tokens) < qty and attempt < max_attempts:
                delay = random.uniform(0.8, 1.5)  # Random delay between 0.8 and 1.5 seconds
                logging.info(f"Waiting {delay:.2f}s before next request")
                await asyncio.sleep(delay)
        
        # Convert to PumpToken objects
        tokens = [PumpToken.parse_obj(token) for token in all_tokens[:qty]]
        
        # Cache the result
        cache_data = [token.to_dict() for token in tokens]
        db_cache.cache_data("latest-tokens", cache_data, params, LATEST_TOKENS_CACHE_TTL)
        
        logging.info(f"Retrieved {len(tokens)} latest tokens from Pump.fun")
        return tokens
    except Exception as e:
        logging.error(f"Error getting latest tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades/latest", response_model=List[PumpTrade])
async def get_latest_trades(
    qty: int = Query(default=1, ge=1, le=50, description="Number of latest trades to retrieve"),
    include_all: bool = Query(default=False, description="Include all trades, not just buys"),
    include_nsfw: bool = Query(default=False, description="Include NSFW tokens"),
    refresh: bool = Query(default=False, description="Force refresh from Pump.fun API")
):
    """
    Get the latest trades from Pump.fun. Returns up to 50 most recent trades.
    
    Args:
        qty: Number of latest trades to retrieve (1-50)
        include_all: Whether to include all trades, not just buys
        include_nsfw: Whether to include NSFW tokens
        refresh: Whether to force a refresh from the Pump.fun API
        
    Returns:
        List of latest trades
    """
    try:
        logging.info(f"Getting {qty} latest trades with include_all={include_all}, include_nsfw={include_nsfw}, refresh={refresh}")
        
        # Create cache key based on parameters
        params = {
            "qty": qty,
            "include_all": include_all,
            "include_nsfw": include_nsfw
        }
        
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data("latest-trades", params, LATEST_TRADES_CACHE_TTL)
            if cached_data:
                logging.info(f"Retrieved {len(cached_data)} latest trades from cache")
                return [PumpTrade.parse_obj(trade) for trade in cached_data]
        
        # If not in cache or forcing refresh, fetch from API
        logging.info(f"Fetching {qty} latest trades from Pump.fun API")
        
        # The new approach: query the same endpoint multiple times with a delay
        all_trades = []
        seen_signatures = set()  # To track unique trades by signature
        
        # Keep querying until we have the requested number of unique trades
        max_attempts = qty * 3  # Allow for some duplicates by trying up to 3x the requested quantity
        attempt = 0
        
        # Construct the base URL with parameters
        url = f"{PUMP_API_BASE_URL}/trades/latest"
        if not include_all:
            url += "?buysOnly=true"
        if not include_nsfw:
            url += f"{'&' if '?' in url else '?'}includeNsfw=false"
        
        while len(all_trades) < qty and attempt < max_attempts:
            attempt += 1
            logging.info(f"Fetching trade attempt {attempt}/{max_attempts}, have {len(all_trades)}/{qty} so far")
            
            # Make the request to the API
            response = await make_http_request(url)
            
            if response:
                try:
                    # Check if this is a new trade we haven't seen yet
                    if isinstance(response, dict) and 'signature' in response:
                        signature = response['signature']
                        if signature not in seen_signatures:
                            seen_signatures.add(signature)
                            
                            # Filter by buy/sell if needed
                            if include_all or response.get('is_buy', False):
                                all_trades.append(response)
                                logging.info(f"Added new trade: {signature} for token {response.get('symbol', 'Unknown')}")
                            else:
                                logging.info(f"Skipping sell trade with signature: {signature}")
                        else:
                            logging.info(f"Skipping duplicate trade with signature: {signature}")
                    elif isinstance(response, list):
                        # Handle case where API might return a list
                        for trade in response:
                            if isinstance(trade, dict) and 'signature' in trade:
                                signature = trade['signature']
                                if signature not in seen_signatures:
                                    seen_signatures.add(signature)
                                    
                                    # Filter by buy/sell if needed
                                    if include_all or trade.get('is_buy', False):
                                        all_trades.append(trade)
                                        logging.info(f"Added new trade from list: {signature}")
                                    else:
                                        logging.info(f"Skipping sell trade from list with signature: {signature}")
                    else:
                        logging.warning(f"Unexpected response format: {type(response)}")
                except Exception as e:
                    logging.error(f"Error processing trade response: {e}")
            
            # Add a small delay between requests to avoid rate limiting and to get different trades
            if len(all_trades) < qty and attempt < max_attempts:
                delay = random.uniform(0.8, 1.5)  # Random delay between 0.8 and 1.5 seconds
                logging.info(f"Waiting {delay:.2f}s before next request")
                await asyncio.sleep(delay)
        
        # Convert to PumpTrade objects and limit to requested quantity
        trades = [PumpTrade.parse_obj(trade) for trade in all_trades[:qty]]
        
        # Cache the result
        cache_data = [trade.to_dict() for trade in trades]
        db_cache.cache_data("latest-trades", cache_data, params, LATEST_TRADES_CACHE_TTL)
        
        logging.info(f"Retrieved {len(trades)} latest trades from Pump.fun")
        return trades
    except Exception as e:
        logging.error(f"Error getting latest trades: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/coins/king-of-the-hill", response_model=PumpToken)
async def get_king_of_the_hill(
    include_nsfw: bool = Query(default=True, description="Whether to include NSFW tokens"),
    refresh: bool = Query(default=False, description="Force refresh from Pump.fun API")
):
    """
    Get the current King of the Hill token from Pump.fun.
    """
    try:
        logging.info(f"Getting king of the hill with include_nsfw={include_nsfw}, refresh={refresh}")
        
        # Create cache key based on parameters
        params = {"include_nsfw": include_nsfw}
        
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data("king-of-the-hill", params, KING_OF_THE_HILL_CACHE_TTL)
            if cached_data:
                logging.info(f"Retrieved king of the hill token from cache")
                return PumpToken.parse_obj(cached_data)
        
        # If not in cache or forcing refresh, fetch from API
        logging.info("Fetching king of the hill from Pump.fun API")
        response = await make_http_request(f"{PUMP_API_BASE_URL}/coins/king-of-the-hill")
        
        # Filter NSFW if needed
        if not include_nsfw and response and response.get("nsfw", False):
            logging.info("King of the hill is NSFW, but include_nsfw=False, returning empty result")
            return PumpToken(mint="", name="No non-NSFW king of the hill available")
        
        # Cache the result
        token = PumpToken.parse_obj(response)
        db_cache.cache_data("king-of-the-hill", token.to_dict(), params, KING_OF_THE_HILL_CACHE_TTL)
        
        return token
    except Exception as e:
        logging.error(f"Error getting king of the hill: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/king-of-the-hill", response_model=PumpToken)
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
async def get_sol_price(
    refresh: bool = Query(default=False, description="Force refresh from Pump.fun API")
):
    """Get current SOL price."""
    try:
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data("sol-price", None, SOL_PRICE_CACHE_TTL)
            if cached_data:
                logging.info("Retrieved SOL price from cache")
                return cached_data
        
        response = await make_http_request(f"{PUMP_API_BASE_URL}/sol-price")
        # Transform the response to match our model
        if response and "solPrice" in response:
            result = {
                "price": response["solPrice"],
                "last_updated": int(datetime.now().timestamp())
            }
            
            # Cache the response
            db_cache.cache_data("sol-price", result, None, SOL_PRICE_CACHE_TTL)
            
            return result
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

@router.get("/trades/all/{mint}", response_model=List[PumpTrade])
async def get_all_trades(
    mint: str,
    limit: int = Query(default=50, ge=1, le=100),
    refresh: bool = Query(default=False, description="Force refresh from Pump.fun API")
):
    """
    Get all trades for a specific token.
    
    Args:
        mint: Token mint address
        limit: Maximum number of trades to return (1-100)
        refresh: Whether to force a refresh from the Pump.fun API
        
    Returns:
        List of trades for the token
    """
    try:
        # Create cache key based on parameters
        params = {"mint": mint, "limit": limit}
        
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data("trades-all", params, LATEST_TRADES_CACHE_TTL)
            if cached_data:
                logging.info(f"Retrieved {len(cached_data)} trades for {mint} from cache")
                return [PumpTrade.parse_obj(trade) for trade in cached_data]
                
        logging.info(f"Fetching up to {limit} trades for token {mint}")
        response = await make_http_request(f"{PUMP_API_BASE_URL}/trades/all/{mint}?limit={limit}")
        
        # Cache the result
        if response:
            db_cache.cache_data("trades-all", [trade.to_dict() for trade in [PumpTrade.parse_obj(trade) for trade in response]], params, LATEST_TRADES_CACHE_TTL)
            logging.info(f"Cached {len(response)} trades for {mint}")
        
        return [PumpTrade.parse_obj(trade) for trade in response] if response else []
    except Exception as e:
        logging.error(f"Error getting trades for {mint}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving trades: {str(e)}"
        )

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
async def get_token_details(
    mint: str,
    refresh: bool = Query(default=False, description="Force refresh from Pump.fun API")
):
    """
    Get detailed information about a specific token by its mint address.
    
    Args:
        mint: Token mint address
        refresh: Whether to force a refresh from the Pump.fun API
        
    Returns:
        Detailed token information
    """
    try:
        # Create cache key based on parameters
        params = {"mint": mint}
        
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data(f"token-details-{mint}", params, TOKEN_DETAILS_CACHE_TTL)
            if cached_data:
                logging.info(f"Retrieved token details for {mint} from cache")
                return cached_data
                
        response = await make_http_request(f"{PUMP_API_BASE_URL}/coins/{mint}")
        
        # Cache the response
        token = PumpToken.parse_obj(response)
        db_cache.cache_data(f"token-details-{mint}", token.to_dict(), params, TOKEN_DETAILS_CACHE_TTL)
        
        return token
    except Exception as e:
        logging.error(f"Error getting token details for {mint}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/{mint}", response_model=TokenAnalytics)
async def get_token_analytics(
    mint: str,
    candlestick_interval: str = Query(default="1h", description="Interval for price data"),
    refresh: bool = Query(default=False, description="Force refresh from Pump.fun API")
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
    # Create cache key based on parameters
    params = {
        "mint": mint,
        "candlestick_interval": candlestick_interval
    }
    
    # Try to get from cache if not forcing refresh
    if not refresh:
        cached_data = db_cache.get_cached_data(f"token-analytics-{mint}", params, TOKEN_ANALYTICS_CACHE_TTL)
        if cached_data:
            logging.info(f"Retrieved token analytics for {mint} from cache")
            return cached_data
    
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
        
        analytics = TokenAnalytics(
            token=token,
            trade_count=trade_count if isinstance(trade_count, int) else 0,
            price_data=candlesticks if candlesticks else [],
            sol_price=sol_price,
            usd_price=usd_price,
            volume_24h=volume_24h,
            market_cap_usd=market_cap_usd
        )
        
        # Cache the response
        db_cache.cache_data(f"token-analytics-{mint}", analytics.dict(), params, TOKEN_ANALYTICS_CACHE_TTL)
        
        return analytics

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting token analytics for {mint}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing analytics for token {mint}. Some data may be unavailable."
        )

async def get_top_tokens(limit: int = 5, refresh: bool = False) -> List[Dict[str, Any]]:
    """Get top tokens by using trending metas sorted by volume"""
    try:
        logging.info(f"Getting top tokens with limit={limit}, refresh={refresh}")
        
        # Create cache key based on parameters
        params = {"limit": limit}
        
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data("top-tokens", params, TOP_PERFORMERS_CACHE_TTL)
            if cached_data:
                logging.info(f"Retrieved {len(cached_data)} top tokens from cache")
                return cached_data
                
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
        
        result = tokens[:limit]
        
        # Cache the response
        db_cache.cache_data("top-tokens", result, params, TOP_PERFORMERS_CACHE_TTL)
        
        return result
    except Exception as e:
        logging.error(f"Error getting top tokens: {e}", exc_info=True)
        return []

@router.get("/market-overview", response_model=MarketOverview)
async def get_market_overview(
    include_nsfw: bool = Query(default=True, description="Whether to include NSFW tokens"),
    latest_limit: int = Query(default=5, description="Number of latest tokens to fetch"),
    refresh: bool = Query(default=False, description="Force refresh from Pump.fun API")
):
    """Get market overview including king of the hill and latest tokens"""
    try:
        # Create cache key based on parameters
        params = {
            "include_nsfw": include_nsfw,
            "latest_limit": latest_limit
        }
        
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data("market-overview", params, MARKET_OVERVIEW_CACHE_TTL)
            if cached_data:
                logging.info("Retrieved market overview from cache")
                return cached_data
        
        # Get data concurrently with proper caching
        king_of_the_hill = await get_king_of_the_hill(include_nsfw=include_nsfw, refresh=refresh)
        latest_tokens = await get_latest_tokens(qty=latest_limit, refresh=refresh)
        sol_price_data = await get_sol_price(refresh=refresh)
        top_tokens = await get_top_tokens(limit=5, refresh=refresh)
        
        # Extract SOL price from response
        sol_price = sol_price_data.get("price", 0) if sol_price_data and isinstance(sol_price_data, dict) else 0
        logging.info(f"SOL price: {sol_price}")
        
        # Ensure king_of_the_hill is properly formatted
        king_list = []
        if king_of_the_hill:
            if isinstance(king_of_the_hill, dict):
                king_list = [king_of_the_hill]
            elif isinstance(king_of_the_hill, list):
                king_list = king_of_the_hill
        
        # Ensure latest_tokens is a list
        latest_list = latest_tokens if isinstance(latest_tokens, list) else [latest_tokens] if latest_tokens else []
        
        # Ensure top_tokens is a list
        top_list = top_tokens if isinstance(top_tokens, list) else [top_tokens] if top_tokens else []
        
        logging.info(f"King of the hill count: {len(king_list)}")
        logging.info(f"Latest tokens count: {len(latest_list)}")
        logging.info(f"Top tokens count: {len(top_list)}")
        
        # Prepare response
        response = {
            "king_of_the_hill": king_list,
            "latest_tokens": latest_list,
            "top_tokens": top_list,
            "sol_price": sol_price,
            "total_tokens_tracked": 0,
            "total_volume_24h": 0
        }
        
        # Cache the response
        db_cache.cache_data("market-overview", response, params, MARKET_OVERVIEW_CACHE_TTL)
        
        logging.info("Successfully prepared market overview response")
        return response
        
    except Exception as e:
        logging.error(f"Error getting market overview: {e}", exc_info=True)
        # Return default values to avoid breaking the UI
        return {
            "king_of_the_hill": [],
            "latest_tokens": [],
            "top_tokens": [],
            "sol_price": 0,
            "total_tokens_tracked": 0,
            "total_volume_24h": 0
        }

@router.get("/token-history/{mint}")
async def get_token_history(
    mint: str,
    time_range: str = Query(default="24h", description="Time range to fetch history for (24h, 7d, 30d)"),
    trade_limit: int = Query(default=50, ge=1, le=100),
    refresh: bool = Query(default=False, description="Force refresh from Pump.fun API")
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
        # Create cache key based on parameters
        params = {
            "mint": mint,
            "time_range": time_range,
            "trade_limit": trade_limit
        }
        
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data(f"token-history-{mint}", params, TOKEN_HISTORY_CACHE_TTL)
            if cached_data:
                logging.info(f"Retrieved token history for {mint} from cache")
                return cached_data
                
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
            
        result = {
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
        
        # Cache the response
        db_cache.cache_data(f"token-history-{mint}", result, params, TOKEN_HISTORY_CACHE_TTL)
        
        return result
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
        
        # Create cache key based on parameters
        params = {
            "metric": metric,
            "limit": limit,
            "hours": hours,
            "include_nsfw": include_nsfw
        }
        
        # Try to get from cache if not forcing refresh
        if not refresh:
            cached_data = db_cache.get_cached_data("top-performers", params, TOP_PERFORMERS_CACHE_TTL)
            if cached_data:
                logging.info(f"Retrieved {len(cached_data)} top performers from cache")
                result = [PumpToken.parse_obj(token) for token in cached_data]
                return result
        
        db = DatabaseCache()
        
        # If not forcing a refresh, try to get from the database
        if not refresh:
            top_tokens = db.get_top_performing_tokens(metric, limit, hours)
            if top_tokens and len(top_tokens) > 0:
                logging.info(f"Retrieved {len(top_tokens)} top performing tokens from database")
                result = [PumpToken.parse_obj(token["data"]) for token in top_tokens]
                cache_data = [token.to_dict() for token in result]
                db_cache.cache_data("top-performers", cache_data, params, TOP_PERFORMERS_CACHE_TTL)
                return result
        
        # If we're here, either refresh was requested or no data was found in the database
        # Get the latest tokens from Pump.fun and store them in the database
        logging.info("Fetching latest tokens from Pump.fun API for top performers")
        latest_tokens = await get_latest_tokens(qty=50, refresh=refresh)
        
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
            result = [PumpToken.parse_obj(token) for token in result_tokens]
            cache_data = [token.to_dict() for token in result]
            db_cache.cache_data("top-performers", cache_data, params, TOP_PERFORMERS_CACHE_TTL)
            return result
        
        # Return the top tokens from the database
        logging.info(f"Returning {len(top_tokens)} top performers from database")
        result = [PumpToken.parse_obj(token["data"]) for token in top_tokens]
        cache_data = [token.to_dict() for token in result]
        db_cache.cache_data("top-performers", cache_data, params, TOP_PERFORMERS_CACHE_TTL)
        return result
        
    except Exception as e:
        logging.error(f"Error getting top performers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
