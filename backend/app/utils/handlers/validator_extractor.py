"""
Validator Extractor - Handles extraction and analysis of validator-related activities on Solana
"""

from typing import Dict, Any, List, Optional, Set
import logging

logger = logging.getLogger(__name__)

class ValidatorExtractor:
    """Handles extraction and analysis of validator-related activities"""
    
    def __init__(self):
        """Initialize the validator extractor"""
        self.validator_operations: List[Dict] = []
        self.stats = {
            'total_validator_ops': 0,
            'operation_types': {
                'vote': 0,
                'stake': 0,
                'unstake': 0,
                'commission_change': 0,
                'other': 0
            },
            'validator_stats': {},
            'stake_stats': {
                'total_stake': 0,
                'active_stake': 0,
                'deactivating_stake': 0,
                'stake_accounts': set(),
                'stake_changes': []
            },
            'vote_stats': {
                'total_votes': 0,
                'vote_success_rate': 0.0,
                'vote_accounts': set(),
                'vote_history': []
            },
            'performance_stats': {
                'blocks_produced': {},
                'skip_rate': {},
                'average_stake': {},
                'commission': {}
            },
            'error_stats': {
                'total_errors': 0,
                'error_types': {}
            }
        }
        self.processed_txs: Set[str] = set()
        
    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a single block for validator activities"""
        if not block:
            logger.warning("Empty block data received")
            return
            
        try:
            # Track block production
            if 'leader' in block:
                leader = block.get('leader')
                self.stats['performance_stats']['blocks_produced'][leader] = \
                    self.stats['performance_stats']['blocks_produced'].get(leader, 0) + 1
                    
            transactions = block.get('transactions', [])
            for tx in transactions:
                self._process_transaction(tx)
                
            logger.debug(f"Processed block with {len(transactions)} transactions")
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            
    def _process_transaction(self, transaction: Dict[str, Any]) -> None:
        """Process a single transaction for validator activities"""
        try:
            if not transaction:
                return
                
            # Extract program invocations
            message = transaction.get('message', {})
            instructions = message.get('instructions', [])
            account_keys = message.get('accountKeys', [])
            
            # Process each instruction
            for instruction in instructions:
                program_id = instruction.get('programId')
                if self._is_validator_related_program(program_id):
                    self._process_validator_operation(
                        program_id,
                        instruction,
                        account_keys,
                        transaction
                    )
                    
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            
    def _is_validator_related_program(self, program_id: str) -> bool:
        """Check if program is related to validator operations"""
        validator_programs = {
            'Vote111111111111111111111111111111111111111',
            'Stake11111111111111111111111111111111111111',
            'StakeConfig11111111111111111111111111111111'
        }
        return program_id in validator_programs
        
    def _process_validator_operation(
        self,
        program_id: str,
        instruction: Dict[str, Any],
        account_keys: List[str],
        transaction: Dict[str, Any]
    ) -> None:
        """Process validator operation details"""
        try:
            # Update validator stats
            validator_id = self._extract_validator_id(instruction, account_keys)
            if validator_id:
                if validator_id not in self.stats['validator_stats']:
                    self.stats['validator_stats'][validator_id] = {
                        'total_operations': 0,
                        'operation_types': {
                            'vote': 0,
                            'stake': 0,
                            'unstake': 0,
                            'commission_change': 0,
                            'other': 0
                        },
                        'stake_accounts': set(),
                        'vote_accounts': set(),
                        'performance': {
                            'blocks_produced': 0,
                            'skip_rate': 0.0,
                            'average_stake': 0.0,
                            'commission': 0.0
                        }
                    }
                    
            # Determine operation type
            operation_type = self._determine_operation_type(instruction)
            self.stats['operation_types'][operation_type] += 1
            
            if validator_id:
                self.stats['validator_stats'][validator_id]['operation_types'][operation_type] += 1
                self.stats['validator_stats'][validator_id]['total_operations'] += 1
                
            # Extract transaction signature
            signature = transaction.get('signatures', [None])[0]
            if signature and signature not in self.processed_txs:
                self.processed_txs.add(signature)
                
                # Extract operation details
                operation_details = self._extract_operation_details(
                    instruction,
                    account_keys,
                    program_id,
                    validator_id,
                    transaction
                )
                
                if operation_details:
                    # Update stake stats
                    if operation_type in ['stake', 'unstake']:
                        stake_account = operation_details.get('stake_account')
                        if stake_account:
                            self.stats['stake_stats']['stake_accounts'].add(stake_account)
                            if validator_id:
                                self.stats['validator_stats'][validator_id]['stake_accounts'].add(
                                    stake_account
                                )
                                
                        stake_amount = operation_details.get('stake_amount', 0)
                        if operation_type == 'stake':
                            self.stats['stake_stats']['total_stake'] += stake_amount
                            self.stats['stake_stats']['active_stake'] += stake_amount
                        else:  # unstake
                            self.stats['stake_stats']['active_stake'] -= stake_amount
                            self.stats['stake_stats']['deactivating_stake'] += stake_amount
                            
                        self.stats['stake_stats']['stake_changes'].append({
                            'validator': validator_id,
                            'operation_type': operation_type,
                            'amount': stake_amount,
                            'slot': transaction.get('slot'),
                            'block_time': transaction.get('blockTime')
                        })
                        
                    # Update vote stats
                    elif operation_type == 'vote':
                        vote_account = operation_details.get('vote_account')
                        if vote_account:
                            self.stats['vote_stats']['vote_accounts'].add(vote_account)
                            if validator_id:
                                self.stats['validator_stats'][validator_id]['vote_accounts'].add(
                                    vote_account
                                )
                                
                        self.stats['vote_stats']['total_votes'] += 1
                        success = operation_details.get('success', False)
                        if success:
                            self.stats['vote_stats']['vote_success_rate'] = (
                                self.stats['vote_stats']['vote_success_rate'] *
                                (self.stats['vote_stats']['total_votes'] - 1) +
                                1
                            ) / self.stats['vote_stats']['total_votes']
                            
                        self.stats['vote_stats']['vote_history'].append({
                            'validator': validator_id,
                            'success': success,
                            'slot': transaction.get('slot'),
                            'block_time': transaction.get('blockTime')
                        })
                        
                    # Store operation data
                    self.validator_operations.append({
                        'signature': signature,
                        'validator': validator_id,
                        'operation_type': operation_type,
                        'operation_details': operation_details,
                        'slot': transaction.get('slot'),
                        'block_time': transaction.get('blockTime')
                    })
                    
            self.stats['total_validator_ops'] += 1
            
        except Exception as e:
            logger.error(f"Error processing validator operation: {str(e)}")
            self.stats['error_stats']['total_errors'] += 1
            error_type = type(e).__name__
            self.stats['error_stats']['error_types'][error_type] = \
                self.stats['error_stats']['error_types'].get(error_type, 0) + 1
                
    def _determine_operation_type(self, instruction: Dict[str, Any]) -> str:
        """Determine the type of validator operation"""
        try:
            # This is a simplified version - implement actual logic based on
            # instruction data and program calls
            data = str(instruction.get('data', '')).lower()
            
            if 'vote' in data:
                return 'vote'
            elif 'delegate' in data:
                return 'stake'
            elif 'deactivate' in data:
                return 'unstake'
            elif 'commission' in data:
                return 'commission_change'
            else:
                return 'other'
                
        except Exception as e:
            logger.error(f"Error determining operation type: {str(e)}")
            return 'other'
            
    def _extract_validator_id(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str]
    ) -> Optional[str]:
        """Extract validator ID from instruction"""
        try:
            # This is a placeholder - implement actual validator ID extraction
            # based on instruction data and account keys
            return account_keys[instruction.get('accounts', [0])[0]]
            
        except Exception as e:
            logger.error(f"Error extracting validator ID: {str(e)}")
            return None
            
    def _extract_operation_details(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str],
        program_id: str,
        validator_id: Optional[str],
        transaction: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract detailed information about the validator operation"""
        try:
            return {
                'accounts': [
                    account_keys[idx]
                    for idx in instruction.get('accounts', [])
                ],
                'data': instruction.get('data'),
                'program_id': program_id,
                'validator_id': validator_id,
                'stake_account': self._extract_stake_account(instruction, account_keys),
                'vote_account': self._extract_vote_account(instruction, account_keys),
                'stake_amount': self._extract_stake_amount(instruction),
                'success': transaction.get('meta', {}).get('status', {}).get('Ok') is not None,
                'error': transaction.get('meta', {}).get('error')
            }
            
        except Exception as e:
            logger.error(f"Error extracting operation details: {str(e)}")
            return None
            
    def _extract_stake_account(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str]
    ) -> Optional[str]:
        """Extract stake account from instruction"""
        try:
            # This is a placeholder - implement actual stake account extraction
            accounts = instruction.get('accounts', [])
            if len(accounts) > 1:
                return account_keys[accounts[1]]
            return None
            
        except Exception as e:
            logger.error(f"Error extracting stake account: {str(e)}")
            return None
            
    def _extract_vote_account(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str]
    ) -> Optional[str]:
        """Extract vote account from instruction"""
        try:
            # This is a placeholder - implement actual vote account extraction
            accounts = instruction.get('accounts', [])
            if len(accounts) > 1:
                return account_keys[accounts[1]]
            return None
            
        except Exception as e:
            logger.error(f"Error extracting vote account: {str(e)}")
            return None
            
    def _extract_stake_amount(self, instruction: Dict[str, Any]) -> int:
        """Extract stake amount from instruction"""
        try:
            # This is a placeholder - implement actual stake amount extraction
            # based on instruction data
            return 0
            
        except Exception as e:
            logger.error(f"Error extracting stake amount: {str(e)}")
            return 0
            
    def get_results(self) -> Dict[str, Any]:
        """Get the accumulated results and statistics"""
        return {
            'validator_operations': self.validator_operations,
            'stats': {
                **self.stats,
                'stake_stats': {
                    **self.stats['stake_stats'],
                    'stake_accounts': len(self.stats['stake_stats']['stake_accounts'])
                },
                'vote_stats': {
                    **self.stats['vote_stats'],
                    'vote_accounts': len(self.stats['vote_stats']['vote_accounts'])
                }
            },
            'total_processed': len(self.processed_txs)
        }
        
    def reset(self) -> None:
        """Reset the extractor state"""
        self.validator_operations = []
        self.stats = {
            'total_validator_ops': 0,
            'operation_types': {
                'vote': 0,
                'stake': 0,
                'unstake': 0,
                'commission_change': 0,
                'other': 0
            },
            'validator_stats': {},
            'stake_stats': {
                'total_stake': 0,
                'active_stake': 0,
                'deactivating_stake': 0,
                'stake_accounts': set(),
                'stake_changes': []
            },
            'vote_stats': {
                'total_votes': 0,
                'vote_success_rate': 0.0,
                'vote_accounts': set(),
                'vote_history': []
            },
            'performance_stats': {
                'blocks_produced': {},
                'skip_rate': {},
                'average_stake': {},
                'commission': {}
            },
            'error_stats': {
                'total_errors': 0,
                'error_types': {}
            }
        }
        self.processed_txs = set()
