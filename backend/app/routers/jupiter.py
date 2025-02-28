from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import httpx
from urllib.parse import unquote, parse_qs, urlparse, urljoin
import socket
import dns.resolver

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Jupiter"])

JUPITER_API_HOST = "price.jup.ag"
JUPITER_API_FALLBACK_IP = "146.190.153.45"  # Resolved IP for price.jup.ag
JUPITER_API_BASE = "https://api.jup.ag"
JUPITER_TOKEN_HOST = "token.jup.ag"
JUPITER_PRICE_API_VERSION = "v2"
HTTP_TIMEOUT = 30.0
VERIFY_SSL = True

DNS_SERVERS = [
    "8.8.8.8",  # Google DNS
    "1.1.1.1",  # Cloudflare DNS
]

async def resolve_host(hostname: str) -> str:
    """
    Resolve hostname to IP address using multiple DNS servers
    """
    try:
        # First try direct socket resolution
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            logger.warning(f"Failed to resolve {hostname} using system DNS")
        
        # Try multiple DNS servers
        for dns_server in DNS_SERVERS:
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [dns_server]
                answers = resolver.resolve(hostname, "A")
                for answer in answers:
                    return str(answer)
            except Exception as e:
                logger.warning(f"Failed to resolve {hostname} using DNS server {dns_server}: {str(e)}")
                continue
                
        # Use fallback IP if all resolution attempts fail
        logger.warning(f"Using fallback IP for {hostname}")
        return JUPITER_API_FALLBACK_IP
        
    except Exception as e:
        logger.error(f"Error resolving hostname {hostname}: {str(e)}")
        return JUPITER_API_FALLBACK_IP

class TokenExtensions(BaseModel):
    coingeckoId: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None

class TokenInfo(BaseModel):
    address: str = Field(..., description="Token mint address")
    chainId: Optional[int] = None
    decimals: int = Field(..., description="Token decimals")
    name: str = Field(..., description="Token name")
    symbol: str = Field(..., description="Token symbol")
    logoURI: Optional[str] = Field(None, description="Token logo URL")
    tags: Optional[List[str]] = Field(default_factory=list, description="Token tags")
    extensions: Optional[TokenExtensions] = None
    verified: Optional[bool] = None

class SwapRoute(BaseModel):
    inAmount: str = Field(..., description="Input amount")
    outAmount: str = Field(..., description="Output amount")
    priceImpactPct: str = Field(..., description="Price impact percentage")
    marketInfos: List[Dict[str, Any]] = Field(..., description="Market information")
    amount: str = Field(..., description="Amount")
    slippageBps: int = Field(..., description="Slippage in basis points")
    otherAmountThreshold: str = Field(..., description="Minimum output amount")
    swapMode: str = Field(..., description="Swap mode (ExactIn or ExactOut)")

class QuoteResponse(BaseModel):
    inputMint: str
    outputMint: str
    inAmount: str
    outAmount: str
    otherAmountThreshold: str
    swapMode: str
    slippageBps: int
    priceImpactPct: str
    routePlan: List[Dict[str, Any]]
    contextSlot: int
    timeTaken: float

class Route(BaseModel):
    route_id: str
    in_amount: int
    out_amount: int
    price_impact_pct: float
    market_infos: List[Dict]
    time_taken: float

class TokenPrice(BaseModel):
    """Response model for token price data"""
    id: str = Field(..., description="Token mint address")
    mint: str = Field(..., description="Token mint address")
    price: float = Field(..., description="Token price in USD or relative to vsToken if specified")
    price_24h_change: Optional[float] = Field(None, description="24h price change percentage")
    volume_24h: Optional[float] = Field(None, description="24h trading volume")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "price": 1.000023,
                "price_24h_change": None,
                "volume_24h": None
            }
        }

