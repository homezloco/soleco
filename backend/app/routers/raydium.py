from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
import httpx
from pydantic import BaseModel
import logging
from enum import Enum
from fastapi import Query

router = APIRouter()

# Raydium API V3 base URL
RAYDIUM_API_BASE = "https://api-v3.raydium.io"

class RaydiumResponse(BaseModel):
    id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    msg: Optional[str] = None

class TokenInfo(BaseModel):
    chainId: int
    address: str
    symbol: str
    name: str
    decimals: int
    logoURI: Optional[str] = None

class PoolInfo(BaseModel):
    type: str
    programId: str
    id: str
    mintA: TokenInfo
    mintB: TokenInfo
    lpMint: str
    version: int
    liquidity: float
    volume24h: float
    volume7d: float
    volume30d: float
    fee24h: float
    fee7d: float
    fee30d: float
    apr24h: float
    apr7d: float
    apr30d: float

class PoolList(BaseModel):
    count: int
    data: List[PoolInfo]

class PoolType(str, Enum):
    all = "all"
    concentrated = "concentrated"
    standard = "standard"
    all_farm = "allFarm"
    concentrated_farm = "concentratedFarm"
    standard_farm = "standardFarm"

class PoolSortField(str, Enum):
    default = "default"
    liquidity = "liquidity"
    volume_24h = "volume24h"
    fee_24h = "fee24h"
    apr_24h = "apr24h"
    volume_7d = "volume7d"
    fee_7d = "fee7d"
    apr_7d = "apr7d"
    volume_30d = "volume30d"
    fee_30d = "fee30d"
    apr_30d = "apr30d"

class SortType(str, Enum):
    desc = "desc"
    asc = "asc"

class VersionInfo(BaseModel):
    latest: str
    least: str

class MarketInfo(BaseModel):
    volume24: float
    tvl: float

class MintInfo(BaseModel):
    chainId: int
    address: str
    symbol: str
    name: str
    decimals: int
    logoURI: Optional[str] = None
    tags: Optional[List[str]] = None
    extensions: Optional[Dict[str, Any]] = None

class MintList(BaseModel):
    blacklist: List[str]
    mintList: List[MintInfo]

