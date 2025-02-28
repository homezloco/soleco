from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel, Field
import aiohttp
import os
from datetime import datetime

router = APIRouter(tags=["RugCheck"])

RUGCHECK_API_KEY = os.getenv("RUGCHECK_API_KEY", "")
RUGCHECK_BASE_URL = "https://api.rugcheck.xyz/v1"

class TokenRiskProfile(BaseModel):
    mint: str
    symbol: str
    name: str
    risk_score: float = Field(..., description="Overall risk score (0-100)")
    risk_level: str = Field(..., description="Risk categorization (Low/Medium/High)")
    
    # Detailed risk components
    liquidity_risk: Optional[float] = None
    holder_concentration: Optional[float] = None
    trading_volume_risk: Optional[float] = None
    contract_risk: Optional[float] = None
    
    # Additional metadata
    creation_date: Optional[datetime] = None
    total_supply: Optional[int] = None
    max_wallet_holding: Optional[float] = None

class AuthResponse(BaseModel):
    token: str
    expires_at: datetime

async def make_rugcheck_request(
    endpoint: str, 
    method: str = "GET", 
    params: Optional[Dict[str, Any]] = None, 
    json_data: Optional[Dict[str, Any]] = None,
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """Make a request to RugCheck API with error handling"""
    try:
        url = f"{RUGCHECK_BASE_URL}{endpoint}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, params=params, headers=headers) as response:
                    return await _handle_response(response)
            elif method == "POST":
                async with session.post(url, json=json_data, headers=headers) as response:
                    return await _handle_response(response)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
    except aiohttp.ClientError as e:
        logging.error(f"Error making RugCheck request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def _handle_response(response):
    """Handle API response with error checking"""
    if response.status == 429:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    elif response.status != 200:
        error_text = await response.text()
        raise HTTPException(
            status_code=response.status,
            detail=f"RugCheck API error: {error_text}"
        )
    return await response.json()

@router.post("/auth/login")
async def solana_login(
    wallet_signature: str = Header(..., description="Signed message from wallet"),
    wallet_address: str = Header(..., description="Solana wallet address")
):
    """
    Login to RugCheck via a signed Solana message.
    Requires the user to sign a message with their wallet.
    """
    try:
        response = await make_rugcheck_request("/auth/login/solana", method="POST", json_data={
            "wallet_address": wallet_address,
            "signature": wallet_signature
        })
        return AuthResponse(**response)
    except Exception as e:
        logging.error(f"RugCheck login error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")

@router.get("/token/{mint}/risk", response_model=TokenRiskProfile)
async def get_token_risk_profile(
    mint: str,
    auth_token: Optional[str] = Header(None)
):
    """
    Get comprehensive risk profile for a Solana token.
    Requires authentication.
    """
    try:
        if not auth_token:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        response = await make_rugcheck_request(f"/token/{mint}/risk", auth_token=auth_token)
        return TokenRiskProfile(**response)
    except Exception as e:
        logging.error(f"Error getting token risk profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tokens/trending", response_model=List[TokenRiskProfile])
async def get_trending_tokens(
    auth_token: Optional[str] = Header(None),
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Get list of trending tokens with their risk profiles.
    Requires authentication.
    """
    try:
        if not auth_token:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        response = await make_rugcheck_request("/tokens/trending", 
                                               params={"limit": limit}, 
                                               auth_token=auth_token)
        return [TokenRiskProfile(**token) for token in response]
    except Exception as e:
        logging.error(f"Error getting trending tokens: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
