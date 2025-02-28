from typing import Optional, Dict, Any, AsyncContextManager, Tuple, List
import logging
import json
import base64
import base58
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from solders.keypair import Keypair
from solders.pubkey import Pubkey as PublicKey
from solders.transaction import Transaction
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solana.rpc.providers import http
import httpx
import functools

logger = logging.getLogger(__name__)

MAX_IMPORTED_WALLETS = 20

class WalletConnection:
    def __init__(
        self, 
        public_key: str, 
        is_imported: bool = False, 
        keypair: Optional[Keypair] = None
    ):
        """
        Represent a wallet connection
        
        Args:
            public_key (str): Wallet's public key
            is_imported (bool): Whether the wallet is imported
            keypair (Optional[Keypair]): Keypair for imported wallets
        """
        self.public_key = public_key
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.is_imported = is_imported
        self.keypair = keypair  # Only set for imported wallets

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()

class WalletService:
    def __init__(self, session: AsyncSession):
        """
        Initialize WalletService
        
        Args:
            session (AsyncSession): SQLAlchemy async session
        """
        self.session = session
        self.phantom_adapter = PhantomAdapter()

    async def list_wallets(self) -> Dict[str, Any]:
        """
        List all wallets in the system
        
        Returns:
            Dict[str, Any]: Wallet list details
        """
        try:
            return await self.phantom_adapter.list_wallets()
        except Exception as e:
            logger.error(f"Error listing wallets: {str(e)}")
            raise

    async def get_wallet_balance(self, public_key: str) -> float:
        """
        Get wallet balance
        
        Args:
            public_key (str): Wallet's public key
        
        Returns:
            float: Wallet balance in SOL
        """
        try:
            # Create client without proxy argument
            client = create_solana_client(self.phantom_adapter.rpc_url)
            balance_response = client.get_balance(PublicKey.from_string(public_key))
            return balance_response.value / 10**9  # Convert lamports to SOL
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            raise

