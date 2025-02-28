import sys
import os
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential

# Custom exceptions
from .exceptions import TokenNotFoundError, TransactionFailedError, ConfigurationError

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Retry decorator for trade operations
def trade_retry(func):
    @wraps(func)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry_error_callback=lambda retry_state: None
    )
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Trade operation failed: {e}")
            raise
    return wrapper

from .pump_fun import buy, sell
from .config import client, payer_keypair, validate_configuration, NETWORK_DIAGNOSTICS
from .coin_data import get_coin_data
from .wallet_management import WalletManager

# Decorator for authentication and error handling
def handle_trade_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # Add authentication check if needed
            if not client or not payer_keypair:
                raise HTTPException(status_code=403, detail="Wallet not configured")
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Trade error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    return wrapper

# Main Pump.fun Router
router = APIRouter(prefix="/pumpfun", tags=["Pump.fun Trading"])

# Trading Router for Frontend
trade_router = APIRouter(prefix="/trade", tags=["Trading"])

class TradeRequest(BaseModel):
    """Base model for trading requests"""
    mint_address: str = Field(..., description="Token mint address")
    sol_amount: Optional[float] = Field(0.01, description="SOL amount to trade", ge=0.001)
    slippage: Optional[int] = Field(5, description="Slippage percentage", ge=1, le=50)

class SellRequest(TradeRequest):
    """Specific model for sell requests"""
    percentage: Optional[int] = Field(100, description="Percentage of tokens to sell", ge=1, le=100)

