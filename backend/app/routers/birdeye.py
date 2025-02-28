from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
import httpx
from pydantic import BaseModel

router = APIRouter()

# Birdeye API base URL
BIRDEYE_API_BASE = "https://api.birdeye.so/v1"

class TokenInfo(BaseModel):
    address: str
    symbol: str
    name: str
    price: float
    volume_24h: float

@router.get("/token/{token_address}", response_model=TokenInfo)
async def get_token_info(
    token_address: str,
    x_api_key: str = Header(..., description="Birdeye API Key")
):
    """
    Get detailed token information from Birdeye
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BIRDEYE_API_BASE}/token/info",
                params={"address": token_address},
                headers={"X-API-KEY": x_api_key}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Birdeye API error")
            
            data = response.json()["data"]
            return TokenInfo(
                address=data["address"],
                symbol=data["symbol"],
                name=data["name"],
                price=float(data["price"]),
                volume_24h=float(data["volume24h"])
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pairs/{token_address}")
async def get_token_pairs(
    token_address: str,
    x_api_key: str = Header(..., description="Birdeye API Key")
):
    """
    Get trading pairs for a token from Birdeye
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BIRDEYE_API_BASE}/pairs",
                params={"token_address": token_address},
                headers={"X-API-KEY": x_api_key}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Birdeye API error")
            
            return response.json()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
