"""
Models for tracking statistics and metrics.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger("solana.response")

@dataclass
class Statistics:
    """Base statistics tracking"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retried_requests: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    
    def increment_total(self) -> None:
        """Increment total request count"""
        self.total_requests += 1
        
    def increment_success(self) -> None:
        """Increment successful request count"""
        self.successful_requests += 1
        
    def increment_failed(self) -> None:
        """Increment failed request count"""
        self.failed_requests += 1
        
    def increment_retried(self) -> None:
        """Increment retried request count"""
        self.retried_requests += 1
        
    def get_success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
        
    def get_error_rate(self) -> float:
        """Calculate error rate"""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary format"""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'retried_requests': self.retried_requests,
            'success_rate': self.get_success_rate(),
            'error_rate': self.get_error_rate(),
            'uptime': (datetime.now() - self.start_time).total_seconds()
        }

class MetricsTracker:
    """Tracks time-based metrics and patterns"""
    
    def __init__(self, window_size: timedelta = timedelta(minutes=5)):
        """Initialize metrics tracker"""
        self.window_size = window_size
        self.token_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'first_seen': datetime.now(),
            'last_seen': datetime.now(),
            'mint_count': 0,
            'transaction_count': 0,
            'volume': 0.0,
            'unique_accounts': set(),
            'mint_times': [],
            'volume_history': []
        })
        
    def update_token_stats(self, token_address: str,
                          transaction_data: Dict[str, Any]) -> None:
        """Update statistics for a token"""
        stats = self.token_stats[token_address]
        current_time = datetime.now()
        
        # Update basic stats
        stats['last_seen'] = current_time
        stats['transaction_count'] += 1
        
        # Update mint count if applicable
        if transaction_data.get('is_mint'):
            stats['mint_count'] += 1
            stats['mint_times'].append(current_time)
            
        # Update volume
        volume = transaction_data.get('volume', 0.0)
        stats['volume'] += volume
        stats['volume_history'].append((current_time, volume))
        
        # Update unique accounts
        accounts = transaction_data.get('accounts', [])
        stats['unique_accounts'].update(accounts)
        
        # Cleanup old data
        self._cleanup_old_data(token_address)
        
    def get_transaction_patterns(self, token_address: str) -> Dict[str, int]:
        """Analyze transaction patterns for a token"""
        stats = self.token_stats.get(token_address, {})
        if not stats:
            return {'rapid_mints': 0, 'high_volume': 0}
            
        # Count rapid mints (multiple mints in short window)
        mint_times = stats.get('mint_times', [])
        rapid_mints = 0
        for i in range(len(mint_times) - 1):
            if (mint_times[i+1] - mint_times[i]).total_seconds() < 60:
                rapid_mints += 1
                
        # Count high volume transactions
        volume_history = stats.get('volume_history', [])
        high_volume = sum(1 for _, vol in volume_history if vol > 1000.0)
        
        return {
            'rapid_mints': rapid_mints,
            'high_volume': high_volume
        }
        
    def get_time_based_metrics(self, token_address: str) -> Dict[str, float]:
        """Calculate time-based metrics for a token"""
        stats = self.token_stats.get(token_address, {})
        if not stats:
            return {'mint_rate': 0.0, 'volume_spike': 0.0}
            
        current_time = datetime.now()
        window_start = current_time - self.window_size
        
        # Calculate mint rate (mints per minute)
        recent_mints = sum(1 for t in stats['mint_times'] if t > window_start)
        mint_rate = recent_mints / (self.window_size.total_seconds() / 60)
        
        # Calculate volume spike (ratio of recent volume to average)
        volume_history = stats['volume_history']
        recent_volume = sum(vol for t, vol in volume_history if t > window_start)
        total_volume = stats['volume']
        volume_spike = recent_volume / total_volume if total_volume > 0 else 0.0
        
        return {
            'mint_rate': mint_rate,
            'volume_spike': volume_spike
        }
        
    def _cleanup_old_data(self, token_address: str) -> None:
        """Remove data older than the window size"""
        stats = self.token_stats[token_address]
        current_time = datetime.now()
        window_start = current_time - self.window_size
        
        # Clean up mint times
        stats['mint_times'] = [t for t in stats['mint_times'] if t > window_start]
        
        # Clean up volume history
        stats['volume_history'] = [(t, v) for t, v in stats['volume_history']
                                 if t > window_start]