class WalletManager:
    def __init__(self):
        """
        Initialize WalletManager
        
        Sets up Phantom Adapter and manages wallet connections
        """
        self.active_connections: Dict[str, WalletConnection] = {}
        self.imported_wallets: Dict[str, WalletConnection] = {}
        self.phantom = PhantomAdapter()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Cleanup any stale connections
        await self.cleanup_stale_connections()
        return None

    @asynccontextmanager
    async def get_phantom_adapter(self) -> AsyncContextManager[PhantomAdapter]:
        """Get a phantom adapter instance within a context"""
        async with self.phantom as adapter:
            yield adapter

    async def connect_wallet(
        self, 
        public_key: str, 
        signature: str, 
        message: str
    ) -> bool:
        """
        Connect a wallet and verify its signature
        
        Args:
            public_key (str): Wallet's public key
            signature (str): Signature for verification
            message (str): Original message
        
        Returns:
            bool: Connection status
        """
        try:
            # Verify connection
            is_verified = await self.phantom.verify_connection(
                public_key, signature, message
            )
            
            if is_verified:
                # Create or update wallet connection
                connection = WalletConnection(public_key)
                self.active_connections[public_key] = connection
                
                return True
            
            return False
        except Exception as e:
            logger.error(f"Wallet connection failed: {e}")
            return False

    async def disconnect_wallet(self, public_key: str) -> bool:
        """
        Disconnect a wallet
        
        Args:
            public_key (str): Wallet's public key
        
        Returns:
            bool: Disconnection status
        """
        try:
            # Remove from active connections
            if public_key in self.active_connections:
                del self.active_connections[public_key]
            
            # Remove from imported wallets if applicable
            if public_key in self.imported_wallets:
                del self.imported_wallets[public_key]
            
            return True
        except Exception as e:
            logger.error(f"Wallet disconnection failed: {e}")
            return False

    async def import_wallet(self, private_key: str) -> str:
        """
        Import a new wallet
        
        Args:
            private_key (str): Base58 encoded private key
        
        Returns:
            str: Public key of the imported wallet
        """
        try:
            # Use PhantomAdapter to import wallet
            public_key = await self.phantom.import_wallet(private_key)
            
            # Create imported wallet connection
            connection = WalletConnection(
                public_key, 
                is_imported=True
            )
            
            self.imported_wallets[public_key] = connection
            self.active_connections[public_key] = connection
            
            return public_key
        except PhantomAdapterError as e:
            logger.error(f"Wallet import failed: {e}")
            raise

    async def sign_transaction(
        self, 
        public_key: str, 
        transaction: Transaction
    ) -> Transaction:
        """
        Sign a transaction with a specific wallet
        
        Args:
            public_key (str): Wallet's public key
            transaction (Transaction): Transaction to sign
        
        Returns:
            Transaction: Signed transaction
        """
        try:
            # Check if wallet is connected or imported
            if public_key not in self.active_connections:
                raise PhantomAdapterError("Wallet not connected")
            
            # Sign transaction using PhantomAdapter
            signed_transaction = await self.phantom.sign_transaction(
                public_key, transaction
            )
            
            return signed_transaction
        except Exception as e:
            logger.error(f"Transaction signing failed: {e}")
            raise

    async def verify_signature(
        self, 
        public_key: str, 
        message: str, 
        signature: str
    ) -> bool:
        """
        Verify a signature for a given wallet
        
        Args:
            public_key (str): Wallet's public key
            message (str): Original message
            signature (str): Signature to verify
        
        Returns:
            bool: Signature verification result
        """
        try:
            return await self.phantom.verify_signature(
                public_key, message, signature
            )
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    async def cleanup_stale_connections(self) -> None:
        """
        Clean up stale wallet connections
        """
        try:
            # Remove connections older than 30 minutes
            current_time = datetime.utcnow()
            timeout_threshold = current_time - timedelta(minutes=30)
            
            stale_connections = [
                key for key, conn in self.active_connections.items()
                if conn.last_activity < timeout_threshold
            ]
            
            for key in stale_connections:
                del self.active_connections[key]
                
                # Also remove from imported wallets if applicable
                if key in self.imported_wallets:
                    del self.imported_wallets[key]
        except Exception as e:
            logger.error(f"Connection cleanup failed: {e}")

    def validate_private_key(self, private_key: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a Solana private key and return validation status and error message
        """
        try:
            # Try to decode base58 private key
            decoded_key = base58.b58decode(private_key)
            
            # Check key length (32 bytes for ed25519)
            if len(decoded_key) != 32:
                return False, "Invalid private key length"
            
            # Try to create a Solana keypair
            keypair = Keypair.from_secret_key(decoded_key)
            
            # Verify we can get a valid public key
            _ = str(keypair.public_key)
            
            return True, None
        except ValueError:
            return False, "Invalid private key format"
        except Exception as e:
            return False, f"Error validating private key: {str(e)}"

    async def import_wallet_from_private_key(self, private_key: str) -> Tuple[Optional[WalletConnection], Optional[str]]:
        """
        Import a wallet from a private key
        Returns (WalletConnection, None) on success or (None, error_message) on failure
        """
        try:
            # Check wallet import limit
            if len(self.imported_wallets) >= MAX_IMPORTED_WALLETS:
                return None, f"Maximum {MAX_IMPORTED_WALLETS} wallet imports reached"

            # Validate private key
            is_valid, error_msg = self.validate_private_key(private_key)
            if not is_valid:
                return None, error_msg

            # Create Solana keypair
            decoded_key = base58.b58decode(private_key)
            keypair = Keypair.from_secret_key(decoded_key)
            public_key = str(keypair.public_key)

            # Check if wallet is already imported
            if public_key in self.imported_wallets:
                return None, "Wallet already imported"

            # Create and store wallet connection
            connection = WalletConnection(public_key, is_imported=True, keypair=keypair)
            self.imported_wallets[public_key] = connection
            logger.info(f"Wallet imported: {public_key}")
            
            return connection, None

        except Exception as e:
            error_msg = f"Error importing wallet: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    def get_connection(self, public_key: str) -> Optional[WalletConnection]:
        """Get an active wallet connection by public key"""
        # Check imported wallets first
        connection = self.imported_wallets.get(public_key)
        if connection:
            connection.update_activity()
            return connection
            
        # Then check phantom connections
        connection = self.active_connections.get(public_key)
        if connection:
            connection.update_activity()
            return connection
            
        return None

    async def send_transaction(
        self, 
        sender_key: str, 
        recipient_key: str, 
        amount: float, 
        additional_signers: Optional[list] = None
    ) -> str:
        """
        Send a transaction from one wallet to another
        
        Args:
            sender_key (str): Sender's public key
            recipient_key (str): Recipient's public key
            amount (float): Amount to send in SOL
            additional_signers (list, optional): Additional transaction signers
        
        Returns:
            str: Transaction signature
        """
        if sender_key not in self.active_connections:
            raise ValueError("Sender wallet not connected")
        
        # Create transaction
        transaction = Transaction()
        # Here you would add the actual transaction instructions
        # This is a placeholder and needs to be implemented with actual Solana transaction logic
        
        return await self.phantom.sign_and_send_transaction(
            sender_key, 
            transaction, 
            signers=additional_signers
        )

    @patch_client_initialization
    def get_wallet_balance(self, public_key: str) -> float:
        """
        Get wallet balance
        
        Args:
            public_key (str): Wallet's public key
        
        Returns:
            float: Wallet balance in SOL
        """
        try:
            # Create client with patched initialization
            client = Client(self.phantom_adapter.rpc_url)
            
            # Get balance
            balance_response = client.get_balance(PublicKey.from_string(public_key))
            return balance_response.value / 10**9  # Convert lamports to SOL
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            raise

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

def create_solana_client(rpc_url: str) -> Client:
    """
    Create a Solana RPC client with patched initialization
    
    Args:
        rpc_url (str): Solana RPC endpoint URL
    
    Returns:
        Client: Solana RPC client
    """
    # Store original methods
    original_http_init = http.HTTPProvider.__init__
    original_httpx_init = httpx.Client.__init__
    
    def patched_http_init(self, *args, **kwargs):
        # Remove proxy from kwargs
        kwargs.pop('proxy', None)
        return original_http_init(self, *args, **kwargs)
    
    def patched_httpx_init(self, *args, **kwargs):
        # Remove proxy from kwargs
        kwargs.pop('proxy', None)
        return original_httpx_init(self, *args, **kwargs)
    
    try:
        # Patch initialization methods
        http.HTTPProvider.__init__ = patched_http_init
        httpx.Client.__init__ = patched_httpx_init
        
        # Initialize client
        return Client(rpc_url)
    finally:
        # Restore original methods
        http.HTTPProvider.__init__ = original_http_init
        httpx.Client.__init__ = original_httpx_init
