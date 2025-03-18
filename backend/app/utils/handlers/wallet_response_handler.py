"""
Handler for processing wallet-related responses from Solana RPC.
"""

from typing import Dict, Optional, Set
from collections import defaultdict

from app.utils.base_response_handler import ResponseHandler, SolanaResponseManager

class WalletResponseHandler(ResponseHandler):
    """Handler for wallet-related responses"""
    
    def __init__(self, response_manager: Optional[SolanaResponseManager] = None):
        super().__init__(response_manager)
        self.wallet_stats = {
            "transaction_count": 0,
            "program_interactions": defaultdict(int),
            "gas_usage": {
                "total": 0,
                "average": 0,
                "by_program": defaultdict(int)
            },
            "token_transfers": set(),
            "nft_interactions": set()
        }
    
    def process_transaction(self, transaction: Dict) -> Dict:
        """Process a wallet transaction"""
        tx_details = super().process_result(transaction)
        self.wallet_stats["transaction_count"] += 1
        
        # Track program interactions
        for inst in tx_details.get("instructions", []):
            program_id = inst.get("program")
            if program_id:
                self.wallet_stats["program_interactions"][program_id] += 1
                
                # Track gas usage by program
                if "computeUnitsConsumed" in inst:
                    self.wallet_stats["gas_usage"]["by_program"][program_id] += \
                        inst["computeUnitsConsumed"]
                    self.wallet_stats["gas_usage"]["total"] += inst["computeUnitsConsumed"]
        
        # Update averages
        if self.wallet_stats["transaction_count"] > 0:
            self.wallet_stats["gas_usage"]["average"] = \
                self.wallet_stats["gas_usage"]["total"] / \
                self.wallet_stats["transaction_count"]
        
        # Track token and NFT interactions
        if self._is_token_transfer(tx_details):
            token_address = self._get_token_address(tx_details)
            if token_address:
                if self._is_nft(tx_details):
                    self.wallet_stats["nft_interactions"].add(token_address)
                else:
                    self.wallet_stats["token_transfers"].add(token_address)
        
        return tx_details
    
    def _is_token_transfer(self, tx_details: Dict) -> bool:
        """Check if transaction involves token transfer"""
        token_programs = {
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token Program
            "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"   # Token-2022
        }
        
        for inst in tx_details.get("instructions", []):
            if inst.get("program") in token_programs and \
               "Transfer" in str(inst.get("data", "")):
                return True
        return False
    
    def _get_token_address(self, tx_details: Dict) -> Optional[str]:
        """Extract token address from transaction"""
        for inst in tx_details.get("instructions", []):
            if "mint" in inst:
                return inst["mint"]
        return None
    
    def _is_nft(self, tx_details: Dict) -> bool:
        """Check if token is an NFT"""
        for inst in tx_details.get("instructions", []):
            if "decimals" in inst and inst["decimals"] == 0:
                return True
        return False
