from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import aiohttp
import os

router = APIRouter(tags=["Helius"])

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
HELIUS_BASE_URL = "https://api.helius.xyz/v0"

class TokenMetadata(BaseModel):
    mint: str
    name: str
    symbol: str
    decimals: int
    image_uri: Optional[str] = None
    collection: Optional[Dict[str, Any]] = None
    attributes: Optional[List[Dict[str, Any]]] = None

class TokenBalance(BaseModel):
    mint: str
    amount: float
    decimals: int

class TokenHistory(BaseModel):
    signature: str
    type: str
    timestamp: int
    slot: int
    fee: int
    amount: float
    mint: str

async def make_helius_request(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make a request to Helius API with error handling"""
    try:
        url = f"{HELIUS_BASE_URL}{endpoint}"
        if not params:
            params = {}
        params["api-key"] = HELIUS_API_KEY

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 429:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                elif response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Helius API error: {await response.text()}"
                    )
                return await response.json()
                
    except aiohttp.ClientError as e:
        logging.error(f"Error making Helius request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/token/{mint}/metadata", response_model=TokenMetadata)
async def get_token_metadata(mint: str):
    """Get token metadata from Helius"""
    try:
        response = await make_helius_request(f"/token-metadata/{mint}")
        return TokenMetadata(**response)
    except Exception as e:
        logging.error(f"Error getting token metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/address/{address}/balances", response_model=List[TokenBalance])
async def get_token_balances(address: str):
    """Get token balances for an address"""
    try:
        response = await make_helius_request(f"/addresses/{address}/balances")
        return [TokenBalance(**balance) for balance in response.get("tokens", [])]
    except Exception as e:
        logging.error(f"Error getting token balances: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/token/{mint}/history", response_model=List[TokenHistory])
async def get_token_history(
    mint: str,
    limit: int = Query(default=10, ge=1, le=100),
    before: Optional[str] = None
):
    """Get token transaction history"""
    try:
        params = {"limit": limit}
        if before:
            params["before"] = before
            
        response = await make_helius_request(f"/token-history/{mint}", params)
        return [TokenHistory(**tx) for tx in response]
    except Exception as e:
        logging.error(f"Error getting token history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/priority-fee")
async def get_priority_fee(
    accounts: List[str] = Query(..., description="List of account addresses involved in the transaction")
):
    """Get current priority fee estimate"""
    try:
        response = await make_helius_request("/priority-fees", {"accounts": accounts})
        return response
    except Exception as e:
        logging.error(f"Error getting priority fee: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
