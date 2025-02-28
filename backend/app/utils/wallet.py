"""
Wallet management utilities for Solana wallets.
"""

import logging
from typing import Dict, List, Any, Optional
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient

logger = logging.getLogger(__name__)

class WalletManager:
    """
    Manages Solana wallet operations.
    """
    
    def __init__(self):
        """Initialize wallet manager."""
        self.wallets: Dict[str, Keypair] = {}
        self.active_wallet: Optional[str] = None
    
    def add_wallet(self, name: str, keypair: Keypair) -> None:
        """
        Add a wallet to the manager.
        
        Args:
            name: Name of the wallet
            keypair: Solana keypair
        """
        self.wallets[name] = keypair
        logger.info(f"Added wallet: {name}")
        
        # Set as active if it's the first wallet
        if not self.active_wallet:
            self.active_wallet = name
    
    def set_active_wallet(self, name: str) -> bool:
        """
        Set the active wallet.
        
        Args:
            name: Name of the wallet to set as active
            
        Returns:
            True if successful, False otherwise
        """
        if name in self.wallets:
            self.active_wallet = name
            logger.info(f"Set active wallet: {name}")
            return True
        
        logger.error(f"Wallet not found: {name}")
        return False
    
    def get_active_wallet(self) -> Optional[Keypair]:
        """
        Get the active wallet keypair.
        
        Returns:
            Active wallet keypair or None if no active wallet
        """
        if not self.active_wallet:
            logger.warning("No active wallet set")
            return None
        
        return self.wallets.get(self.active_wallet)
    
    def get_active_pubkey(self) -> Optional[Pubkey]:
        """
        Get the public key of the active wallet.
        
        Returns:
            Public key of the active wallet or None if no active wallet
        """
        wallet = self.get_active_wallet()
        if not wallet:
            return None
        
        return wallet.pubkey()
    
    def list_wallets(self) -> List[Dict[str, Any]]:
        """
        List all wallets.
        
        Returns:
            List of wallet information
        """
        return [
            {
                "name": name,
                "pubkey": str(wallet.pubkey()),
                "active": name == self.active_wallet
            }
            for name, wallet in self.wallets.items()
        ]
    
    async def get_balance(self, client: AsyncClient, wallet_name: Optional[str] = None) -> Optional[float]:
        """
        Get the balance of a wallet.
        
        Args:
            client: Solana RPC client
            wallet_name: Name of the wallet (uses active wallet if None)
            
        Returns:
            Balance in SOL or None if wallet not found
        """
        wallet_name = wallet_name or self.active_wallet
        if not wallet_name or wallet_name not in self.wallets:
            logger.error(f"Wallet not found: {wallet_name}")
            return None
        
        pubkey = self.wallets[wallet_name].pubkey()
        
        try:
            response = await client.get_balance(pubkey)
            if response.value is not None:
                # Convert lamports to SOL
                return response.value / 1_000_000_000
            
            logger.error(f"Failed to get balance for {wallet_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting balance for {wallet_name}: {str(e)}")
            return None
