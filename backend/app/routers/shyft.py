from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import aiohttp
import os

router = APIRouter(tags=["Shyft"])

SHYFT_API_KEY = os.getenv("SHYFT_API_KEY", "")
SHYFT_BASE_URL = "https://api.shyft.to/sol/v1"

class WalletToken(BaseModel):
    address: str
    associated_token_address: str
    balance: float
    info: Dict[str, Any]
    token_address: str

class WalletPortfolio(BaseModel):
    tokens: List[WalletToken]
    sol_balance: float
    total_value_usd: float

class NFTToken(BaseModel):
    name: str
    symbol: str
    royalty: int
    image_uri: str
    collection: Optional[str] = None
    attributes: Optional[List[Dict[str, Any]]] = None
    owner: str

async def make_shyft_request(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make a request to SHYFT API with error handling"""
    try:
        url = f"{SHYFT_BASE_URL}{endpoint}"
        headers = {
            "x-api-key": SHYFT_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 429:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                elif response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"SHYFT API error: {await response.text()}"
                    )
                return await response.json()
                
    except aiohttp.ClientError as e:
        logging.error(f"Error making SHYFT request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallet/{address}/portfolio", response_model=WalletPortfolio)
async def get_wallet_portfolio(address: str):
    """Get wallet portfolio summary"""
    try:
        response = await make_shyft_request("/wallet/get_portfolio", {"wallet": address})
        return WalletPortfolio(**response.get("result", {}))
    except Exception as e:
        logging.error(f"Error getting wallet portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallet/{address}/tokens", response_model=List[WalletToken])
async def get_wallet_tokens(
    address: str,
    network: str = Query(default="mainnet-beta", enum=["mainnet-beta", "devnet"])
):
    """Get wallet token holdings"""
    try:
        response = await make_shyft_request("/wallet/all_tokens", {
            "wallet": address,
            "network": network
        })
        return [WalletToken(**token) for token in response.get("result", [])]
    except Exception as e:
        logging.error(f"Error getting wallet tokens: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/token/{mint}/holders", response_model=List[Dict[str, Any]])
async def get_token_holders(
    mint: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """Get token holder list"""
    try:
        response = await make_shyft_request("/token/holders", {
            "token_address": mint,
            "limit": limit,
            "offset": offset
        })
        return response.get("result", [])
    except Exception as e:
        logging.error(f"Error getting token holders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nft/{mint}", response_model=NFTToken)
async def get_nft_details(mint: str):
    """Get NFT metadata and details"""
    try:
        response = await make_shyft_request("/nft/read", {"token_address": mint})
        return NFTToken(**response.get("result", {}))
    except Exception as e:
        logging.error(f"Error getting NFT details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
