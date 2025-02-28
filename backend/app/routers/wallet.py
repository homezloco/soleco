"""
Wallet management router for the Soleco API.
"""
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

# Create router
router = APIRouter(
    prefix="",  # Remove the prefix as it's already added in main.py
    tags=["wallet"],
    responses={404: {"description": "Not found"}}
)

# Models
class WalletListResponse(BaseModel):
    phantom_wallets: List[str] = []
    imported_wallets: List[str] = []
    max_imported_wallets: int = 20

class WalletConnectRequest(BaseModel):
    wallet_address: str
    wallet_type: str = "phantom"

class WalletDisconnectRequest(BaseModel):
    wallet_address: str

class WalletImportRequest(BaseModel):
    private_key: str

class WalletImportResponse(BaseModel):
    wallet_address: str
    success: bool
    message: str

class WalletBalanceResponse(BaseModel):
    balance: float
    wallet_address: str

class SignTransactionRequest(BaseModel):
    wallet_address: str
    transaction_data: Dict

class SignTransactionResponse(BaseModel):
    signature: str
    signed_transaction: Dict

# Mock data for development
PHANTOM_WALLETS = []
IMPORTED_WALLETS = []
MAX_IMPORTED_WALLETS = 20

@router.get("/list", response_model=WalletListResponse)
async def list_wallets():
    """
    List all connected wallets.
    """
    return WalletListResponse(
        phantom_wallets=PHANTOM_WALLETS,
        imported_wallets=IMPORTED_WALLETS,
        max_imported_wallets=MAX_IMPORTED_WALLETS
    )

@router.post("/connect")
async def connect_wallet(request: WalletConnectRequest):
    """
    Connect a wallet.
    """
    wallet_address = request.wallet_address
    if request.wallet_type == "phantom" and wallet_address not in PHANTOM_WALLETS:
        PHANTOM_WALLETS.append(wallet_address)
    
    return {"success": True, "message": f"Wallet {wallet_address} connected"}

@router.post("/disconnect")
async def disconnect_wallet(request: WalletDisconnectRequest):
    """
    Disconnect a wallet.
    """
    wallet_address = request.wallet_address
    if wallet_address in PHANTOM_WALLETS:
        PHANTOM_WALLETS.remove(wallet_address)
    elif wallet_address in IMPORTED_WALLETS:
        IMPORTED_WALLETS.remove(wallet_address)
    
    return {"success": True, "message": f"Wallet {wallet_address} disconnected"}

@router.post("/import", response_model=WalletImportResponse)
async def import_wallet(request: WalletImportRequest):
    """
    Import a wallet using a private key.
    """
    # In a real implementation, this would validate the private key
    # and derive the wallet address
    
    # For demo purposes, we'll just use a mock address
    mock_address = f"mock_{request.private_key[:8]}"
    
    if len(IMPORTED_WALLETS) >= MAX_IMPORTED_WALLETS:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum number of imported wallets ({MAX_IMPORTED_WALLETS}) reached"
        )
    
    if mock_address not in IMPORTED_WALLETS:
        IMPORTED_WALLETS.append(mock_address)
    
    return WalletImportResponse(
        wallet_address=mock_address,
        success=True,
        message="Wallet imported successfully"
    )

@router.get("/balance/{wallet_address}", response_model=WalletBalanceResponse)
async def get_wallet_balance(wallet_address: str):
    """
    Get the balance of a wallet.
    """
    # In a real implementation, this would query the Solana blockchain
    # For demo purposes, we'll return a mock balance
    
    return WalletBalanceResponse(
        balance=100.0,
        wallet_address=wallet_address
    )

@router.post("/sign-transaction", response_model=SignTransactionResponse)
async def sign_transaction(request: SignTransactionRequest):
    """
    Sign a transaction.
    """
    # In a real implementation, this would use the private key to sign the transaction
    # For demo purposes, we'll return a mock signature
    
    return SignTransactionResponse(
        signature="mock_signature",
        signed_transaction=request.transaction_data
    )