async def make_http_request(url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Make HTTP request with proper error handling and timeout
    """
    try:
        logger.debug(f"Making HTTP request - URL: {url}, params: {params}")
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, verify=VERIFY_SSL) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Received response: {data}")
            return data
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e.response.text}", exc_info=True)
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"HTTP error: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error occurred: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Request error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@router.get("/quote", response_model=QuoteResponse)
async def get_quote(
    input_mint: str,
    output_mint: str,
    amount: int,
    slippage_bps: Optional[int] = 50,
    only_direct_routes: Optional[bool] = False
):
    """
    Get optimized swap routes from Jupiter Aggregator
    """
    try:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),  # Jupiter expects string amounts
            "slippageBps": slippage_bps,
            "onlyDirectRoutes": only_direct_routes
        }
        
        logger.info(f"Fetching quote for {input_mint} -> {output_mint}")
        response = await make_http_request(f"https://api.jup.ag/swap/v1/quote", params)
        logger.info(f"Got quote response: {response}")
        return QuoteResponse(**response)
    except Exception as e:
        logger.error(f"Error getting quote: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quote: {str(e)}"
        )

@router.get("/routes", response_model=List[Route])
async def get_swap_routes(
    input_mint: str,
    output_mint: str,
    amount: int,
    slippage_bps: Optional[int] = 50,
    only_direct_routes: Optional[bool] = False
):
    """
    Get optimized swap routes from Jupiter Aggregator
    """
    try:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": slippage_bps,
            "onlyDirectRoutes": only_direct_routes,
            "asLegacyTransaction": False
        }
        
        logger.info(f"Fetching routes for {input_mint} -> {output_mint}")
        data = await make_http_request(f"https://api.jup.ag/swap/v1/quote", params)
        
        routes = []
        for route in data.get("routes", []):
            routes.append(Route(
                route_id=route["routeId"],
                in_amount=route["inAmount"],
                out_amount=route["outAmount"],
                price_impact_pct=route["priceImpactPct"],
                market_infos=route["marketInfos"],
                time_taken=route["timeTaken"]
            ))
        logger.info(f"Got {len(routes)} routes")
        return routes
    except Exception as e:
        logger.error(f"Error getting routes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get routes: {str(e)}"
        )

@router.get(
    "/price/{token_mint}",
    response_model=TokenPrice,
    summary="Get token price from Jupiter API",
    description="""
    Get token price and 24h statistics from Jupiter Price API v2.
    
    You can get the price in two ways:
    1. Single token price (in USD): /price/{token_mint}
    2. Token price relative to another token: /price/{token_mint}?vsToken={vs_token_mint}
    
    Examples:
    - Get USDC price: /price/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
    - Get token price vs USDC: /price/{token_mint}?vsToken=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
    """,
    responses={
        200: {
            "description": "Successfully retrieved token price",
            "content": {
                "application/json": {
                    "example": {
                        "id": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                        "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                        "price": 1.000023,
                        "price_24h_change": None,
                        "volume_24h": None
                    }
                }
            }
        },
        404: {
            "description": "Token not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Token {token_mint} not found"}
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to get token price: {error}"}
                }
            }
        }
    }
)
async def get_token_price(
    request: Request,
    token_mint: str,
    vsToken: Optional[str] = Query(
        None,
        description="Optional token mint address to get price relative to. If not provided, returns USD price.",
        example="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    ),
    includeVolume: Optional[bool] = Query(
        True,
        description="Include 24h volume in response. Defaults to true."
    ),
    include24hChange: Optional[bool] = Query(
        True,
        description="Include 24h price change in response. Defaults to true."
    )
):
    """
    Get token price and 24h statistics from Jupiter Price API v2.
    Handles both query parameters and embedded vsToken in path.
    """
    try:
        logger.info(f"Received request for token_mint: {token_mint}")
        
        # Build request parameters
        token_ids = [token_mint]
        if vsToken:
            token_ids.append(vsToken)
        params = {"ids": ",".join(token_ids)}
        
        # Make request to Jupiter API using correct endpoint
        url = f"{JUPITER_API_BASE}/price/{JUPITER_PRICE_API_VERSION}"
        logger.info(f"Making request to Jupiter API - URL: {url}, params: {params}")
        
        response = await make_http_request(url, params)
        logger.info(f"Raw response from Jupiter API: {response}")
        
        if not response or "data" not in response:
            raise HTTPException(
                status_code=500,
                detail="Invalid response from Jupiter API"
            )
        
        prices = response["data"]
        logger.info(f"Prices data: {prices}")
        
        if token_mint not in prices:
            raise HTTPException(
                status_code=404,
                detail=f"Token {token_mint} not found"
            )
        
        token_price = prices[token_mint]
        logger.info(f"Token price data for {token_mint}: {token_price}")
        
        # Handle vs token case
        if vsToken:
            if vsToken not in prices:
                raise HTTPException(
                    status_code=404,
                    detail=f"VS token {vsToken} not found"
                )
                
            vs_token_price = prices[vsToken]
            logger.info(f"VS token price data for {vsToken}: {vs_token_price}")
            
            # Convert prices to float before division
            try:
                token_price_value = float(token_price["price"])
                vs_token_price_value = float(vs_token_price["price"])
                logger.info(f"Converted prices - token: {token_price_value}, vs_token: {vs_token_price_value}")
                relative_price = token_price_value / vs_token_price_value
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Error converting prices: {str(e)}")
                logger.error(f"Token price structure: {token_price}")
                logger.error(f"VS token price structure: {vs_token_price}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing price data: {str(e)}"
                )
            
            # Calculate 24h change if available and requested
            price_24h_change = None
            if include24hChange and token_price.get("price24hChange") is not None and vs_token_price.get("price24hChange") is not None:
                try:
                    token_24h_change = float(token_price["price24hChange"])
                    vs_token_24h_change = float(vs_token_price["price24hChange"])
                    price_24h_change = (
                        (1 + token_24h_change) / 
                        (1 + vs_token_24h_change) - 1
                    ) * 100
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error calculating 24h change: {str(e)}")
            
            # Convert volume to float if present and requested
            volume_24h = None
            if includeVolume and token_price.get("volume24h") is not None:
                try:
                    volume_24h = float(token_price["volume24h"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error converting volume: {str(e)}")
            
            return TokenPrice(
                id=token_mint,
                mint=token_mint,
                price=relative_price,
                price_24h_change=price_24h_change if include24hChange else None,
                volume_24h=volume_24h if includeVolume else None
            )
        
        # Handle single token case
        try:
            price = float(token_price["price"])
            price_24h_change = float(token_price["price24hChange"]) if include24hChange and token_price.get("price24hChange") is not None else None
            volume_24h = float(token_price["volume24h"]) if includeVolume and token_price.get("volume24h") is not None else None
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting single token price data: {str(e)}")
            logger.error(f"Token price structure: {token_price}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing price data: {str(e)}"
            )
            
        return TokenPrice(
            id=token_mint,
            mint=token_mint,
            price=price,
            price_24h_change=price_24h_change if include24hChange else None,
            volume_24h=volume_24h if includeVolume else None
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get token price: {str(e)}"
        )

@router.get("/price/{full_path:path}", response_model=TokenPrice)
async def get_token_price_full_path(
    request: Request,
    full_path: str,
    vsToken: Optional[str] = Query(
        None,
        description="Optional token mint address to get price relative to. If not provided, returns USD price.",
        example="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    ),
    includeVolume: Optional[bool] = Query(
        True,
        description="Include 24h volume in response. Defaults to true."
    ),
    include24hChange: Optional[bool] = Query(
        True,
        description="Include 24h price change in response. Defaults to true."
    )
):
    """
    Get token price and 24h statistics from Jupiter Price API v2.
    Handles both query parameters and embedded vsToken in path.
    """
    try:
        logger.info(f"Received request with full_path: {full_path}")
        
        # Extract token_mint and vsToken from path if embedded
        if '&vsToken=' in full_path:
            parts = full_path.split('&vsToken=')
            token_mint = unquote(parts[0])
            vsToken = unquote(parts[1]) if len(parts) > 1 else vsToken
        else:
            token_mint = unquote(full_path)
            
        logger.info(f"Extracted tokens - token_mint: {token_mint}, vsToken: {vsToken}")
        
        # Build request parameters
        token_ids = [token_mint]
        if vsToken:
            token_ids.append(vsToken)
        params = {"ids": ",".join(token_ids)}
        
        # Make request to Jupiter API using correct endpoint
        url = f"{JUPITER_API_BASE}/price/{JUPITER_PRICE_API_VERSION}"
        logger.info(f"Making request to Jupiter API - URL: {url}, params: {params}")
        
        response = await make_http_request(url, params)
        logger.info(f"Raw response from Jupiter API: {response}")
        
        if not response or "data" not in response:
            raise HTTPException(
                status_code=500,
                detail="Invalid response from Jupiter API"
            )
        
        prices = response["data"]
        logger.info(f"Prices data: {prices}")
        
        if token_mint not in prices:
            raise HTTPException(
                status_code=404,
                detail=f"Token {token_mint} not found"
            )
        
        token_price = prices[token_mint]
        logger.info(f"Token price data for {token_mint}: {token_price}")
        
        # Handle vs token case
        if vsToken:
            if vsToken not in prices:
                raise HTTPException(
                    status_code=404,
                    detail=f"VS token {vsToken} not found"
                )
                
            vs_token_price = prices[vsToken]
            logger.info(f"VS token price data for {vsToken}: {vs_token_price}")
            
            # Convert prices to float before division
            try:
                token_price_value = float(token_price["price"])
                vs_token_price_value = float(vs_token_price["price"])
                logger.info(f"Converted prices - token: {token_price_value}, vs_token: {vs_token_price_value}")
                relative_price = token_price_value / vs_token_price_value
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Error converting prices: {str(e)}")
                logger.error(f"Token price structure: {token_price}")
                logger.error(f"VS token price structure: {vs_token_price}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing price data: {str(e)}"
                )
            
            # Calculate 24h change if available and requested
            price_24h_change = None
            if include24hChange and token_price.get("price24hChange") is not None and vs_token_price.get("price24hChange") is not None:
                try:
                    token_24h_change = float(token_price["price24hChange"])
                    vs_token_24h_change = float(vs_token_price["price24hChange"])
                    price_24h_change = (
                        (1 + token_24h_change) / 
                        (1 + vs_token_24h_change) - 1
                    ) * 100
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error calculating 24h change: {str(e)}")
            
            # Convert volume to float if present and requested
            volume_24h = None
            if includeVolume and token_price.get("volume24h") is not None:
                try:
                    volume_24h = float(token_price["volume24h"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error converting volume: {str(e)}")
            
            return TokenPrice(
                id=token_mint,
                mint=token_mint,
                price=relative_price,
                price_24h_change=price_24h_change if include24hChange else None,
                volume_24h=volume_24h if includeVolume else None
            )
        
        # Handle single token case
        try:
            price = float(token_price["price"])
            price_24h_change = float(token_price["price24hChange"]) if include24hChange and token_price.get("price24hChange") is not None else None
            volume_24h = float(token_price["volume24h"]) if includeVolume and token_price.get("volume24h") is not None else None
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting single token price data: {str(e)}")
            logger.error(f"Token price structure: {token_price}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing price data: {str(e)}"
            )
            
        return TokenPrice(
            id=token_mint,
            mint=token_mint,
            price=price,
            price_24h_change=price_24h_change if include24hChange else None,
            volume_24h=volume_24h if includeVolume else None
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get token price: {str(e)}"
        )

@router.get("/tokens/list", response_model=List[TokenInfo])
async def get_token_list():
    """
    Get list of all tokens from Jupiter's strict token list
    """
    try:
        logger.info("Fetching token list from Jupiter API")
        response = await make_http_request("https://token.jup.ag/strict")
        
        if not response or not isinstance(response, list):
            logger.error(f"Invalid response from Jupiter API: {response}")
            raise HTTPException(
                status_code=500,
                detail="Invalid response from Jupiter API"
            )
            
        logger.info(f"Got token list with {len(response)} tokens")
        
        # Log sample token data for debugging
        if len(response) > 0:
            sample = response[0]
            logger.info(f"Sample raw token data: {sample}")
        
        # Convert each token dict to a TokenInfo model
        tokens = []
        for token_data in response:
            try:
                # Ensure tags is a list
                if 'tags' in token_data and token_data['tags'] is None:
                    token_data['tags'] = []
                elif 'tags' not in token_data:
                    token_data['tags'] = []
                    
                # Ensure verified field exists
                if 'verified' not in token_data:
                    token_data['verified'] = None
                
                token = TokenInfo(**token_data)
                tokens.append(token)
                
                # Log token details for debugging
                logger.debug(f"Parsed token: {token.symbol} - Tags: {token.tags}, Verified: {token.verified}")
                
            except Exception as e:
                logger.error(f"Error parsing token data: {token_data} - Error: {str(e)}")
                continue
        
        logger.info(f"Successfully parsed {len(tokens)} tokens")
        if tokens:
            sample = tokens[0]
            logger.info(f"Sample parsed token - Symbol: {sample.symbol}, Tags: {sample.tags}, Verified: {sample.verified}")
        
        return tokens
        
    except Exception as e:
        logger.error(f"Error fetching token list: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch token list: {str(e)}"
        )

@router.get("/tokens/info/{token_mint}", response_model=TokenInfo)
async def get_token_info(token_mint: str):
    """
    Get token information from the token list
    """
    try:
        logger.info(f"Fetching token info for {token_mint}")
        token_list = await get_token_list()
        token = next((t for t in token_list if t.address == token_mint), None)
        if token:
            logger.info(f"Got token info for {token_mint}")
            return token
        else:
            logger.error(f"Token {token_mint} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Token {token_mint} not found"
            )
    except Exception as e:
        logger.error(f"Error fetching token info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch token info: {str(e)}"
        )

@router.get("/tokens/popular", response_model=List[TokenInfo])
async def get_popular_tokens(limit: int = 20):
    """
    Get list of popular tokens sorted by volume
    """
    try:
        logger.info(f"Fetching popular tokens with limit {limit}")
        # Get all tokens
        all_tokens = await get_token_list()
        logger.info(f"Got {len(all_tokens)} tokens")
        
        # Filter for tokens we want to consider as popular
        # Priority: SOL, USDC, USDT, and other major tokens
        priority_symbols = {"SOL", "USDC", "USDT", "ETH", "BTC", "JUP", "BONK", "RAY"}
        
        # First, get priority tokens
        priority_tokens = [
            token for token in all_tokens 
            if token.symbol in priority_symbols
        ]
        logger.info(f"Found {len(priority_tokens)} priority tokens")
        
        # Then get other verified tokens
        other_tokens = [
            token for token in all_tokens 
            if token.symbol not in priority_symbols 
            and getattr(token, 'verified', False)
        ]
        logger.info(f"Found {len(other_tokens)} other verified tokens")
        
        # Sort other tokens by symbol
        other_tokens.sort(key=lambda x: x.symbol)
        
        # Combine priority tokens with other tokens
        popular_tokens = priority_tokens + other_tokens
        
        # Limit the results
        result = popular_tokens[:limit]
        logger.info(f"Returning {len(result)} popular tokens")
        
        # Log some sample data for debugging
        if result:
            logger.info(f"Sample popular token - Symbol: {result[0].symbol}, Address: {result[0].address}")
        
        return result
    except Exception as e:
        logger.error(f"Error fetching popular tokens: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch popular tokens: {str(e)}"
        )

@router.get("/tokens/tradable", response_model=List[TokenInfo])
async def get_tradable_tokens():
    """
    Get all token mints that are tradable on Jupiter
    """
    try:
        # Get all tokens first
        all_tokens = await get_token_list()
        logger.info(f"Retrieved {len(all_tokens)} tokens from token list")
        
        # A token is considered tradable if it's verified either through the verified field or verified tag
        tradable_tokens = []
        for token in all_tokens:
            # Check both verification methods:
            # 1. verified field being True 
            # 2. 'verified' tag in tags array
            is_verified = (
                getattr(token, 'verified', False) is True or  # Check verified field
                (token.tags and 'verified' in [t.lower() for t in token.tags])  # Check verified tag
            )
            
            if is_verified:
                tradable_tokens.append(token)
                logger.info(f"Added tradable token: {token.symbol} - Verified status: {getattr(token, 'verified', None)}, Tags: {token.tags}")
        
        logger.info(f"Found {len(tradable_tokens)} tradable tokens")
        if tradable_tokens:
            sample = tradable_tokens[0]
            logger.info(f"Sample tradable token - Symbol: {sample.symbol}, Tags: {sample.tags}, Verified: {getattr(sample, 'verified', None)}")
        else:
            logger.warning("No tradable tokens found")
        
        # Sort by symbol for consistent ordering
        tradable_tokens.sort(key=lambda x: x.symbol)
        
        return tradable_tokens
    except Exception as e:
        logger.error(f"Error fetching tradable tokens: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch tradable tokens: {str(e)}"
        )

@router.get("/tokens/tagged", response_model=List[TokenInfo])
async def get_tagged_tokens(
    tag: Optional[str] = None
):
    """
    Get tokens with specific tags
    """
    try:
        if not tag:
            raise HTTPException(status_code=400, detail="Tag parameter is required")
            
        logger.info(f"Getting tokens with tag: {tag}")
        all_tokens = await get_token_list()
        
        # Special handling for 'verified' tag
        if tag.lower() == 'verified':
            tagged_tokens = []
            for token in all_tokens:
                # Check both the verified field and 'verified' tag
                is_verified = (
                    getattr(token, 'verified', False) or  # Check verified field
                    (token.tags and 'verified' in [t.lower() for t in token.tags]) or  # Check for 'verified' tag
                    (token.tags and 'old-registry' in [t.lower() for t in token.tags])  # Consider old-registry tokens as verified
                )
                if is_verified:
                    tagged_tokens.append(token)
        else:
            # For other tags, do case-insensitive matching
            tagged_tokens = [
                token for token in all_tokens 
                if token.tags and tag.lower() in [t.lower() for t in token.tags]
            ]
        
        logger.info(f"Found {len(tagged_tokens)} tokens with tag '{tag}'")
        if tagged_tokens:
            sample = tagged_tokens[0]
            logger.info(f"Sample tagged token - Symbol: {sample.symbol}, Tags: {sample.tags}, Verified: {getattr(sample, 'verified', None)}")
        
        return tagged_tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tagged tokens: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tagged tokens: {str(e)}"
        )

@router.get("/market-depth")
async def get_market_depth(
    input_mint: str,
    output_mint: str,
    amount: Optional[int] = None,
    depth: Optional[int] = 5
):
    """
    Get market depth information for a token pair
    """
    try:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "depth": depth
        }
        if amount is not None:
            params["amount"] = str(amount)
        
        logger.info(f"Fetching market depth for {input_mint} -> {output_mint}")
        response = await make_http_request(f"https://api.jup.ag/swap/v1/market-depth", params)
        
        if response:
            logger.info(f"Got market depth data with {len(response.get('items', []))} items")
        
        return response
    except Exception as e:
        logger.error(f"Error fetching market depth: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market depth: {str(e)}"
        )

@router.get("/tokens/market/{market_address}/mints")
async def get_market_tokens(market_address: str):
    """
    Get list of token mints that belong to a specific market/pool address
    """
    try:
        logger.info(f"Fetching market tokens for {market_address}")
        return await make_http_request(f"https://token.jup.ag/market/{market_address}/mints")
    except Exception as e:
        logger.error(f"Error fetching market tokens: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Market {market_address} not found")

@router.get("/tokens/all", response_model=List[TokenInfo])
async def get_all_tokens():
    """
    Get comprehensive list of all tokens with their information
    """
    try:
        logger.info("Fetching all tokens")
        response = await make_http_request(f"https://token.jup.ag/all")
        logger.info(f"Got all tokens with {len(response)} tokens")
        
        if not response:
            logger.warning("Empty response from Jupiter API")
            return []
            
        # Ensure we're getting the expected format
        if isinstance(response, list):
            return [TokenInfo(**token) for token in response]
        elif isinstance(response, dict) and "tokens" in response:
            return [TokenInfo(**token) for token in response["tokens"]]
        else:
            logger.error(f"Unexpected response format: {response}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching all tokens: {str(e)}")
        # Re-raise with more detail for debugging
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch all tokens: {str(e)}"
        )

@router.get("/tokens/new", response_model=List[TokenInfo])
async def get_new_tokens(limit: int = 20):
    """
    Get list of newly added tokens on Jupiter
    """
    try:
        # Get all tokens
        all_tokens = await get_token_list()
        logger.info(f"Retrieved {len(all_tokens)} tokens from token list")
        
        # Sort tokens by verification status and then by symbol
        # For demo purposes, we'll consider the last N tokens as "new"
        new_tokens = sorted(
            all_tokens,
            key=lambda x: (getattr(x, 'verified', False), x.symbol),
            reverse=True
        )[:limit]
        
        logger.info(f"Returning {len(new_tokens)} new tokens")
        if new_tokens:
            logger.info(f"Sample new token - Symbol: {new_tokens[0].symbol}, Address: {new_tokens[0].address}")
        
        return new_tokens
    except Exception as e:
        logger.error(f"Error fetching new tokens: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch new tokens: {str(e)}"
        )

        new_tokens = sorted(
            all_tokens,
            key=lambda x: (getattr(x, 'verified', False), x.symbol),
            reverse=True
        )[:limit]
        
        logger.info(f"Returning {len(new_tokens)} new tokens")
        if new_tokens:
            logger.info(f"Sample new token - Symbol: {new_tokens[0].symbol}, Address: {new_tokens[0].address}")
        
        return new_tokens
    except Exception as e:
        logger.error(f"Error fetching new tokens: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch new tokens: {str(e)}"
        )
