"""
Wallet Extractor - Handles extraction and analysis of wallet activities on Solana
"""

from typing import Dict, Any, List, Optional, Set
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WalletExtractor:
    """Handles extraction and analysis of wallet-related activities"""
    
    def __init__(self):
        """Initialize the wallet extractor"""
        self.wallet_operations: List[Dict] = []
        self.stats = {
            'total_wallet_ops': 0,
            'operation_types': {
                'transfer': 0,
                'swap': 0,
                'stake': 0,
                'nft': 0,
                'token': 0,
                'other': 0
            },
            'wallet_stats': {},
            'transfer_stats': {
                'total_transfers': 0,
                'total_volume': 0,
                'unique_senders': set(),
                'unique_receivers': set(),
                'transfer_history': []
            },
            'token_stats': {
                'total_token_txs': 0,
                'unique_tokens': set(),
                'token_volumes': {},
                'token_holders': {}
            },
            'interaction_stats': {
                'programs_used': {},
                'contracts_called': {},
                'interaction_frequency': {}
            },
            'error_stats': {
                'total_errors': 0,
                'error_types': {}
            }
        }
        self.processed_txs: Set[str] = set()
        
    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a single block for wallet activities"""
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
        """Process a single transaction for wallet activities"""
        try:
            if not transaction:
                return
                
            # Extract transaction data
            message = transaction.get('message', {})
            instructions = message.get('instructions', [])
            account_keys = message.get('accountKeys', [])
            
            # Process each instruction
            for instruction in instructions:
                self._process_wallet_operation(
                    instruction,
                    account_keys,
                    transaction,
                    block_time
                )
                
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            
    def _process_wallet_operation(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str],
        transaction: Dict[str, Any],
        block_time: int
    ) -> None:
        """Process wallet operation details"""
        try:
            # Extract operation details
            operation_type = self._determine_operation_type(instruction)
            wallet_addresses = self._extract_wallet_addresses(instruction, account_keys)
            
            if not wallet_addresses:
                return
                
            # Update operation counts
            self.stats['operation_types'][operation_type] += 1
            
            # Update wallet stats
            for wallet in wallet_addresses:
                if wallet not in self.stats['wallet_stats']:
                    self.stats['wallet_stats'][wallet] = {
                        'total_operations': 0,
                        'operation_types': {
                            'transfer': 0,
                            'swap': 0,
                            'stake': 0,
                            'nft': 0,
                            'token': 0,
                            'other': 0
                        },
                        'total_volume': 0,
                        'unique_interactions': set(),
                        'token_holdings': set(),
                        'first_seen': block_time,
                        'last_seen': block_time
                    }
                    
                wallet_stats = self.stats['wallet_stats'][wallet]
                wallet_stats['total_operations'] += 1
                wallet_stats['operation_types'][operation_type] += 1
                wallet_stats['last_seen'] = block_time
                
            # Extract transaction signature
            signature = transaction.get('signatures', [None])[0]
            if signature and signature not in self.processed_txs:
                self.processed_txs.add(signature)
                
                # Extract operation details
                operation_details = self._extract_operation_details(
                    instruction,
                    account_keys,
                    transaction,
                    block_time
                )
                
                if operation_details:
                    # Update transfer stats
                    if operation_type == 'transfer':
                        self._update_transfer_stats(operation_details)
                        
                    # Update token stats
                    elif operation_type == 'token':
                        self._update_token_stats(operation_details)
                        
                    # Update interaction stats
                    program_id = instruction.get('programId')
                    if program_id:
                        self.stats['interaction_stats']['programs_used'][program_id] = \
                            self.stats['interaction_stats']['programs_used'].get(program_id, 0) + 1
                            
                    # Store operation data
                    self.wallet_operations.append({
                        'signature': signature,
                        'wallets': wallet_addresses,
                        'operation_type': operation_type,
                        'operation_details': operation_details,
                        'block_time': block_time,
                        'timestamp': datetime.fromtimestamp(block_time).isoformat() if block_time else None
                    })
                    
            self.stats['total_wallet_ops'] += 1
            
        except Exception as e:
            logger.error(f"Error processing wallet operation: {str(e)}")
            self.stats['error_stats']['total_errors'] += 1
            error_type = type(e).__name__
            self.stats['error_stats']['error_types'][error_type] = \
                self.stats['error_stats']['error_types'].get(error_type, 0) + 1
                
    def _determine_operation_type(self, instruction: Dict[str, Any]) -> str:
        """Determine the type of wallet operation"""
        try:
            # This is a simplified version - implement actual logic based on
            # instruction data and program calls
            data = str(instruction.get('data', '')).lower()
            program_id = instruction.get('programId', '').lower()
            
            if 'transfer' in data:
                return 'transfer'
            elif 'swap' in data:
                return 'swap'
            elif 'stake' in data:
                return 'stake'
            elif 'nft' in program_id or 'metaplex' in program_id:
                return 'nft'
            elif 'token' in program_id:
                return 'token'
            else:
                return 'other'
                
        except Exception as e:
            logger.error(f"Error determining operation type: {str(e)}")
            return 'other'
            
    def _extract_wallet_addresses(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str]
    ) -> List[str]:
        """Extract wallet addresses from instruction"""
        try:
            # Get all account indices from instruction
            account_indices = instruction.get('accounts', [])
            
            # Convert indices to addresses
            return [
                account_keys[idx]
                for idx in account_indices
                if idx < len(account_keys)
            ]
            
        except Exception as e:
            logger.error(f"Error extracting wallet addresses: {str(e)}")
            return []
            
    def _extract_operation_details(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str],
        transaction: Dict[str, Any],
        block_time: int
    ) -> Optional[Dict[str, Any]]:
        """Extract detailed information about the wallet operation"""
        try:
            return {
                'accounts': [
                    account_keys[idx]
                    for idx in instruction.get('accounts', [])
                ],
                'data': instruction.get('data'),
                'program_id': instruction.get('programId'),
                'amount': self._extract_amount(instruction),
                'token_info': self._extract_token_info(instruction, account_keys),
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
            
    def _extract_token_info(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Extract token information from instruction"""
        try:
            # This is a placeholder - implement actual token info extraction
            return None
            
        except Exception as e:
            logger.error(f"Error extracting token info: {str(e)}")
            return None
            
    def _update_transfer_stats(self, operation_details: Dict[str, Any]) -> None:
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
                'amount': amount,
                'sender': accounts[0] if len(accounts) > 0 else None,
                'receiver': accounts[1] if len(accounts) > 1 else None,
                'block_time': operation_details.get('block_time'),
                'timestamp': operation_details.get('timestamp')
            })
            
        except Exception as e:
            logger.error(f"Error updating transfer stats: {str(e)}")
            
    def _update_token_stats(self, operation_details: Dict[str, Any]) -> None:
        """Update token statistics"""
        try:
            self.stats['token_stats']['total_token_txs'] += 1
            
            token_info = operation_details.get('token_info')
            if token_info:
                token_address = token_info.get('address')
                if token_address:
                    self.stats['token_stats']['unique_tokens'].add(token_address)
                    
                    # Update token volumes
                    amount = operation_details.get('amount', 0)
                    self.stats['token_stats']['token_volumes'][token_address] = \
                        self.stats['token_stats']['token_volumes'].get(token_address, 0) + amount
                        
                    # Update token holders
                    accounts = operation_details.get('accounts', [])
                    if accounts:
                        if token_address not in self.stats['token_stats']['token_holders']:
                            self.stats['token_stats']['token_holders'][token_address] = set()
                        self.stats['token_stats']['token_holders'][token_address].update(accounts)
                        
        except Exception as e:
            logger.error(f"Error updating token stats: {str(e)}")
            
    def get_results(self) -> Dict[str, Any]:
        """Get the accumulated results and statistics"""
        return {
            'wallet_operations': self.wallet_operations,
            'stats': {
                **self.stats,
                'transfer_stats': {
                    **self.stats['transfer_stats'],
                    'unique_senders': len(self.stats['transfer_stats']['unique_senders']),
                    'unique_receivers': len(self.stats['transfer_stats']['unique_receivers'])
                },
                'token_stats': {
                    **self.stats['token_stats'],
                    'unique_tokens': len(self.stats['token_stats']['unique_tokens']),
                    'token_holders': {
                        token: len(holders)
                        for token, holders in self.stats['token_stats']['token_holders'].items()
                    }
                }
            },
            'total_processed': len(self.processed_txs)
        }
        
    def reset(self) -> None:
        """Reset the extractor state"""
        self.wallet_operations = []
        self.stats = {
            'total_wallet_ops': 0,
            'operation_types': {
                'transfer': 0,
                'swap': 0,
                'stake': 0,
                'nft': 0,
                'token': 0,
                'other': 0
            },
            'wallet_stats': {},
            'transfer_stats': {
                'total_transfers': 0,
                'total_volume': 0,
                'unique_senders': set(),
                'unique_receivers': set(),
                'transfer_history': []
            },
            'token_stats': {
                'total_token_txs': 0,
                'unique_tokens': set(),
                'token_volumes': {},
                'token_holders': {}
            },
            'interaction_stats': {
                'programs_used': {},
                'contracts_called': {},
                'interaction_frequency': {}
            },
            'error_stats': {
                'total_errors': 0,
                'error_types': {}
            }
        }
        self.processed_txs = set()
