"""
Tracks and analyzes time-based metrics and transaction patterns for Solana tokens.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TokenMetrics:
    """Metrics for a specific token."""
    address: str
    first_seen: float = 0
    last_seen: float = 0
    transaction_count: int = 0
    mint_operations: int = 0
    transfer_operations: int = 0
    holder_count: int = 0
    total_volume: float = 0
    confidence_score: float = 0
    unique_senders: Set[str] = field(default_factory=set)
    unique_receivers: Set[str] = field(default_factory=set)
    avg_transfer_amount: float = 0
    max_transfer_amount: float = 0
    initial_mint_amount: float = 0
    activity_intervals: List[Dict[str, Any]] = field(default_factory=list)

class MetricsTracker:
    """Tracks and analyzes token metrics."""
    
    def __init__(self):
        """Initialize metrics tracker."""
        self.token_metrics: Dict[str, TokenMetrics] = {}
        self.transaction_history: Dict[str, List[Dict]] = {}
        self.time_based_metrics: Dict[str, Dict[str, Any]] = {}
        self.program_interactions: Dict[str, Dict[str, int]] = {}
        
    def track_transaction(self, token: str, tx_data: Dict[str, Any]) -> None:
        """Track a transaction for a token."""
        if token not in self.token_metrics:
            self.token_metrics[token] = TokenMetrics(address=token)
            
        metrics = self.token_metrics[token]
        timestamp = tx_data.get('blockTime', 0)
        
        # Update basic metrics
        metrics.transaction_count += 1
        metrics.last_seen = max(metrics.last_seen, timestamp)
        if not metrics.first_seen:
            metrics.first_seen = timestamp
            
        # Track addresses
        if from_addr := tx_data.get('from'):
            metrics.unique_senders.add(from_addr)
        if to_addr := tx_data.get('to'):
            metrics.unique_receivers.add(to_addr)
            
        # Track amounts
        amount = tx_data.get('amount', 0)
        if amount:
            metrics.total_volume += amount
            metrics.max_transfer_amount = max(metrics.max_transfer_amount, amount)
            metrics.avg_transfer_amount = metrics.total_volume / metrics.transaction_count
            
        # Store transaction history
        if token not in self.transaction_history:
            self.transaction_history[token] = []
        self.transaction_history[token].append(tx_data)
        
    def analyze_transaction_patterns(self, token: str) -> Dict[str, int]:
        """Analyze transaction patterns for a token."""
        patterns = {
            "circular_transfers": 0,
            "self_transfers": 0,
            "large_transfers": 0,
            "rapid_transfers": 0
        }
        
        if token not in self.transaction_history:
            return patterns
            
        transactions = self.transaction_history[token]
        seen_addresses = set()
        last_transfer_time = 0
        
        for tx in transactions:
            # Check for self transfers
            if tx.get("from") == tx.get("to"):
                patterns["self_transfers"] += 1
                
            # Check for large transfers
            metrics = self.token_metrics.get(token)
            if metrics and metrics.avg_transfer_amount:
                if tx.get("amount", 0) > metrics.avg_transfer_amount * 3:
                    patterns["large_transfers"] += 1
                    
            # Check for rapid transfers
            current_time = tx.get("blockTime", 0)
            if last_transfer_time > 0 and current_time - last_transfer_time < 10:
                patterns["rapid_transfers"] += 1
            last_transfer_time = current_time
            
            # Track addresses for circular transfer detection
            if from_addr := tx.get("from"):
                seen_addresses.add(from_addr)
                
            # Check for circular transfers
            if tx.get("to") in seen_addresses:
                patterns["circular_transfers"] += 1
                
        return patterns
        
    def analyze_time_based_metrics(self, token: str) -> Dict[str, Any]:
        """Analyze time-based metrics for a token."""
        metrics = {
            "hourly_volume": [],
            "hourly_transactions": [],
            "peak_activity_hours": [],
            "inactive_periods": []
        }
        
        if token not in self.transaction_history:
            return metrics
            
        transactions = self.transaction_history[token]
        hourly_data = defaultdict(lambda: {"volume": 0.0, "count": 0})
        
        # Process transactions by hour
        for tx in transactions:
            hour = int(tx.get("blockTime", 0) / 3600)
            hourly_data[hour]["volume"] += tx.get("amount", 0)
            hourly_data[hour]["count"] += 1
            
        # Sort hours and calculate metrics
        sorted_hours = sorted(hourly_data.keys())
        if not sorted_hours:
            return metrics
            
        # Calculate hourly metrics
        for hour in sorted_hours:
            metrics["hourly_volume"].append(hourly_data[hour]["volume"])
            metrics["hourly_transactions"].append(hourly_data[hour]["count"])
            
            # Identify peak activity hours (top 10% by transaction count)
            if hourly_data[hour]["count"] > sum(metrics["hourly_transactions"]) / len(metrics["hourly_transactions"]) * 1.5:
                metrics["peak_activity_hours"].append(hour)
                
        # Find inactive periods (gaps > 1 hour)
        for i in range(len(sorted_hours) - 1):
            gap = sorted_hours[i + 1] - sorted_hours[i]
            if gap > 1:
                metrics["inactive_periods"].append({
                    "start": sorted_hours[i],
                    "end": sorted_hours[i + 1],
                    "duration": gap
                })
                
        return metrics
        
    def get_token_stats(self, token: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive statistics for a token."""
        if token not in self.token_metrics:
            return None
            
        metrics = self.token_metrics[token]
        time_range = metrics.last_seen - metrics.first_seen
        
        # Calculate growth rates
        if time_range > 0:
            holder_growth_rate = metrics.holder_count / (time_range / 3600)  # Per hour
            volume_growth_rate = metrics.total_volume / (time_range / 3600)  # Per hour
            transactions_per_hour = metrics.transaction_count / (time_range / 3600)
        else:
            holder_growth_rate = 0
            volume_growth_rate = 0
            transactions_per_hour = 0
            
        return {
            "address": metrics.address,
            "first_seen": metrics.first_seen,
            "last_seen": metrics.last_seen,
            "transaction_count": metrics.transaction_count,
            "mint_operations": metrics.mint_operations,
            "transfer_operations": metrics.transfer_operations,
            "holder_count": metrics.holder_count,
            "total_volume": metrics.total_volume,
            "confidence_score": metrics.confidence_score,
            "activity_metrics": {
                "unique_senders": len(metrics.unique_senders),
                "unique_receivers": len(metrics.unique_receivers),
                "avg_transfer_amount": metrics.avg_transfer_amount,
                "max_transfer_amount": metrics.max_transfer_amount,
                "initial_mint_amount": metrics.initial_mint_amount,
                "transactions_per_hour": transactions_per_hour,
                "holder_growth_rate": holder_growth_rate,
                "volume_growth_rate": volume_growth_rate
            },
            "transaction_patterns": self.analyze_transaction_patterns(metrics.address),
            "program_interactions": self.program_interactions.get(metrics.address, {}),
            "activity_intervals": metrics.activity_intervals,
            "time_based_metrics": self.analyze_time_based_metrics(metrics.address)
        }