@router.post("/buy")
@trade_retry
async def trade_buy(trade_request: TradeRequest):
    """
    Execute a buy transaction on Pump.fun with enhanced error handling
    
    Args:
        trade_request (TradeRequest): Trading parameters
    
    Returns:
        Dict: Transaction result
    
    Raises:
        HTTPException: For various trading errors
    """
    try:
        # Validate configuration first
        if not client or not payer_keypair:
            raise ConfigurationError("Trading client or keypair not configured")
        
        # Validate coin data first
        coin_data = get_coin_data(trade_request.mint_address)
        if not coin_data:
            raise TokenNotFoundError(f"Token not found: {trade_request.mint_address}")
        
        # Log trade attempt
        logger.info(f"Attempting to buy token: {trade_request.mint_address}")
        
        # Execute buy
        result = buy(
            mint_str=trade_request.mint_address, 
            sol_in=trade_request.sol_amount, 
            slippage=trade_request.slippage
        )
        
        if not result:
            raise TransactionFailedError("Buy transaction failed")
        
        logger.info(f"Successfully bought token: {trade_request.mint_address}")
        
        return {
            "status": "success",
            "mint_address": trade_request.mint_address,
            "sol_amount": trade_request.sol_amount,
            "slippage": trade_request.slippage
        }
    
    except TokenNotFoundError as e:
        logger.error(f"Token not found error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail="Trading configuration error")
    
    except TransactionFailedError as e:
        logger.error(f"Transaction failed: {e}")
        raise HTTPException(status_code=400, detail="Buy transaction failed")
    
    except Exception as e:
        logger.error(f"Unexpected error in trade_buy: {e}")
        raise HTTPException(status_code=500, detail="Unexpected trading error")

@router.post("/sell")
@trade_retry
async def trade_sell(sell_request: SellRequest):
    """
    Execute a sell transaction on Pump.fun with enhanced error handling
    
    Args:
        sell_request (SellRequest): Selling parameters
    
    Returns:
        Dict: Transaction result
    
    Raises:
        HTTPException: For various trading errors
    """
    try:
        # Validate configuration first
        if not client or not payer_keypair:
            raise ConfigurationError("Trading client or keypair not configured")
        
        # Validate coin data first
        coin_data = get_coin_data(sell_request.mint_address)
        if not coin_data:
            raise TokenNotFoundError(f"Token not found: {sell_request.mint_address}")
        
        # Log trade attempt
        logger.info(f"Attempting to sell token: {sell_request.mint_address}")
        
        # Execute sell
        result = sell(
            mint_str=sell_request.mint_address, 
            percentage=sell_request.percentage, 
            slippage=sell_request.slippage
        )
        
        if not result:
            raise TransactionFailedError("Sell transaction failed")
        
        logger.info(f"Successfully sold token: {sell_request.mint_address}")
        
        return {
            "status": "success",
            "mint_address": sell_request.mint_address,
            "percentage": sell_request.percentage,
            "slippage": sell_request.slippage
        }
    
    except TokenNotFoundError as e:
        logger.error(f"Token not found error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail="Trading configuration error")
    
    except TransactionFailedError as e:
        logger.error(f"Transaction failed: {e}")
        raise HTTPException(status_code=400, detail="Sell transaction failed")
    
    except Exception as e:
        logger.error(f"Unexpected error in trade_sell: {e}")
        raise HTTPException(status_code=500, detail="Unexpected trading error")

@router.get("/token-info/{mint_address}")
async def get_token_info(mint_address: str):
    """
    Retrieve information about a specific token
    
    Args:
        mint_address (str): Token mint address
    
    Returns:
        Dict: Token information
    
    Raises:
        HTTPException: For token not found error
    """
    try:
        coin_data = get_coin_data(mint_address)
        
        if not coin_data:
            raise TokenNotFoundError(f"Token not found: {mint_address}")
        
        return {
            "mint": coin_data.mint,
            "name": coin_data.name,
            "symbol": coin_data.symbol,
            "complete": coin_data.complete,
            "virtual_sol_reserves": coin_data.virtual_sol_reserves,
            "virtual_token_reserves": coin_data.virtual_token_reserves,
            "bonding_curve": coin_data.bonding_curve,
            "associated_bonding_curve": coin_data.associated_bonding_curve
        }
    
    except TokenNotFoundError as e:
        logger.error(f"Token not found error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error retrieving token info: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving token information")

# Configuration endpoint to verify setup
@router.get("/config")
async def get_trade_config():
    """
    Get current trading configuration
    
    Returns:
        Dict: Trading configuration details
    
    Raises:
        HTTPException: For configuration error
    """
    try:
        if not client or not payer_keypair:
            raise ConfigurationError("Trading client or keypair not configured")
        
        return {
            "rpc_url": client.url if client else "Not configured",
            "payer_address": str(payer_keypair.pubkey()) if payer_keypair else "Not configured"
        }
    
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail="Trading configuration error")
    
    except Exception as e:
        logger.error(f"Error retrieving trade config: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving trade configuration")

# Existing Pump.fun Endpoints
@router.get("/trade-config")
async def get_trade_config():
    """
    Retrieve current trading configuration
    """
    try:
        config = {
            "client_configured": client is not None,
            "wallet_configured": payer_keypair is not None,
            "network_diagnostics": NETWORK_DIAGNOSTICS
        }
        return config
    except Exception as e:
        logger.error(f"Error retrieving trade config: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving trade configuration")

# Frontend Trading Endpoints
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey

@trade_router.get("/coin-data/{mint}")
@handle_trade_errors
async def fetch_coin_data(mint: str):
    """
    Fetch coin data for a given mint address
    """
    coin_data = get_coin_data(mint)
    if not coin_data:
        raise HTTPException(status_code=404, detail="Coin not found")
    return coin_data

@trade_router.post("/buy")
@handle_trade_errors
async def buy_token(data: Dict[str, Any]):
    """
    Execute token buy transaction with enhanced logging
    """
    try:
        mint = data.get('mint')
        sol_in = data.get('sol_in', 0.01)
        slippage = data.get('slippage', 5)
        
        if not mint:
            logger.warning("Buy attempt with missing mint address")
            raise HTTPException(status_code=400, detail="Mint address is required")
        
        logger.info(f"Attempting to buy token: {mint}, SOL amount: {sol_in}, Slippage: {slippage}")
        success = buy(mint, sol_in, slippage)
        
        if success:
            logger.info(f"Successfully bought token: {mint}")
        else:
            logger.warning(f"Failed to buy token: {mint}")
        
        return {"success": success}
    
    except Exception as e:
        logger.error(f"Buy transaction error: {e}", exc_info=True)
        raise

@trade_router.post("/sell")
@handle_trade_errors
async def sell_token(data: Dict[str, Any]):
    """
    Execute token sell transaction with enhanced logging
    """
    try:
        mint = data.get('mint')
        percentage = data.get('percentage', 100)
        slippage = data.get('slippage', 5)
        
        if not mint:
            logger.warning("Sell attempt with missing mint address")
            raise HTTPException(status_code=400, detail="Mint address is required")
        
        logger.info(f"Attempting to sell token: {mint}, Percentage: {percentage}, Slippage: {slippage}")
        success = sell(mint, percentage, slippage)
        
        if success:
            logger.info(f"Successfully sold token: {mint}")
        else:
            logger.warning(f"Failed to sell token: {mint}")
        
        return {"success": success}
    
    except Exception as e:
        logger.error(f"Sell transaction error: {e}", exc_info=True)
        raise

@trade_router.get("/balances")
@handle_trade_errors
async def get_token_balances():
    """
    Retrieve token balances for the current wallet
    
    Returns:
        List[Dict]: List of token balances with mint address and balance
    """
    if not payer_keypair:
        raise HTTPException(status_code=403, detail="Wallet not configured")
    
    try:
        # Get the owner's public key
        owner = payer_keypair.pubkey()
        
        # Retrieve token accounts for the wallet
        token_accounts = client.get_token_accounts_by_owner(
            owner, 
            TokenAccountOpts(program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
        )
        
        # Process token balances
        balances = []
        for account in token_accounts.value:
            # Extract mint and balance information
            mint = str(account.account.data.parsed['info']['mint'])
            balance = account.account.data.parsed['info']['tokenAmount']['amount']
            
            # Only include accounts with non-zero balance
            if int(balance) > 0:
                balances.append({
                    "mint": mint,
                    "balance": int(balance) / 1_000_000  # Adjust for token decimals
                })
        
        return balances
    
    except Exception as e:
        logger.error(f"Error retrieving token balances: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve token balances: {e}")

@trade_router.get("/network-diagnostics")
async def get_network_diagnostics():
    """
    Retrieve current network diagnostics
    """
    return validate_configuration()
