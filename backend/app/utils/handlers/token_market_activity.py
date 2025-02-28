"""
Handler for analyzing token market activity through metadata and on-chain behavior.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

from ..models.statistics import Statistics, MetricsTracker
from .base_handler import BaseHandler, TransactionStats
from ..logging_config import setup_logging

# Configure logging
logger = setup_logging('solana.response.market_activity')

class TokenMarketActivityHandler(BaseHandler):
    """Handler for analyzing token market activity and behavior patterns"""
    
    def __init__(self):
        super().__init__()
        # Transaction velocity thresholds
        self.VELOCITY_THRESHOLD = 5  # Minimum transactions in short time
        self.TIME_WINDOW = 3600     # Time window in seconds (1 hour)
        self.HOLDER_THRESHOLD = 3   # Minimum number of holders
        
        # Metadata pattern indicators
        self.SUSPICIOUS_INDICATORS = {
            'moon', 'safe', 'fair', 'gem', 'elon', 'doge',
            'shib', 'inu', 'pepe', 'ai', 'gpt', 'chad', 'wojak',
            'fomo', 'yolo', 'lambo', 'rocket', '🚀', '💎', '🌙'
        }
        
        # Suspicious patterns in addresses/names
        self.SUSPICIOUS_PATTERNS = [
            r'safe$',
            r'gem$',
            r'[A-Z]{4,}(safe|gem|moon)',
            r'(ai|gpt|chad)\d+',
            r'(fomo|yolo|lambo)\d*'
        ]
        
        self.known_suspicious_tokens = set()
        self.validated_addresses = set()
        self.market_activity_stats = {}
        
    async def process(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a transaction to analyze token market activity"""
        try:
            if not tx_data or not isinstance(tx_data, dict):
                logger.debug("Invalid transaction data format")
                return {"success": False, "error": "Invalid transaction format"}
            
            # Extract transaction components
            transaction = tx_data.get('transaction', {})
            meta = tx_data.get('meta')
            
            if not transaction or not meta:
                logger.debug("Missing transaction or meta data")
                return {"success": False, "error": "Missing transaction or meta data"}
            
            # Get message and account keys
            message = transaction.get('message', {})
            if not message:
                return {"success": False, "error": "Missing message data"}
            
            # Process token balances
            pre_balances = meta.get('preTokenBalances', [])
            post_balances = meta.get('postTokenBalances', [])
            
            # Track holders and activity
            holders = {}
            active_tokens = set()
            
            # Process pre/post balances
            for balance in pre_balances + post_balances:
                mint = balance.get('mint')
                if mint:
                    if mint not in holders:
                        holders[mint] = set()
                    owner = balance.get('owner')
                    if owner:
                        holders[mint].add(owner)
            
            # Analyze market activity patterns
            suspicious_tokens = []
            for mint, holder_set in holders.items():
                activity_score = self._analyze_market_activity(mint, len(holder_set))
                metadata_score = self._analyze_token_metadata(mint)
                
                if activity_score > 0.7 or metadata_score > 0.7:
                    suspicious_tokens.append({
                        'address': mint,
                        'holders': len(holder_set),
                        'activity_score': activity_score,
                        'metadata_score': metadata_score,
                        'combined_score': (activity_score + metadata_score) / 2
                    })
            
            return {
                "success": True,
                "suspicious_tokens": suspicious_tokens,
                "statistics": {
                    "total_analyzed": len(holders),
                    "suspicious_count": len(suspicious_tokens),
                    "average_holders": sum(len(h) for h in holders.values()) / len(holders) if holders else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in market activity analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "suspicious_tokens": []
            }
    
    def _analyze_market_activity(self, address: str, holder_count: int) -> float:
        """
        Analyze token market activity patterns
        
        Returns:
            Float between 0-1 indicating suspicion level based on activity
        """
        try:
            score = 0.0
            
            # Check holder threshold
            if holder_count >= self.HOLDER_THRESHOLD:
                score += 0.3
                
            # Check transaction velocity
            tx_count = self.stats.total_queries
            if tx_count >= self.VELOCITY_THRESHOLD:
                score += 0.4
                
            # Check if known suspicious
            if address in self.known_suspicious_tokens:
                score += 0.3
                
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error analyzing market activity: {str(e)}")
            return 0.0
            
    def _analyze_token_metadata(self, address: str, metadata: Dict[str, Any] = None) -> float:
        """
        Analyze token metadata for suspicious patterns
        
        Returns:
            Float between 0-1 indicating suspicion level based on metadata
        """
        try:
            if not metadata:
                return 0.0
                
            score = 0.0
            name = metadata.get('name', '').lower()
            symbol = metadata.get('symbol', '').lower()
            
            # Check for suspicious indicators
            for indicator in self.SUSPICIOUS_INDICATORS:
                if indicator in name or indicator in symbol:
                    score += 0.2
                    break
                    
            # Check for suspicious patterns
            for pattern in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, name) or re.search(pattern, symbol):
                    score += 0.3
                    break
                    
            # Check address patterns
            if any(re.search(pattern, address) for pattern in self.SUSPICIOUS_PATTERNS):
                score += 0.2
                
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error analyzing token metadata: {str(e)}")
            return 0.0

    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block to analyze token market activity.
        
        This method analyzes all transactions in a block to identify unusual
        market activity patterns based on transaction velocity and holder patterns.
        
        Args:
            block_data: Block data from Solana RPC
            
        Returns:
            Dict containing analysis results and statistics
        """
        try:
            if not block_data or not isinstance(block_data, dict):
                logger.warning("Invalid block data format")
                return None
                
            transactions = block_data.get('transactions', [])
            if not transactions:
                logger.debug("No transactions in block")
                return None
                
            # Track market activity metrics for this block
            token_metrics = {}  # token -> {holders, tx_count, volume, etc}
            
            # Process each transaction
            for tx in transactions:
                try:
                    result = await self.process(tx)
                    if not result or not isinstance(result, dict):
                        continue
                        
                    # Extract token activity data
                    for token_data in result.get('suspicious_tokens', []):
                        token_addr = token_data['address']
                        if token_addr not in token_metrics:
                            token_metrics[token_addr] = {
                                'holders': set(),
                                'tx_count': 0,
                                'volume': 0.0,
                                'activity_score': 0.0,
                                'metadata_score': 0.0
                            }
                            
                        metrics = token_metrics[token_addr]
                        metrics['activity_score'] = max(metrics['activity_score'], 
                                                      token_data['activity_score'])
                        metrics['metadata_score'] = max(metrics['metadata_score'], 
                                                      token_data['metadata_score'])
                        metrics['tx_count'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing transaction: {str(e)}")
                    self.stats.update_error_count(type(e).__name__)
                    
            # Filter and format results
            high_activity_tokens = {}
            for token_addr, metrics in token_metrics.items():
                if metrics['activity_score'] > 0.7 or metrics['metadata_score'] > 0.7:
                    high_activity_tokens[token_addr] = {
                        'tx_count': metrics['tx_count'],
                        'activity_score': metrics['activity_score'],
                        'metadata_score': metrics['metadata_score'],
                        'combined_score': (metrics['activity_score'] + metrics['metadata_score']) / 2
                    }
                    
            return {
                'slot': block_data.get('slot'),
                'high_activity_tokens': high_activity_tokens,
                'statistics': {
                    'total_transactions': len(transactions),
                    'analyzed_tokens': len(token_metrics),
                    'high_activity_count': len(high_activity_tokens)
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            return {
                'error': str(e),
                'statistics': {
                    'total_transactions': 0,
                    'analyzed_tokens': 0,
                    'high_activity_count': 0
                }
            }
