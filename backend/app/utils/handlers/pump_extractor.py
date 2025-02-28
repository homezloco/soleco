"""
Pump Extractor - Handles extraction and analysis of pump and dump activities on Solana
"""

from typing import Dict, Any, List, Optional, Set
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PumpExtractor:
    """Handles extraction and analysis of pump and dump activities"""
    
    def __init__(self):
        """Initialize the pump extractor"""
        self.pump_operations: List[Dict] = []
        self.stats = {
            'total_pump_indicators': 0,
            'indicator_types': {
                'volume_spike': 0,
                'price_spike': 0,
                'holder_concentration': 0,
                'wash_trading': 0,
                'other': 0
            },
            'token_stats': {},
            'volume_stats': {
                'total_volume': 0,
                'volume_spikes': [],
                'volume_distribution': {}
            },
            'price_stats': {
                'price_changes': [],
                'price_spikes': [],
                'volatility_metrics': {}
            },
            'trading_stats': {
                'total_trades': 0,
                'unique_traders': set(),
                'trade_frequency': {},
                'wash_trading_indicators': []
            },
            'error_stats': {
                'total_errors': 0,
                'error_types': {}
            }
        }
        self.processed_txs: Set[str] = set()
        
    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a single block for pump and dump indicators"""
        if not block:
            logger.warning("Empty block data received")
            return
            
        try:
            transactions = block.get('transactions', [])
            for tx in transactions:
                self._process_transaction(tx, block.get('blockTime'))
                
            logger.debug(f"Processed block with {len(transactions)} transactions")
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            
    def _process_transaction(self, transaction: Dict[str, Any], block_time: int) -> None:
        """Process a single transaction for pump and dump indicators"""
        try:
            if not transaction:
                return
                
            # Extract transaction data
            message = transaction.get('message', {})
            instructions = message.get('instructions', [])
            account_keys = message.get('accountKeys', [])
            
            # Process each instruction
            for instruction in instructions:
                if self._is_trading_instruction(instruction):
                    self._process_trading_operation(
                        instruction,
                        account_keys,
                        transaction,
                        block_time
                    )
                    
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            
    def _is_trading_instruction(self, instruction: Dict[str, Any]) -> bool:
        """Check if instruction is related to trading"""
        try:
            program_id = instruction.get('programId', '').lower()
            # Check for DEX programs, AMMs, etc.
            trading_programs = {
                'serum', 'raydium', 'orca', 'jupiter'
            }
            return any(prog in program_id for prog in trading_programs)
            
        except Exception as e:
            logger.error(f"Error checking trading instruction: {str(e)}")
            return False
            
    def _process_trading_operation(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str],
        transaction: Dict[str, Any],
        block_time: int
    ) -> None:
        """Process trading operation details"""
        try:
            # Extract operation details
            trade_info = self._extract_trade_info(instruction, account_keys)
            
            if not trade_info:
                return
                
            token_address = trade_info['token_address']
            
            # Initialize token stats if needed
            if token_address not in self.stats['token_stats']:
                self.stats['token_stats'][token_address] = {
                    'total_trades': 0,
                    'total_volume': 0,
                    'price_history': [],
                    'volume_history': [],
                    'unique_traders': set(),
                    'indicators': {
                        'volume_spike': 0,
                        'price_spike': 0,
                        'holder_concentration': 0,
                        'wash_trading': 0,
                        'other': 0
                    },
                    'first_seen': block_time,
                    'last_seen': block_time
                }
                
            # Update token stats
            token_stats = self.stats['token_stats'][token_address]
            token_stats['total_trades'] += 1
            token_stats['last_seen'] = block_time
            
            # Extract transaction signature
            signature = transaction.get('signatures', [None])[0]
            if signature and signature not in self.processed_txs:
                self.processed_txs.add(signature)
                
                # Extract trade details
                trade_details = self._extract_trade_details(
                    instruction,
                    account_keys,
                    transaction,
                    block_time,
                    trade_info
                )
                
                if trade_details:
                    # Update volume stats
                    self._update_volume_stats(trade_details, token_address)
                    
                    # Update price stats
                    self._update_price_stats(trade_details, token_address)
                    
                    # Update trading stats
                    self._update_trading_stats(trade_details, token_address)
                    
                    # Check for pump indicators
                    indicators = self._check_pump_indicators(
                        trade_details,
                        token_address
                    )
                    
                    if indicators:
                        # Store pump operation
                        self.pump_operations.append({
                            'signature': signature,
                            'token': token_address,
                            'indicators': indicators,
                            'trade_details': trade_details,
                            'block_time': block_time,
                            'timestamp': datetime.fromtimestamp(block_time).isoformat() if block_time else None
                        })
                        
                        # Update indicator stats
                        for indicator in indicators:
                            self.stats['indicator_types'][indicator] += 1
                            token_stats['indicators'][indicator] += 1
                            
                        self.stats['total_pump_indicators'] += len(indicators)
                        
        except Exception as e:
            logger.error(f"Error processing trading operation: {str(e)}")
            self.stats['error_stats']['total_errors'] += 1
            error_type = type(e).__name__
            self.stats['error_stats']['error_types'][error_type] = \
                self.stats['error_stats']['error_types'].get(error_type, 0) + 1
                
    def _extract_trade_info(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract trade information from instruction"""
        try:
            # This is a placeholder - implement actual trade info extraction
            # based on instruction data and account keys
            accounts = instruction.get('accounts', [])
            if not accounts:
                return None
                
            return {
                'token_address': account_keys[accounts[0]],
                'market': None,  # Extract market address
                'program': instruction.get('programId')
            }
            
        except Exception as e:
            logger.error(f"Error extracting trade info: {str(e)}")
            return None
            
    def _extract_trade_details(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str],
        transaction: Dict[str, Any],
        block_time: int,
        trade_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract detailed information about the trade"""
        try:
            return {
                'accounts': [
                    account_keys[idx]
                    for idx in instruction.get('accounts', [])
                ],
                'data': instruction.get('data'),
                'program_id': instruction.get('programId'),
                'amount': self._extract_amount(instruction),
                'price': self._extract_price(instruction),
                'trade_info': trade_info,
                'success': transaction.get('meta', {}).get('status', {}).get('Ok') is not None,
                'error': transaction.get('meta', {}).get('error'),
                'block_time': block_time,
                'timestamp': datetime.fromtimestamp(block_time).isoformat() if block_time else None
            }
            
        except Exception as e:
            logger.error(f"Error extracting trade details: {str(e)}")
            return None
            
    def _extract_amount(self, instruction: Dict[str, Any]) -> int:
        """Extract amount from instruction"""
        try:
            # This is a placeholder - implement actual amount extraction
            # based on instruction data
            return 0
            
        except Exception as e:
            logger.error(f"Error extracting amount: {str(e)}")
            return 0
            
    def _extract_price(self, instruction: Dict[str, Any]) -> float:
        """Extract price from instruction"""
        try:
            # This is a placeholder - implement actual price extraction
            # based on instruction data
            return 0.0
            
        except Exception as e:
            logger.error(f"Error extracting price: {str(e)}")
            return 0.0
            
    def _update_volume_stats(
        self,
        trade_details: Dict[str, Any],
        token_address: str
    ) -> None:
        """Update volume statistics"""
        try:
            amount = trade_details.get('amount', 0)
            self.stats['volume_stats']['total_volume'] += amount
            
            # Update token volume history
            token_stats = self.stats['token_stats'][token_address]
            token_stats['volume_history'].append({
                'amount': amount,
                'block_time': trade_details.get('block_time'),
                'timestamp': trade_details.get('timestamp')
            })
            
            # Check for volume spikes
            if self._is_volume_spike(amount, token_stats['volume_history']):
                self.stats['volume_stats']['volume_spikes'].append({
                    'token': token_address,
                    'amount': amount,
                    'block_time': trade_details.get('block_time'),
                    'timestamp': trade_details.get('timestamp')
                })
                
        except Exception as e:
            logger.error(f"Error updating volume stats: {str(e)}")
            
    def _update_price_stats(
        self,
        trade_details: Dict[str, Any],
        token_address: str
    ) -> None:
        """Update price statistics"""
        try:
            price = trade_details.get('price', 0.0)
            token_stats = self.stats['token_stats'][token_address]
            
            # Update price history
            token_stats['price_history'].append({
                'price': price,
                'block_time': trade_details.get('block_time'),
                'timestamp': trade_details.get('timestamp')
            })
            
            # Check for price spikes
            if self._is_price_spike(price, token_stats['price_history']):
                self.stats['price_stats']['price_spikes'].append({
                    'token': token_address,
                    'price': price,
                    'block_time': trade_details.get('block_time'),
                    'timestamp': trade_details.get('timestamp')
                })
                
        except Exception as e:
            logger.error(f"Error updating price stats: {str(e)}")
            
    def _update_trading_stats(
        self,
        trade_details: Dict[str, Any],
        token_address: str
    ) -> None:
        """Update trading statistics"""
        try:
            self.stats['trading_stats']['total_trades'] += 1
            
            # Update unique traders
            accounts = trade_details.get('accounts', [])
            self.stats['trading_stats']['unique_traders'].update(accounts)
            
            # Update token traders
            token_stats = self.stats['token_stats'][token_address]
            token_stats['unique_traders'].update(accounts)
            
            # Check for wash trading
            if self._is_wash_trading(accounts, token_stats['unique_traders']):
                self.stats['trading_stats']['wash_trading_indicators'].append({
                    'token': token_address,
                    'accounts': accounts,
                    'block_time': trade_details.get('block_time'),
                    'timestamp': trade_details.get('timestamp')
                })
                
        except Exception as e:
            logger.error(f"Error updating trading stats: {str(e)}")
            
    def _is_volume_spike(
        self,
        current_volume: int,
        volume_history: List[Dict[str, Any]]
    ) -> bool:
        """Check if current volume represents a spike"""
        try:
            if len(volume_history) < 10:  # Need more history
                return False
                
            # Calculate average volume
            recent_volumes = [v['amount'] for v in volume_history[-10:]]
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            
            # Consider it a spike if volume is 3x the average
            return current_volume > (avg_volume * 3)
            
        except Exception as e:
            logger.error(f"Error checking volume spike: {str(e)}")
            return False
            
    def _is_price_spike(
        self,
        current_price: float,
        price_history: List[Dict[str, Any]]
    ) -> bool:
        """Check if current price represents a spike"""
        try:
            if len(price_history) < 10:  # Need more history
                return False
                
            # Calculate average price
            recent_prices = [p['price'] for p in price_history[-10:]]
            avg_price = sum(recent_prices) / len(recent_prices)
            
            # Consider it a spike if price is 2x the average
            return current_price > (avg_price * 2)
            
        except Exception as e:
            logger.error(f"Error checking price spike: {str(e)}")
            return False
            
    def _is_wash_trading(
        self,
        current_accounts: List[str],
        historical_accounts: Set[str]
    ) -> bool:
        """Check for wash trading indicators"""
        try:
            # This is a simplified check - implement more sophisticated detection
            return len(current_accounts) >= 2 and \
                   len(set(current_accounts)) < len(current_accounts)
                   
        except Exception as e:
            logger.error(f"Error checking wash trading: {str(e)}")
            return False
            
    def _check_pump_indicators(
        self,
        trade_details: Dict[str, Any],
        token_address: str
    ) -> List[str]:
        """Check for pump and dump indicators"""
        try:
            indicators = []
            token_stats = self.stats['token_stats'][token_address]
            
            # Check volume spike
            if self._is_volume_spike(
                trade_details.get('amount', 0),
                token_stats['volume_history']
            ):
                indicators.append('volume_spike')
                
            # Check price spike
            if self._is_price_spike(
                trade_details.get('price', 0.0),
                token_stats['price_history']
            ):
                indicators.append('price_spike')
                
            # Check holder concentration
            if len(token_stats['unique_traders']) < 10 and \
               token_stats['total_trades'] > 50:
                indicators.append('holder_concentration')
                
            # Check wash trading
            if self._is_wash_trading(
                trade_details.get('accounts', []),
                token_stats['unique_traders']
            ):
                indicators.append('wash_trading')
                
            return indicators
            
        except Exception as e:
            logger.error(f"Error checking pump indicators: {str(e)}")
            return []
            
    def get_results(self) -> Dict[str, Any]:
        """Get the accumulated results and statistics"""
        return {
            'pump_operations': self.pump_operations,
            'stats': {
                **self.stats,
                'trading_stats': {
                    **self.stats['trading_stats'],
                    'unique_traders': len(self.stats['trading_stats']['unique_traders'])
                },
                'token_stats': {
                    token: {
                        **stats,
                        'unique_traders': len(stats['unique_traders'])
                    }
                    for token, stats in self.stats['token_stats'].items()
                }
            },
            'total_processed': len(self.processed_txs)
        }
        
    def reset(self) -> None:
        """Reset the extractor state"""
        self.pump_operations = []
        self.stats = {
            'total_pump_indicators': 0,
            'indicator_types': {
                'volume_spike': 0,
                'price_spike': 0,
                'holder_concentration': 0,
                'wash_trading': 0,
                'other': 0
            },
            'token_stats': {},
            'volume_stats': {
                'total_volume': 0,
                'volume_spikes': [],
                'volume_distribution': {}
            },
            'price_stats': {
                'price_changes': [],
                'price_spikes': [],
                'volatility_metrics': {}
            },
            'trading_stats': {
                'total_trades': 0,
                'unique_traders': set(),
                'trade_frequency': {},
                'wash_trading_indicators': []
            },
            'error_stats': {
                'total_errors': 0,
                'error_types': {}
            }
        }
        self.processed_txs = set()
