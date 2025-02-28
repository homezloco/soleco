"""
Models for coin and token data.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class TokenMetadata(BaseModel):
    """Token metadata model."""
    name: str
    symbol: str
    logo_uri: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None
    discord: Optional[str] = None
    telegram: Optional[str] = None

class TokenSupply(BaseModel):
    """Token supply information."""
    total: int
    circulating: Optional[int] = None
    max: Optional[int] = None
    decimals: int = 9

class TokenPrice(BaseModel):
    """Token price information."""
    current: float
    change_24h: Optional[float] = None
    change_7d: Optional[float] = None
    ath: Optional[float] = None
    ath_date: Optional[datetime] = None
    atl: Optional[float] = None
    atl_date: Optional[datetime] = None

class MarketData(BaseModel):
    """Market data for a token."""
    market_cap: Optional[float] = None
    fully_diluted_valuation: Optional[float] = None
    volume_24h: Optional[float] = None
    volume_change_24h: Optional[float] = None
    price: Optional[TokenPrice] = None
    liquidity: Optional[float] = None
    liquidity_change_24h: Optional[float] = None

class CoinData(BaseModel):
    """Comprehensive coin/token data model."""
    id: str
    mint_address: str
    metadata: TokenMetadata
    supply: TokenSupply
    market_data: Optional[MarketData] = None
    created_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = []
    is_verified: bool = False
    is_scam: bool = False
    risk_score: Optional[int] = None
    additional_data: Dict[str, Any] = {}
