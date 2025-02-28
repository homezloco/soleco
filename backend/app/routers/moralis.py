from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import aiohttp
import os
from datetime import datetime

router = APIRouter(tags=["Moralis"])

MORALIS_API_KEY = os.getenv("MORALIS_API_KEY", "")
MORALIS_BASE_URL = "https://solana-gateway.moralis.io"

class SwapTransaction(BaseModel):
    signature: str
    block_timestamp: datetime
    success: bool
    fee: float
    token_in: Dict[str, Any]
    token_out: Dict[str, Any]
    amount_in: float
    amount_out: float
    price_impact: Optional[float] = None
    exchange: str

class NFTTransfer(BaseModel):
    signature: str
    block_timestamp: datetime
    from_address: str
    to_address: str
    mint: str
    amount: int

async def make_moralis_request(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make a request to Moralis API with error handling"""
    try:
        url = f"{MORALIS_BASE_URL}{endpoint}"
        headers = {
            "X-API-Key": MORALIS_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 429:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                elif response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Moralis API error: {await response.text()}"
                    )
                return await response.json()
                
    except aiohttp.ClientError as e:
        logging.error(f"Error making Moralis request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/token/{address}/swaps", response_model=List[SwapTransaction])
async def get_token_swaps(
    address: str,
    network: str = Query(default="mainnet", enum=["mainnet", "devnet"]),
    limit: int = Query(default=100, ge=1, le=500),
    cursor: Optional[str] = None
):
    """
    Get all swap transactions for a token, including:
    - Buy transactions
    - Sell transactions
    - Add liquidity
    - Remove liquidity
    """
    try:
        params = {
            "network": network,
            "limit": limit
        }
        if cursor:
            params["cursor"] = cursor
            
        response = await make_moralis_request(f"/token/{address}/swaps", params)
        return [SwapTransaction(**swap) for swap in response.get("result", [])]
    except Exception as e:
        logging.error(f"Error getting token swaps: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/address/{address}/nft/transfers", response_model=List[NFTTransfer])
async def get_nft_transfers(
    address: str,
    network: str = Query(default="mainnet", enum=["mainnet", "devnet"]),
    limit: int = Query(default=100, ge=1, le=500),
    cursor: Optional[str] = None
):
    """Get all NFT transfers for an address (both sent and received)"""
    try:
        params = {
            "network": network,
            "limit": limit
        }
        if cursor:
            params["cursor"] = cursor
            
        response = await make_moralis_request(f"/address/{address}/nft/transfers", params)
        return [NFTTransfer(**transfer) for transfer in response.get("result", [])]
    except Exception as e:
        logging.error(f"Error getting NFT transfers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/token/{address}/price")
async def get_token_price(
    address: str,
    network: str = Query(default="mainnet", enum=["mainnet", "devnet"])
):
    """Get current token price and 24h price change"""
    try:
        response = await make_moralis_request(f"/token/{address}/price", {
            "network": network
        })
        return response.get("result", {})
    except Exception as e:
        logging.error(f"Error getting token price: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/tokens")
async def get_market_tokens(
    network: str = Query(default="mainnet", enum=["mainnet", "devnet"]),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="volume_24h", enum=["volume_24h", "market_cap", "price_change_24h"])
):
    """Get list of tokens with market data, sorted by specified metric"""
    try:
        response = await make_moralis_request("/market/tokens", {
            "network": network,
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by
        })
        return response.get("result", [])
    except Exception as e:
        logging.error(f"Error getting market tokens: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
