import logging
import base58
import nacl.signing
import nacl.exceptions
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class TransactionError(Exception):
    """Exception raised for transaction-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class PhantomWallet:
    def __init__(self, connection_timeout: int = 30):
        """
        Initialize PhantomWallet with configurable connection timeout
        
        Args:
            connection_timeout (int): Timeout for wallet connections in minutes
        """
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.connection_timeout = connection_timeout
        self.max_connections = 10  # Limit total number of active connections

    def verify_signature(self, wallet_address: str, message: str, signature: str) -> bool:
        """
        Verify a signature from a Phantom wallet
        
        Args:
            wallet_address (str): Base58 encoded public key
            message (str): Original message
            signature (str): Base58 encoded signature
        
        Returns:
            bool: Signature verification result
        """
        try:
            verify_key = nacl.signing.VerifyKey(base58.b58decode(wallet_address))
            verify_key.verify(message.encode(), base58.b58decode(signature))
            return True
        except (nacl.exceptions.BadSignatureError, Exception) as e:
            logger.error(f"Signature verification failed: {str(e)}")
            return False

    def add_connection(self, wallet_address: str, is_imported: bool = False) -> None:
        """
        Add a wallet connection with optional import flag
        
        Args:
            wallet_address (str): Wallet's public key
            is_imported (bool): Whether the wallet is imported
        """
        # Clean up expired connections first
        self._cleanup_connections()

        # Check if max connections reached
        if len(self.active_connections) >= self.max_connections:
            # Remove the oldest connection
            oldest_key = min(self.active_connections, key=lambda k: self.active_connections[k]['connected_at'])
            del self.active_connections[oldest_key]

        self.active_connections[wallet_address] = {
            'connected_at': datetime.utcnow(),
            'last_active': datetime.utcnow(),
            'is_imported': is_imported
        }

    def remove_connection(self, wallet_address: str) -> None:
        """
        Remove a wallet connection
        
        Args:
            wallet_address (str): Wallet's public key to remove
        """
        self.active_connections.pop(wallet_address, None)

    def is_connected(self, wallet_address: str) -> bool:
        """
        Check if a wallet is connected and not timed out
        
        Args:
            wallet_address (str): Wallet's public key
        
        Returns:
            bool: Connection status
        """
        self._cleanup_connections()
        return wallet_address in self.active_connections

    def update_last_active(self, wallet_address: str) -> None:
        """
        Update the last active timestamp for a wallet
        
        Args:
            wallet_address (str): Wallet's public key
        """
        if wallet_address in self.active_connections:
            self.active_connections[wallet_address]['last_active'] = datetime.utcnow()

    def _cleanup_connections(self) -> None:
        """
        Remove connections that have exceeded the timeout
        """
        current_time = datetime.utcnow()
        timeout_threshold = current_time - timedelta(minutes=self.connection_timeout)
        
        # Remove connections older than timeout
        expired_connections = [
            key for key, conn in self.active_connections.items()
            if conn['last_active'] < timeout_threshold
        ]
        
        for key in expired_connections:
            del self.active_connections[key]

    def get_active_wallets(self) -> List[Dict[str, Any]]:
        """
        Get a list of currently active wallets
        
        Returns:
            List[Dict[str, Any]]: List of active wallet details
        """
        self._cleanup_connections()
        return [
            {
                'public_key': key, 
                'connected_at': conn['connected_at'], 
                'last_active': conn['last_active'],
                'is_imported': conn.get('is_imported', False)
            } 
            for key, conn in self.active_connections.items()
        ]

    def get_wallet_details(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific wallet connection
        
        Args:
            wallet_address (str): Wallet's public key
        
        Returns:
            Optional[Dict[str, Any]]: Wallet connection details or None
        """
        self._cleanup_connections()
        return self.active_connections.get(wallet_address)

    async def get_balance(self, wallet_address: str) -> Optional[float]:
        """Get the SOL balance for a wallet."""
        try:
            # Mock implementation for now
            # In production, this would make an RPC call to the Solana network
            return 100.0
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            return None

    async def send_transaction(self, wallet_address: str, transaction_data: Dict[str, Any]) -> str:
        """Send a transaction using the wallet."""
        try:
            if not self.is_connected(wallet_address):
                raise TransactionError("Wallet not connected")

            # Mock implementation for now
            # In production, this would:
            # 1. Build the transaction
            # 2. Sign it with the wallet
            # 3. Send it to the Solana network
            # 4. Return the transaction signature

            return "mock_transaction_signature"
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            raise TransactionError(
                "Failed to send transaction",
                details={
                    "wallet_address": wallet_address,
                    "error": str(e)
                }
            )

    async def confirm_transaction(self, signature: str) -> bool:
        """Confirm a transaction has been processed."""
        try:
            # Mock implementation for now
            # In production, this would check the transaction status on the Solana network
            return True
        except Exception as e:
            logger.error(f"Error confirming transaction: {str(e)}")
            return False
