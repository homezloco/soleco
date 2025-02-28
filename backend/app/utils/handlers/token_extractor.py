"""
Token Extractor - Handles extraction and analysis of token activities on Solana
"""

from typing import Dict, Any, List, Optional, Set
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TokenExtractor:
    """Handles extraction and analysis of token-related activities"""
    
    def __init__(self):
        """Initialize the token extractor"""
        self.token_operations: List[Dict] = []
        self.stats = {
            'total_token_ops': 0,
            'operation_types': {
                'transfer': 0,
                'mint': 0,
                'burn': 0,
                'freeze': 0,
                'thaw': 0,
                'approve': 0,
                'revoke': 0,
                'other': 0
            },
            'token_stats': {},
            'transfer_stats': {
                'total_transfers': 0,
                'total_volume': 0,
                'unique_senders': set(),
                'unique_receivers': set(),
                'transfer_history': []
            },
            'mint_stats': {
                'total_mints': 0,
                'total_supply_changes': [],
                'mint_authorities': set(),
                'freeze_authorities': set()
            },
            'holder_stats': {
                'total_holders': 0,
                'holder_distribution': {},
                'top_holders': []
            },
            'error_stats': {
                'total_errors': 0,
                'error_types': {}
            }
        }
        self.processed_txs: Set[str] = set()
        
    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a single block for token activities"""
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
        """Process a single transaction for token activities"""
        try:
            if not transaction:
                return
                
            # Extract transaction data
            message = transaction.get('message', {})
            instructions = message.get('instructions', [])
            account_keys = message.get('accountKeys', [])
            
            # Process each instruction
            for instruction in instructions:
                if self._is_token_instruction(instruction):
                    self._process_token_operation(
                        instruction,
                        account_keys,
                        transaction,
                        block_time
                    )
                    
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            
    def _is_token_instruction(self, instruction: Dict[str, Any]) -> bool:
        """Check if instruction is token-related"""
        try:
            program_id = instruction.get('programId', '').lower()
            return 'token' in program_id or 'spl' in program_id
            
        except Exception as e:
            logger.error(f"Error checking token instruction: {str(e)}")
            return False
            
    def _process_token_operation(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str],
        transaction: Dict[str, Any],
        block_time: int
    ) -> None:
        """Process token operation details"""
        try:
            # Extract operation details
            operation_type = self._determine_operation_type(instruction)
            token_info = self._extract_token_info(instruction, account_keys)
            
            if not token_info:
                return
                
            # Update operation counts
            self.stats['operation_types'][operation_type] += 1
            
            # Update token stats
            token_address = token_info['address']
            if token_address not in self.stats['token_stats']:
                self.stats['token_stats'][token_address] = {
                    'total_operations': 0,
                    'operation_types': {
                        'transfer': 0,
                        'mint': 0,
                        'burn': 0,
                        'freeze': 0,
                        'thaw': 0,
                        'approve': 0,
                        'revoke': 0,
                        'other': 0
                    },
                    'total_volume': 0,
                    'holders': set(),
                    'mint_authority': None,
                    'freeze_authority': None,
                    'decimals': token_info.get('decimals'),
                    'supply': token_info.get('supply', 0),
                    'first_seen': block_time,
                    'last_seen': block_time
                }
                
            token_stats = self.stats['token_stats'][token_address]
            token_stats['total_operations'] += 1
            token_stats['operation_types'][operation_type] += 1
            token_stats['last_seen'] = block_time
            
            # Extract transaction signature
            signature = transaction.get('signatures', [None])[0]
            if signature and signature not in self.processed_txs:
                self.processed_txs.add(signature)
                
                # Extract operation details
                operation_details = self._extract_operation_details(
                    instruction,
                    account_keys,
                    transaction,
                    block_time,
                    token_info
                )
                
                if operation_details:
                    # Update transfer stats
                    if operation_type == 'transfer':
                        self._update_transfer_stats(operation_details, token_address)
                        
                    # Update mint stats
                    elif operation_type == 'mint':
                        self._update_mint_stats(operation_details, token_address)
                        
                    # Update holder stats
                    self._update_holder_stats(operation_details, token_address)
                    
                    # Store operation data
                    self.token_operations.append({
                        'signature': signature,
                        'token': token_address,
                        'operation_type': operation_type,
                        'operation_details': operation_details,
                        'block_time': block_time,
                        'timestamp': datetime.fromtimestamp(block_time).isoformat() if block_time else None
                    })
                    
            self.stats['total_token_ops'] += 1
            
        except Exception as e:
            logger.error(f"Error processing token operation: {str(e)}")
            self.stats['error_stats']['total_errors'] += 1
            error_type = type(e).__name__
            self.stats['error_stats']['error_types'][error_type] = \
                self.stats['error_stats']['error_types'].get(error_type, 0) + 1
                
    def _determine_operation_type(self, instruction: Dict[str, Any]) -> str:
        """Determine the type of token operation"""
        try:
            # This is a simplified version - implement actual logic based on
            # instruction data and program calls
            data = str(instruction.get('data', '')).lower()
            
            if 'transfer' in data:
                return 'transfer'
            elif 'mint' in data:
                return 'mint'
            elif 'burn' in data:
                return 'burn'
            elif 'freeze' in data:
                return 'freeze'
            elif 'thaw' in data:
                return 'thaw'
            elif 'approve' in data:
                return 'approve'
            elif 'revoke' in data:
                return 'revoke'
            else:
                return 'other'
                
        except Exception as e:
            logger.error(f"Error determining operation type: {str(e)}")
            return 'other'
            
    def _extract_token_info(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract token information from instruction"""
        try:
            # This is a placeholder - implement actual token info extraction
            # based on instruction data and account keys
            accounts = instruction.get('accounts', [])
            if not accounts:
                return None
                
            return {
                'address': account_keys[accounts[0]],
                'decimals': None,  # Extract from account data
                'supply': None,    # Extract from account data
                'mint_authority': None,  # Extract from account data
                'freeze_authority': None  # Extract from account data
            }
            
        except Exception as e:
            logger.error(f"Error extracting token info: {str(e)}")
            return None
            
    def _extract_operation_details(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str],
        transaction: Dict[str, Any],
        block_time: int,
        token_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract detailed information about the token operation"""
        try:
            return {
                'accounts': [
                    account_keys[idx]
                    for idx in instruction.get('accounts', [])
                ],
                'data': instruction.get('data'),
                'program_id': instruction.get('programId'),
                'amount': self._extract_amount(instruction),
                'token_info': token_info,
                'success': transaction.get('meta', {}).get('status', {}).get('Ok') is not None,
                'error': transaction.get('meta', {}).get('error'),
                'block_time': block_time,
                'timestamp': datetime.fromtimestamp(block_time).isoformat() if block_time else None
            }
            
        except Exception as e:
            logger.error(f"Error extracting operation details: {str(e)}")
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
            
    def _update_transfer_stats(
        self,
        operation_details: Dict[str, Any],
        token_address: str
    ) -> None:
        """Update transfer statistics"""
        try:
            self.stats['transfer_stats']['total_transfers'] += 1
            amount = operation_details.get('amount', 0)
            self.stats['transfer_stats']['total_volume'] += amount
            
            accounts = operation_details.get('accounts', [])
            if len(accounts) >= 2:
                self.stats['transfer_stats']['unique_senders'].add(accounts[0])
                self.stats['transfer_stats']['unique_receivers'].add(accounts[1])
                
            self.stats['transfer_stats']['transfer_history'].append({
                'token': token_address,
                'amount': amount,
                'sender': accounts[0] if len(accounts) > 0 else None,
                'receiver': accounts[1] if len(accounts) > 1 else None,
                'block_time': operation_details.get('block_time'),
                'timestamp': operation_details.get('timestamp')
            })
            
            # Update token-specific volume
            self.stats['token_stats'][token_address]['total_volume'] += amount
            
        except Exception as e:
            logger.error(f"Error updating transfer stats: {str(e)}")
            
    def _update_mint_stats(
        self,
        operation_details: Dict[str, Any],
        token_address: str
    ) -> None:
        """Update mint statistics"""
        try:
            self.stats['mint_stats']['total_mints'] += 1
            
            # Update authorities
            token_info = operation_details.get('token_info', {})
            mint_authority = token_info.get('mint_authority')
            freeze_authority = token_info.get('freeze_authority')
            
            if mint_authority:
                self.stats['mint_stats']['mint_authorities'].add(mint_authority)
            if freeze_authority:
                self.stats['mint_stats']['freeze_authorities'].add(freeze_authority)
                
            # Update supply changes
            amount = operation_details.get('amount', 0)
            self.stats['mint_stats']['total_supply_changes'].append({
                'token': token_address,
                'amount': amount,
                'type': 'mint',
                'authority': mint_authority,
                'block_time': operation_details.get('block_time'),
                'timestamp': operation_details.get('timestamp')
            })
            
            # Update token supply
            self.stats['token_stats'][token_address]['supply'] += amount
            
        except Exception as e:
            logger.error(f"Error updating mint stats: {str(e)}")
            
    def _update_holder_stats(
        self,
        operation_details: Dict[str, Any],
        token_address: str
    ) -> None:
        """Update holder statistics"""
        try:
            accounts = operation_details.get('accounts', [])
            token_stats = self.stats['token_stats'][token_address]
            
            # Update token holders
            token_stats['holders'].update(accounts)
            
            # Update global holder stats
            self.stats['holder_stats']['total_holders'] = sum(
                len(stats['holders'])
                for stats in self.stats['token_stats'].values()
            )
            
            # Update holder distribution
            holder_count = len(token_stats['holders'])
            self.stats['holder_stats']['holder_distribution'][token_address] = holder_count
            
            # Update top holders (maintain sorted list)
            self.stats['holder_stats']['top_holders'] = sorted(
                [
                    {'token': addr, 'holders': len(stats['holders'])}
                    for addr, stats in self.stats['token_stats'].items()
                ],
                key=lambda x: x['holders'],
                reverse=True
            )[:10]  # Keep top 10
            
        except Exception as e:
            logger.error(f"Error updating holder stats: {str(e)}")
            
    def get_results(self) -> Dict[str, Any]:
        """Get the accumulated results and statistics"""
        return {
            'token_operations': self.token_operations,
            'stats': {
                **self.stats,
                'transfer_stats': {
                    **self.stats['transfer_stats'],
                    'unique_senders': len(self.stats['transfer_stats']['unique_senders']),
                    'unique_receivers': len(self.stats['transfer_stats']['unique_receivers'])
                },
                'mint_stats': {
                    **self.stats['mint_stats'],
                    'mint_authorities': len(self.stats['mint_stats']['mint_authorities']),
                    'freeze_authorities': len(self.stats['mint_stats']['freeze_authorities'])
                },
                'token_stats': {
                    token: {
                        **stats,
                        'holders': len(stats['holders'])
                    }
                    for token, stats in self.stats['token_stats'].items()
                }
            },
            'total_processed': len(self.processed_txs)
        }
        
    def reset(self) -> None:
        """Reset the extractor state"""
        self.token_operations = []
        self.stats = {
            'total_token_ops': 0,
            'operation_types': {
                'transfer': 0,
                'mint': 0,
                'burn': 0,
                'freeze': 0,
                'thaw': 0,
                'approve': 0,
                'revoke': 0,
                'other': 0
            },
            'token_stats': {},
            'transfer_stats': {
                'total_transfers': 0,
                'total_volume': 0,
                'unique_senders': set(),
                'unique_receivers': set(),
                'transfer_history': []
            },
            'mint_stats': {
                'total_mints': 0,
                'total_supply_changes': [],
                'mint_authorities': set(),
                'freeze_authorities': set()
            },
            'holder_stats': {
                'total_holders': 0,
                'holder_distribution': {},
                'top_holders': []
            },
            'error_stats': {
                'total_errors': 0,
                'error_types': {}
            }
        }
        self.processed_txs = set()