async def make_raydium_request(endpoint: str) -> Dict[str, Any]:
    """Make a request to Raydium API with error handling"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{RAYDIUM_API_BASE}{endpoint}")
            response.raise_for_status()
            
            data = response.json()
            if not data.get('success'):
                raise HTTPException(status_code=400, detail=data.get('msg', 'Raydium API error'))
            
            return data.get('data', {})
    except httpx.HTTPError as e:
        logging.error(f"Raydium API error: {str(e)}")
        raise HTTPException(status_code=e.response.status_code if hasattr(e, 'response') else 500, 
                          detail=f"Raydium API error: {str(e)}")
    except Exception as e:
        logging.error(f"Error making Raydium request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/version", response_model=VersionInfo)
async def get_version():
    """Get UI V3 current version"""
    return await make_raydium_request("/main/version")

@router.get("/rpcs")
async def get_rpcs():
    """Get UI RPCs"""
    return await make_raydium_request("/main/rpcs")

@router.get("/chain-time")
async def get_chain_time():
    """Get chain time"""
    return await make_raydium_request("/main/chain-time")

@router.get("/info", response_model=MarketInfo)
async def get_info():
    """Get TVL and 24 hour volume"""
    return await make_raydium_request("/main/info")

@router.get("/pools", response_model=PoolList)
async def get_pools(
    pool_type: PoolType = Query(PoolType.all, description="Pool type"),
    sort_field: PoolSortField = Query(PoolSortField.default, description="Field to sort by"),
    sort_type: SortType = Query(SortType.desc, description="Sort direction"),
    page_size: int = Query(default=100, ge=1, le=1000, description="Page size, max 1000"),
    page: int = Query(default=1, ge=1, description="Page index")
):
    """Get list of Raydium pools with pagination and sorting"""
    params = {
        "poolType": pool_type.value,
        "poolSortField": sort_field.value,
        "sortType": sort_type.value,
        "pageSize": page_size,
        "page": page
    }
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return await make_raydium_request(f"/pools/info/list?{query_string}")

@router.get("/pools/{pool_id}")
async def get_pool_info(pool_id: str):
    """Get pool info by ID"""
    return await make_raydium_request(f"/pools/info/ids?ids=[{pool_id}]")

@router.get("/pools/by-lp/{lp_mint}")
async def get_pool_by_lp(lp_mint: str):
    """Get pool info by LP mint"""
    return await make_raydium_request(f"/pools/info/lps?lps=[{lp_mint}]")

@router.get("/pools/by-token/{token_mint}")
async def get_pool_by_token(token_mint: str):
    """Get pool info by token mint"""
    return await make_raydium_request(f"/pools/info/mint?mint={token_mint}")

@router.get("/pools/{pool_id}/liquidity")
async def get_pool_liquidity(pool_id: str):
    """Get pool liquidity history"""
    return await make_raydium_request(f"/pools/line/liquidity?poolId={pool_id}")

@router.get("/pools/{pool_id}/position")
async def get_pool_position(pool_id: str):
    """Get CLMM position"""
    return await make_raydium_request(f"/pools/line/position?poolId={pool_id}")

@router.get("/farms")
async def get_farms():
    """Get farm pool info"""
    return await make_raydium_request("/farms/info/ids")

@router.get("/farms/by-lp/{lp_mint}")
async def get_farm_by_lp(lp_mint: str):
    """Get farm info by LP mint"""
    return await make_raydium_request(f"/farms/info/lp?lp={lp_mint}")

@router.get("/mints", response_model=MintList)
async def get_mints():
    """Get default mint list"""
    return await make_raydium_request("/mint/list")

@router.get("/mints/{mint_id}")
async def get_mint_info(mint_id: str):
    """Get mint info"""
    return await make_raydium_request(f"/mint/ids?ids=[{mint_id}]")

@router.get("/mints/{mint_id}/price")
async def get_mint_price(mint_id: str):
    """Get mint price"""
    return await make_raydium_request(f"/mint/price?ids=[{mint_id}]")

@router.get("/price/{token_mint}")
async def get_token_price(token_mint: str):
    """
    Get token price from Raydium
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{RAYDIUM_API_BASE}/main/price", params={"tokens": token_mint})
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Raydium API error")
            
            data = response.json()
            return {
                "price": data.get(token_mint, 0),
                "token_mint": token_mint
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TokenMarketInfo(BaseModel):
    mint: str
    symbol: str
    name: str
    price: Optional[float] = None
    volume24h: float = 0
    tvl: float = 0
    apr24h: Optional[float] = None
    pools: List[str] = []

class TopTokensResponse(BaseModel):
    tokens: List[TokenMarketInfo]

@router.get("/market/top-tokens", response_model=TopTokensResponse)
async def get_top_tokens(
    sort_by: str = Query("volume24h", enum=["volume24h", "tvl", "apr24h"]),
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Get top tokens by volume, TVL, or APR.
    Combines data from pools and mints to provide comprehensive token metrics.
    """
    try:
        logging.info("Getting pools data...")
        pools_data = await get_pools(
            pool_type=PoolType.all,
            sort_field=PoolSortField.volume_24h,
            sort_type=SortType.desc,
            page_size=1000,
            page=1
        )
        logging.info(f"Got pools data with {len(pools_data.get('data', []))} pools")
        
        logging.info("Getting mint list...")
        mint_list_response = await get_mints()
        mint_list = mint_list_response.get('mintList', [])
        mint_map = {mint['address']: mint for mint in mint_list}
        logging.info(f"Got {len(mint_map)} mints")
        
        # Track token metrics
        token_metrics: Dict[str, TokenMarketInfo] = {}
        
        # Process pool data to aggregate token metrics
        pools = pools_data.get('data', [])
        logging.info(f"Processing {len(pools)} pools")
        
        for pool in pools:
            try:
                for mint_side in ['mintA', 'mintB']:
                    mint = pool[mint_side]['address']
                    if mint not in token_metrics:
                        token_metrics[mint] = TokenMarketInfo(
                            mint=mint,
                            symbol=pool[mint_side].get('symbol', ''),
                            name=pool[mint_side].get('name', ''),
                            volume24h=0,
                            tvl=0,
                            pools=[]
                        )
                    
                    # Add pool metrics to token
                    metrics = token_metrics[mint]
                    volume = float(pool.get('volume24h', 0)) / 2
                    tvl = float(pool.get('liquidity', 0)) / 2
                    apr = float(pool.get('apr24h', 0)) if pool.get('apr24h') else None
                    
                    metrics.volume24h += volume
                    metrics.tvl += tvl
                    if apr:
                        if not metrics.apr24h or apr > metrics.apr24h:
                            metrics.apr24h = apr
                    metrics.pools.append(pool['id'])
            except Exception as e:
                logging.error(f"Error processing pool {pool.get('id')}: {str(e)}")
                continue
        
        logging.info(f"Processed {len(token_metrics)} tokens")
        
        # Sort tokens by requested metric
        sorted_tokens = sorted(
            token_metrics.values(),
            key=lambda x: getattr(x, sort_by, 0) or 0,
            reverse=True
        )
        
        result = TopTokensResponse(tokens=sorted_tokens[:limit])
        logging.info(f"Returning {len(result.tokens)} tokens")
        return result
        
    except Exception as e:
        logging.error(f"Error getting top tokens: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class PoolOpportunity(BaseModel):
    pool_id: str
    token_a: str
    token_b: str
    apr24h: float
    volume24h: float
    tvl: float
    type: str

class PoolOpportunitiesResponse(BaseModel):
    opportunities: List[PoolOpportunity]

@router.get("/market/opportunities", response_model=PoolOpportunitiesResponse)
async def get_pool_opportunities(
    min_apr: float = Query(default=0, ge=0),
    min_volume: float = Query(default=0, ge=0),
    min_tvl: float = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Find pool opportunities based on APR, volume, and TVL thresholds.
    Returns pools that meet all specified criteria, sorted by APR.
    """
    try:
        logging.info(f"Getting pools data for opportunities with criteria: min_apr={min_apr}, min_volume={min_volume}, min_tvl={min_tvl}")
        pools_data = await get_pools(
            pool_type=PoolType.all,
            sort_field=PoolSortField.apr_24h,
            sort_type=SortType.desc,
            page_size=1000,
            page=1
        )
        
        opportunities = []
        pools = pools_data.get('data', [])
        logging.info(f"Processing {len(pools)} pools for opportunities")
        
        for pool in pools:
            try:
                apr = float(pool.get('apr24h', 0))
                volume = float(pool.get('volume24h', 0))
                tvl = float(pool.get('liquidity', 0))
                
                logging.info(f"Pool {pool['id']}: apr={apr}, volume={volume}, tvl={tvl}")
                
                if apr >= min_apr and volume >= min_volume and tvl >= min_tvl:
                    logging.info(f"Found matching pool: {pool['id']}")
                    opportunities.append(PoolOpportunity(
                        pool_id=pool['id'],
                        token_a=f"{pool['mintA']['symbol']} ({pool['mintA']['address']})",
                        token_b=f"{pool['mintB']['symbol']} ({pool['mintB']['address']})",
                        apr24h=apr,
                        volume24h=volume,
                        tvl=tvl,
                        type=pool['type']
                    ))
                    
                    if len(opportunities) >= limit:
                        break
            except Exception as e:
                logging.error(f"Error processing pool opportunity {pool.get('id')}: {str(e)}")
                continue
        
        logging.info(f"Found {len(opportunities)} opportunities matching criteria")
        return PoolOpportunitiesResponse(opportunities=opportunities)
        
    except Exception as e:
        logging.error(f"Error getting pool opportunities: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
