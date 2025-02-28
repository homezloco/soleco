from typing import Optional, Dict, Any, Union, List
import logging
import base58
import json
from datetime import datetime, timedelta
from solders.pubkey import Pubkey as PublicKey
from solders.transaction import Transaction
from solders.keypair import Keypair
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import os
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solana.rpc.providers import http
import httpx
from solders.message import Message
import functools

from app.config.wallet_config import WALLET_CONFIG, ERROR_MESSAGES
from .phantom_wallet import PhantomWallet

logger = logging.getLogger(__name__)

class PhantomAdapterError(Exception):
    """Custom exception for Phantom adapter errors"""
    pass

class PhantomAdapter:
    """Adapter for communicating with Phantom wallet browser extension and imported wallets"""
    
    def __init__(self, 
                 rpc_url: Optional[str] = None, 
                 max_imported_wallets: int = 20):
        """
        Initialize the Phantom Wallet Adapter
        
        Args:
            rpc_url (Optional[str]): Solana RPC URL
            max_imported_wallets (int): Maximum number of imported wallets
        """
        self.connected_wallets: Dict[str, Dict[str, Any]] = {}
        self.imported_wallets: Dict[str, Keypair] = {}
        self.phantom_wallet = PhantomWallet()
        
        # RPC Configuration
        self.rpc_url = rpc_url or os.getenv(
            "SOLANA_RPC_URL", 
            "https://api.mainnet-beta.solana.com"
        )
        
        # Wallet Import Limits
        self.max_imported_wallets = max_imported_wallets

    def verify_connection(
        self, 
        public_key: str, 
        signature: str, 
        message: str
    ) -> bool:
        """
        Verify wallet connection signature
        
        Args:
            public_key (str): Base58 encoded public key
            signature (str): Base58 encoded signature
            message (str): Original message
        
        Returns:
            bool: Signature verification result
        """
        try:
            # Decode the public key
            verify_key = VerifyKey(base58.b58decode(public_key))
            
            # Verify the signature
            verify_key.verify(
                message.encode(),
                base58.b58decode(signature)
            )
            
            # Add connection to PhantomWallet
            self.phantom_wallet.add_connection(public_key)
            
            return True
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False

    @staticmethod
    def patch_client_initialization(func):
        """
        Decorator to patch client initialization and remove proxy argument
        
        Args:
            func (callable): Function to decorate
        
        Returns:
            callable: Decorated function with patched client initialization
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Store original methods
            original_http_init = http.HTTPProvider.__init__
            original_httpx_init = httpx.Client.__init__
            
            def patched_http_init(self, *http_args, **http_kwargs):
                # Remove proxy from kwargs
                http_kwargs.pop('proxy', None)
                return original_http_init(self, *http_args, **http_kwargs)
            
            def patched_httpx_init(self, *httpx_args, **httpx_kwargs):
                # Remove proxy from kwargs
                httpx_kwargs.pop('proxy', None)
                return original_httpx_init(self, *httpx_args, **httpx_kwargs)
            
            try:
                # Patch initialization methods
                http.HTTPProvider.__init__ = patched_http_init
                httpx.Client.__init__ = patched_httpx_init
                
                # Call the original function
                return func(*args, **kwargs)
            finally:
                # Restore original methods
                http.HTTPProvider.__init__ = original_http_init
                httpx.Client.__init__ = original_httpx_init
        
        return wrapper

    @patch_client_initialization
    def create_solana_client(self, rpc_url: str) -> Client:
        """
        Create a Solana RPC client with patched initialization
        
        Args:
            rpc_url (str): Solana RPC endpoint URL
        
        Returns:
            Client: Solana RPC client
        """
        return Client(rpc_url)

    def get_wallet_balance(self, public_key: str) -> float:
        """
        Retrieve the SOL balance for a given wallet address
        
        Args:
            public_key (str): Base58 encoded public key
        
        Returns:
            float: Wallet balance in SOL
        """
        try:
            # Create client with patched initialization
            client = self.create_solana_client(self.rpc_url)
            
            # Get balance
            balance_response = client.get_balance(PublicKey.from_string(public_key))
            return balance_response.value / 10**9  # Convert lamports to SOL
        except Exception as e:
            logger.error(f"Balance retrieval failed: {e}")
            raise PhantomAdapterError(f"Balance retrieval failed: {e}")

    def import_wallet(self, private_key: str) -> str:
        """
        Import a new wallet
        
        Args:
            private_key (str): Base58 encoded private key
        
        Returns:
            str: Public key of the imported wallet
        """
        # Check imported wallet limit
        if len(self.imported_wallets) >= self.max_imported_wallets:
            raise PhantomAdapterError("Maximum number of imported wallets reached")
        
        try:
            # Create keypair from private key
            keypair = Keypair.from_base58_private_key(private_key)
            public_key = str(keypair.pubkey())
            
            # Store imported wallet
            self.imported_wallets[public_key] = keypair
            
            # Add connection with imported flag
            self.phantom_wallet.add_connection(public_key, is_imported=True)
            
            return public_key
        except Exception as e:
            logger.error(f"Wallet import failed: {e}")
            raise PhantomAdapterError(f"Wallet import failed: {e}")

    def sign_transaction(
        self, 
        public_key: str, 
        transaction: Transaction
    ) -> Transaction:
        """
        Sign a transaction with an imported wallet's private key
        
        Args:
            public_key (str): Base58 encoded public key
            transaction (Transaction): Transaction to sign
        
        Returns:
            Transaction: Signed transaction
        """
        if public_key not in self.imported_wallets:
            raise PhantomAdapterError("Wallet not found or not imported")
        
        try:
            # Get the keypair for the wallet
            keypair = self.imported_wallets[public_key]
            
            # Sign the transaction
            transaction.sign([keypair])
            
            return transaction
        except Exception as e:
            logger.error(f"Transaction signing failed: {e}")
            raise PhantomAdapterError(f"Transaction signing failed: {e}")

    def verify_signature(
        self, 
        public_key: str, 
        message: str, 
        signature: str
    ) -> bool:
        """
        Verify a signature for a given wallet
        
        Args:
            public_key (str): Base58 encoded public key
            message (str): Original message
            signature (str): Base58 encoded signature
        
        Returns:
            bool: Signature verification result
        """
        return self.phantom_wallet.verify_signature(public_key, message, signature)

    def list_wallets(self) -> Dict[str, Any]:
        """
        List all active and imported wallets
        
        Returns:
            Dict[str, Any]: Wallet list details
        """
        active_wallets = self.phantom_wallet.get_active_wallets()
        
        return {
            "phantom_wallets": [
                wallet for wallet in active_wallets 
                if not wallet['is_imported']
            ],
            "imported_wallets": [
                wallet for wallet in active_wallets 
                if wallet['is_imported']
            ],
            "max_imported_wallets": self.max_imported_wallets
        }

    def cleanup_stale_connections(self) -> None:
        """
        Clean up stale wallet connections
        """
        # This is handled internally by PhantomWallet's _cleanup_connections method
        pass
