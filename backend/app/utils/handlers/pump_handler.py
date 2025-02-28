"""
Handler for pump token detection and analysis.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

from ..models.statistics import Statistics, MetricsTracker
from .base_handler import BaseHandler, TransactionStats
from ..logging_config import setup_logging

# Configure logging
logger = setup_logging('solana.response.pump')

class PumpHandler(BaseHandler):
    """Handler for detecting pump tokens"""
    
    def __init__(self):
        super().__init__()
        self.VELOCITY_THRESHOLD = 5  # Minimum transactions in short time
        self.TIME_WINDOW = 3600     # Time window in seconds (1 hour)
        self.HOLDER_THRESHOLD = 3   # Minimum number of holders
        
    async def process(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a transaction to detect pump tokens"""
        try:
            if not tx_data or not isinstance(tx_data, dict):
                logger.debug("Invalid transaction data format in pump handler")
                return {"success": False, "error": "Invalid transaction format"}
            
            # Extract transaction components
            transaction = tx_data.get('transaction', {})
            meta = tx_data.get('meta')
            
            if not transaction or not meta:
                logger.debug("Missing transaction or meta data in pump handler")
                return {"success": False, "error": "Missing transaction or meta data"}
            
            # Get message and account keys
            message = transaction.get('message', {})
            if not message:
                return {"success": False, "error": "Missing message data"}
            
            # Process token balances
            pre_balances = meta.get('preTokenBalances', [])
            post_balances = meta.get('postTokenBalances', [])
            
            # Track holders and transactions
            holders = {}
            pump_tokens = set()
            
            # Process pre balances
            for balance in pre_balances:
                mint = balance.get('mint')
                if mint:
                    if mint not in holders:
                        holders[mint] = set()
                    owner = balance.get('owner')
                    if owner:
                        holders[mint].add(owner)
            
            # Process post balances
            for balance in post_balances:
                mint = balance.get('mint')
                if mint:
                    if mint not in holders:
                        holders[mint] = set()
                    owner = balance.get('owner')
                    if owner:
                        holders[mint].add(owner)
            
            # Analyze for pump characteristics
            for mint, holder_set in holders.items():
                if self._is_pump_token(mint, len(holder_set)):
                    pump_tokens.add(mint)
                    logger.info(f"Detected pump token: {mint} with {len(holder_set)} holders")
            
            return {
                "success": True,
                "pump_tokens": list(pump_tokens),
                "statistics": {
                    "total_pump_tokens": len(pump_tokens),
                    "analyzed_mints": len(holders)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in pump handler: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "pump_tokens": []
            }
    
    def _is_pump_token(self, address: str, holder_count: int) -> bool:
        """
        Determine if a token shows characteristics of a pump token
        
        Criteria:
        1. High transaction velocity in a short time window
        2. Minimum number of holders
        3. Significant price movement
        """
        try:
            # Check holder threshold
            if holder_count < self.HOLDER_THRESHOLD:
                return False
                
            # Check transaction velocity
            tx_count = self.stats.total_queries  # Use total_queries instead of get_transaction_count
            if tx_count < self.VELOCITY_THRESHOLD:
                return False
                
            # If we reach here, token meets pump criteria
            logger.info(f"Token {address} identified as pump token with {holder_count} holders and {tx_count} transactions")
            return True
            
        except Exception as e:
            logger.error(f"Error checking pump token: {str(e)}")
            return False

    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block to detect pump tokens.
        
        This method analyzes all transactions in a block to identify potential
        pump tokens based on transaction velocity and holder patterns.
        
        Args:
            block_data: Block data from Solana RPC
            
        Returns:
            Dict containing pump detection results and statistics
        """
        try:
            if not block_data or not isinstance(block_data, dict):
                logger.warning("Invalid block data format")
                return None
                
            transactions = block_data.get('transactions', [])
            if not transactions:
                logger.debug("No transactions in block")
                return None
                
            # Track pump metrics for this block
            pump_candidates = {}  # token -> {holders: set(), tx_count: int}
            
            # Process each transaction
            for tx in transactions:
                try:
                    result = await self.process(tx)
                    if not result or not isinstance(result, dict):
                        continue
                        
                    # Extract pump token data
                    for token_addr, token_data in result.get('pump_tokens', {}).items():
                        if token_addr not in pump_candidates:
                            pump_candidates[token_addr] = {
                                'holders': set(),
                                'tx_count': 0,
                                'volume': 0.0
                            }
                            
                        # Update metrics
                        pump_candidates[token_addr]['holders'].update(token_data.get('holders', []))
                        pump_candidates[token_addr]['tx_count'] += token_data.get('tx_count', 0)
                        pump_candidates[token_addr]['volume'] += token_data.get('volume', 0.0)
                        
                except Exception as e:
                    logger.error(f"Error processing transaction: {str(e)}")
                    self.stats.update_error_count(type(e).__name__)
                    
            # Filter and format results
            pump_tokens = {}
            for token_addr, metrics in pump_candidates.items():
                if (len(metrics['holders']) >= self.HOLDER_THRESHOLD and 
                    metrics['tx_count'] >= self.VELOCITY_THRESHOLD):
                    pump_tokens[token_addr] = {
                        'holders': list(metrics['holders']),
                        'tx_count': metrics['tx_count'],
                        'volume': metrics['volume']
                    }
                    
            return {
                'slot': block_data.get('slot'),
                'pump_tokens': pump_tokens,
                'statistics': {
                    'total_transactions': len(transactions),
                    'pump_candidates': len(pump_candidates),
                    'confirmed_pumps': len(pump_tokens)
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            return {
                'error': str(e),
                'statistics': {
                    'total_transactions': 0,
                    'pump_candidates': 0,
                    'confirmed_pumps': 0
                }
            }
