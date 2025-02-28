"""
Handler for tracking and analyzing transaction statistics.
"""

from typing import Dict, List, Set, Any, Optional, Union
import time
from collections import defaultdict
import logging
from dataclasses import dataclass, field
from ..solana_errors import RetryableError

logger = logging.getLogger(__name__)

@dataclass
class MintActivity:
    """Tracks activity for a specific mint"""
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    transaction_count: int = 0
    total_transfers: int = 0
    
class TransactionStatsHandler:
    """Handler for tracking transaction statistics"""
    
    def __init__(self):
        # Basic counters
        self.start_time = time.time()
        self.total_processed = 0
        self.total_instructions = 0
        
        # Transaction type tracking
        self.transaction_types = {
            'vote': 0,
            'token': 0,
            'token2022': 0,
            'nft': 0,
            'marketplace': 0,
            'compute_budget': 0,
            'associated_token': 0,
            'other': 0
        }
        
        # Mint tracking
        self.mint_addresses = set()
        self.pump_tokens = set()
        self.mint_activity: Dict[str, MintActivity] = {}
        
        # Error tracking
        self.errors = []
        self.retries = defaultdict(int)
        self.retry_success = defaultdict(int)
        self.error_counts = defaultdict(int)
        
    def update_transaction_type(self, tx_type: str):
        """Update transaction type counter"""
        if tx_type in self.transaction_types:
            self.transaction_types[tx_type] += 1
        else:
            self.transaction_types['other'] += 1
            
    def add_mint_address(self, mint_address: str, timestamp: Optional[float] = None):
        """Track a new mint address"""
        if not mint_address:
            return
            
        self.mint_addresses.add(mint_address)
        current_time = timestamp or time.time()
        
        if mint_address not in self.mint_activity:
            self.mint_activity[mint_address] = MintActivity(
                first_seen=current_time,
                last_seen=current_time
            )
        else:
            activity = self.mint_activity[mint_address]
            activity.transaction_count += 1
            activity.last_seen = max(activity.last_seen, current_time)
            
    def add_pump_token(self, address: str):
        """Track a pump token address"""
        if address:
            self.pump_tokens.add(address)
            
    def log_error(self, error: Union[str, Exception], tx_index: Optional[int] = None):
        """Log an error with context"""
        error_str = str(error)
        self.error_counts[error_str] += 1
        
        error_context = {
            'error': error_str,
            'time': time.time(),
            'tx_index': tx_index
        }
        
        if isinstance(error, RetryableError):
            error_context['retryable'] = True
            
        self.errors.append(error_context)
        
    def record_retry(self, tx_hash: str, success: bool):
        """Record retry attempt and outcome"""
        self.retries[tx_hash] += 1
        if success:
            self.retry_success[tx_hash] += 1
            
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive statistics summary"""
        duration = time.time() - self.start_time
        
        return {
            'performance': {
                'total_processed': self.total_processed,
                'total_instructions': self.total_instructions,
                'duration_seconds': duration,
                'avg_time_per_tx': (duration/max(1, self.total_processed))*1000
            },
            'transactions': {
                'types': dict(self.transaction_types),
                'total': sum(self.transaction_types.values())
            },
            'mints': {
                'total_unique': len(self.mint_addresses),
                'pump_tokens': len(self.pump_tokens),
                'activity': {
                    mint: {
                        'first_seen': activity.first_seen,
                        'last_seen': activity.last_seen,
                        'transaction_count': activity.transaction_count,
                        'total_transfers': activity.total_transfers
                    }
                    for mint, activity in self.mint_activity.items()
                }
            },
            'errors': {
                'total': len(self.errors),
                'by_type': dict(self.error_counts),
                'retry_success_rate': sum(self.retry_success.values()) / max(1, sum(self.retries.values()))
            }
        }
