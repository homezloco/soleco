"""
Handler for processing mint-related responses from Solana RPC.
"""

from typing import Dict, Optional, Set
from collections import defaultdict

from app.utils.solana_response import ResponseHandler, SolanaResponseManager

class MintResponseHandler(ResponseHandler):
    """Handler for mint-related responses"""
    
    def __init__(self, response_manager: Optional[SolanaResponseManager] = None):
        super().__init__(response_manager)
        self.mint_stats = {
            "total_mints": 0,
            "unique_minters": set(),
            "mint_programs": defaultdict(int),
            "token_types": {
                "fungible": 0,
                "non_fungible": 0
            }
        }
    
    def process_transaction(self, transaction: Dict) -> Dict:
        """Process a mint transaction"""
        tx_details = super().process_result(transaction)
        
        # Track mint statistics
        if self._is_mint_transaction(tx_details):
            self.mint_stats["total_mints"] += 1
            
            # Track minter
            if "signer" in tx_details:
                self.mint_stats["unique_minters"].add(tx_details["signer"])
            
            # Track program
            if "program" in tx_details:
                self.mint_stats["mint_programs"][tx_details["program"]] += 1
            
            # Determine token type
            if self._is_nft_mint(tx_details):
                self.mint_stats["token_types"]["non_fungible"] += 1
            else:
                self.mint_stats["token_types"]["fungible"] += 1
        
        return tx_details
    
    def _is_mint_transaction(self, tx_details: Dict) -> bool:
        """Check if transaction is a mint operation"""
        if not tx_details.get("instructions"):
            return False
            
        mint_programs = {
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token Program
            "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"   # Token-2022
        }
        
        for inst in tx_details["instructions"]:
            if inst.get("program") in mint_programs and \
               "MintTo" in str(inst.get("data", "")):
                return True
        return False
    
    def _is_nft_mint(self, tx_details: Dict) -> bool:
        """Check if mint is for an NFT"""
        for inst in tx_details.get("instructions", []):
            if "decimals" in inst and inst["decimals"] == 0:
                return True
        return False
