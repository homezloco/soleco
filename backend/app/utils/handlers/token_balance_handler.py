"""
Handler for processing token balance changes in Solana transactions.
"""

from typing import Dict, List, Set, Any, Optional
import logging
from dataclasses import dataclass
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)

@dataclass
class TokenBalanceChange:
    """Represents a token balance change"""
    mint: str
    owner: str
    pre_amount: int = 0
    post_amount: int = 0
    is_new: bool = False

class TokenBalanceHandler(BaseHandler):
    """Handler for processing token balance changes"""
    
    def __init__(self):
        super().__init__()
        self.known_mints = set()
        self.processed_balances = set()
        
    def process_balance_changes(self, pre_balances: List[Dict], post_balances: List[Dict]) -> Dict[str, Any]:
        """Process token balance changes to detect new mints and transfers"""
        result = {
            'new_mints': set(),
            'transfers': [],
            'balance_changes': []
        }
        
        try:
            # Create lookup of pre-balances by mint and owner
            pre_balance_map = {
                (b['mint'], b.get('owner')): b.get('uiTokenAmount', {}).get('amount', 0)
                for b in pre_balances if b.get('mint')
            }
            
            # Process post balances
            for balance in post_balances:
                mint = balance.get('mint')
                owner = balance.get('owner')
                if not mint or not owner:
                    continue
                    
                amount = balance.get('uiTokenAmount', {}).get('amount', 0)
                pre_amount = pre_balance_map.get((mint, owner), 0)
                
                change = TokenBalanceChange(
                    mint=mint,
                    owner=owner,
                    pre_amount=pre_amount,
                    post_amount=amount,
                    is_new=not any(b['mint'] == mint for b in pre_balances)
                )
                
                # Track balance change
                result['balance_changes'].append({
                    'mint': change.mint,
                    'owner': change.owner,
                    'pre_amount': change.pre_amount,
                    'post_amount': change.post_amount,
                    'change': float(change.post_amount) - float(change.pre_amount)
                })
                
                # Check if this is a new mint
                if change.is_new and self._is_valid_new_mint(change.mint):
                    result['new_mints'].add(change.mint)
                
                # Track transfers
                if change.pre_amount != change.post_amount:
                    result['transfers'].append({
                        'mint': change.mint,
                        'owner': change.owner,
                        'amount': float(change.post_amount) - float(change.pre_amount)
                    })
                    
        except Exception as e:
            logger.error(f"Error processing balance changes: {str(e)}", exc_info=True)
            
        return result
    
    def _is_valid_new_mint(self, mint: str) -> bool:
        """Check if mint appears to be a valid new mint"""
        if not mint or mint in self.known_mints:
            return False
            
        # Add to processed set
        self.known_mints.add(mint)
        return True
