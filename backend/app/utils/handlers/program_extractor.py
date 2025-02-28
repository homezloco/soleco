"""
Program Extractor - Handles extraction and analysis of program-related activities on Solana
"""

from typing import Dict, Any, List, Optional, Set
import logging

logger = logging.getLogger(__name__)

class ProgramExtractor:
    """Handles extraction and analysis of program-related activities"""
    
    def __init__(self):
        """Initialize the program extractor"""
        self.program_operations: List[Dict] = []
        self.stats = {
            'total_program_ops': 0,
            'operation_types': {
                'invoke': 0,
                'upgrade': 0,
                'close': 0,
                'initialize': 0,
                'other': 0
            },
            'program_stats': {},
            'account_stats': {
                'total_accounts': 0,
                'unique_accounts': set(),
                'account_types': {}
            },
            'error_stats': {
                'total_errors': 0,
                'error_types': {}
            },
            'performance_stats': {
                'compute_units': {
                    'total': 0,
                    'average': 0,
                    'max': 0
                },
                'execution_times': {
                    'total': 0,
                    'average': 0,
                    'max': 0
                }
            }
        }
        self.processed_txs: Set[str] = set()
        
    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a single block for program activities"""
        if not block:
            logger.warning("Empty block data received")
            return
            
        try:
            transactions = block.get('transactions', [])
            for tx in transactions:
                self._process_transaction(tx)
                
            logger.debug(f"Processed block with {len(transactions)} transactions")
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            
    def _process_transaction(self, transaction: Dict[str, Any]) -> None:
        """Process a single transaction for program activities"""
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
                if program_id:
                    self._process_program_operation(
                        program_id,
                        instruction,
                        account_keys,
                        transaction
                    )
                    
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            
    def _process_program_operation(
        self,
        program_id: str,
        instruction: Dict[str, Any],
        account_keys: List[str],
        transaction: Dict[str, Any]
    ) -> None:
        """Process program operation details"""
        try:
            # Update program stats
            if program_id not in self.stats['program_stats']:
                self.stats['program_stats'][program_id] = {
                    'total_invocations': 0,
                    'unique_callers': set(),
                    'operation_types': {
                        'invoke': 0,
                        'upgrade': 0,
                        'close': 0,
                        'initialize': 0,
                        'other': 0
                    },
                    'error_count': 0
                }
                
            self.stats['program_stats'][program_id]['total_invocations'] += 1
            
            # Determine operation type
            operation_type = self._determine_operation_type(instruction)
            self.stats['operation_types'][operation_type] += 1
            self.stats['program_stats'][program_id]['operation_types'][operation_type] += 1
            
            # Extract transaction signature
            signature = transaction.get('signatures', [None])[0]
            if signature and signature not in self.processed_txs:
                self.processed_txs.add(signature)
                
                # Extract operation details
                operation_details = self._extract_operation_details(
                    instruction,
                    account_keys,
                    program_id,
                    transaction
                )
                
                if operation_details:
                    # Update account stats
                    for account in operation_details.get('accounts', []):
                        self.stats['account_stats']['unique_accounts'].add(account)
                        
                    account_type = operation_details.get('account_type')
                    if account_type:
                        self.stats['account_stats']['account_types'][account_type] = \
                            self.stats['account_stats']['account_types'].get(account_type, 0) + 1
                            
                    # Update performance stats if available
                    compute_units = operation_details.get('compute_units', 0)
                    if compute_units:
                        self.stats['performance_stats']['compute_units']['total'] += compute_units
                        self.stats['performance_stats']['compute_units']['max'] = \
                            max(self.stats['performance_stats']['compute_units']['max'], compute_units)
                            
                    # Store operation data
                    self.program_operations.append({
                        'signature': signature,
                        'program_id': program_id,
                        'operation_type': operation_type,
                        'operation_details': operation_details,
                        'slot': transaction.get('slot'),
                        'block_time': transaction.get('blockTime')
                    })
                    
            self.stats['total_program_ops'] += 1
            
            # Update averages
            if self.stats['total_program_ops'] > 0:
                self.stats['performance_stats']['compute_units']['average'] = \
                    self.stats['performance_stats']['compute_units']['total'] / \
                    self.stats['total_program_ops']
                    
        except Exception as e:
            logger.error(f"Error processing program operation: {str(e)}")
            self.stats['error_stats']['total_errors'] += 1
            error_type = type(e).__name__
            self.stats['error_stats']['error_types'][error_type] = \
                self.stats['error_stats']['error_types'].get(error_type, 0) + 1
                
    def _determine_operation_type(self, instruction: Dict[str, Any]) -> str:
        """Determine the type of program operation"""
        try:
            # This is a simplified version - implement actual logic based on
            # instruction data and program calls
            data = str(instruction.get('data', '')).lower()
            
            if 'invoke' in data:
                return 'invoke'
            elif 'upgrade' in data:
                return 'upgrade'
            elif 'close' in data:
                return 'close'
            elif 'initialize' in data or 'init' in data:
                return 'initialize'
            else:
                return 'other'
                
        except Exception as e:
            logger.error(f"Error determining operation type: {str(e)}")
            return 'other'
            
    def _extract_operation_details(
        self,
        instruction: Dict[str, Any],
        account_keys: List[str],
        program_id: str,
        transaction: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract detailed information about the program operation"""
        try:
            return {
                'accounts': [
                    account_keys[idx]
                    for idx in instruction.get('accounts', [])
                ],
                'data': instruction.get('data'),
                'program_id': program_id,
                'account_type': self._determine_account_type(instruction),
                'compute_units': transaction.get('meta', {}).get('computeUnitsConsumed', 0),
                'status': transaction.get('meta', {}).get('status'),
                'error': transaction.get('meta', {}).get('error')
            }
            
        except Exception as e:
            logger.error(f"Error extracting operation details: {str(e)}")
            return None
            
    def _determine_account_type(self, instruction: Dict[str, Any]) -> Optional[str]:
        """Determine the type of account being operated on"""
        try:
            # This is a placeholder - implement actual account type detection
            # based on instruction data and program context
            data = str(instruction.get('data', '')).lower()
            
            if 'token' in data:
                return 'token'
            elif 'mint' in data:
                return 'mint'
            elif 'vault' in data:
                return 'vault'
            elif 'pool' in data:
                return 'pool'
            else:
                return 'other'
                
        except Exception as e:
            logger.error(f"Error determining account type: {str(e)}")
            return None
            
    def get_results(self) -> Dict[str, Any]:
        """Get the accumulated results and statistics"""
        return {
            'program_operations': self.program_operations,
            'stats': {
                **self.stats,
                'account_stats': {
                    **self.stats['account_stats'],
                    'unique_accounts': len(self.stats['account_stats']['unique_accounts'])
                }
            },
            'total_processed': len(self.processed_txs)
        }
        
    def reset(self) -> None:
        """Reset the extractor state"""
        self.program_operations = []
        self.stats = {
            'total_program_ops': 0,
            'operation_types': {
                'invoke': 0,
                'upgrade': 0,
                'close': 0,
                'initialize': 0,
                'other': 0
            },
            'program_stats': {},
            'account_stats': {
                'total_accounts': 0,
                'unique_accounts': set(),
                'account_types': {}
            },
            'error_stats': {
                'total_errors': 0,
                'error_types': {}
            },
            'performance_stats': {
                'compute_units': {
                    'total': 0,
                    'average': 0,
                    'max': 0
                },
                'execution_times': {
                    'total': 0,
                    'average': 0,
                    'max': 0
                }
            }
        }
        self.processed_txs = set()
