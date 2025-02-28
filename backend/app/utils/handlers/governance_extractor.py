"""
Governance Extractor - Handles extraction and analysis of governance-related activities on Solana
"""

from typing import Dict, Any, List, Optional, Set
import logging

# Constants for governance programs
SPL_GOVERNANCE = "GovER5Lthms3bLBqWub97yVrMmEogzX7xNjdXpPPCVZw"
REALM_GOVERNANCE = "GovHgfDPyQ1GwCkDs8KS7kUFVHmzgkrHmHXbKJqHWfJt"
PROGRAM_GOVERNANCE = "GovProg1111111111111111111111111111111111"
STAKE_GOVERNANCE = "StakeGov11111111111111111111111111111111"

logger = logging.getLogger(__name__)

class GovernanceExtractor:
    """Handles extraction and analysis of governance-related activities"""
    
    def __init__(self):
        """Initialize the governance extractor"""
        self.governance_operations: List[Dict] = []
        self.stats = {
            'total_governance_ops': 0,
            'operation_types': {
                'proposal_create': 0,
                'vote_cast': 0,
                'comment': 0,
                'execution': 0,
                'config_change': 0,
                'other': 0
            },
            'program_stats': {
                SPL_GOVERNANCE: 0,
                REALM_GOVERNANCE: 0,
                PROGRAM_GOVERNANCE: 0,
                STAKE_GOVERNANCE: 0
            },
            'voter_stats': {
                'unique_voters': set(),
                'vote_distribution': {
                    'yes': 0,
                    'no': 0,
                    'abstain': 0
                }
            },
            'proposal_stats': {
                'total': 0,
                'active': 0,
                'executed': 0,
                'defeated': 0,
                'by_category': {}
            }
        }
        self.processed_txs: Set[str] = set()
        
    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a single block for governance activities"""
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
        """Process a single transaction for governance activities"""
        try:
            if not transaction:
                return
                
            # Extract program IDs
            program_ids = set()
            for instruction in transaction.get('message', {}).get('instructions', []):
                program_id = instruction.get('programId')
                if program_id:
                    program_ids.add(program_id)
                    
            # Check for governance operations
            if self._is_governance_transaction(program_ids):
                self._process_governance_operation(transaction, program_ids)
                
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            
    def _is_governance_transaction(self, program_ids: Set[str]) -> bool:
        """Check if transaction involves governance operations"""
        governance_programs = {
            SPL_GOVERNANCE,
            REALM_GOVERNANCE,
            PROGRAM_GOVERNANCE,
            STAKE_GOVERNANCE
        }
        return bool(program_ids & governance_programs)
        
    def _process_governance_operation(self, transaction: Dict[str, Any], program_ids: Set[str]) -> None:
        """Process governance-related operations in a transaction"""
        try:
            # Update program stats
            for program_id in program_ids:
                if program_id in self.stats['program_stats']:
                    self.stats['program_stats'][program_id] += 1
                    
            # Determine operation type and details
            operation_type = self._determine_operation_type(transaction)
            self.stats['operation_types'][operation_type] += 1
            
            # Extract transaction signature
            signature = transaction.get('signatures', [None])[0]
            if signature and signature not in self.processed_txs:
                self.processed_txs.add(signature)
                
                # Extract governance details
                governance_details = self._extract_governance_details(transaction)
                if governance_details:
                    # Update voter stats if applicable
                    if operation_type == 'vote_cast':
                        self.stats['voter_stats']['unique_voters'].add(
                            governance_details.get('voter')
                        )
                        vote_type = governance_details.get('vote_type', 'abstain')
                        self.stats['voter_stats']['vote_distribution'][vote_type] += 1
                        
                    # Update proposal stats if applicable
                    if operation_type == 'proposal_create':
                        self.stats['proposal_stats']['total'] += 1
                        self.stats['proposal_stats']['active'] += 1
                        
                        category = governance_details.get('category', 'other')
                        self.stats['proposal_stats']['by_category'][category] = \
                            self.stats['proposal_stats']['by_category'].get(category, 0) + 1
                            
                    elif operation_type == 'execution':
                        self.stats['proposal_stats']['executed'] += 1
                        self.stats['proposal_stats']['active'] -= 1
                        
                    # Store operation data
                    self.governance_operations.append({
                        'signature': signature,
                        'operation_type': operation_type,
                        'governance_details': governance_details,
                        'slot': transaction.get('slot'),
                        'block_time': transaction.get('blockTime'),
                        'program_ids': list(program_ids)
                    })
                    
            self.stats['total_governance_ops'] += 1
            
        except Exception as e:
            logger.error(f"Error processing governance operation: {str(e)}")
            
    def _determine_operation_type(self, transaction: Dict[str, Any]) -> str:
        """Determine the type of governance operation"""
        try:
            # This is a simplified version - implement actual logic based on
            # instruction data and program calls
            tx_str = str(transaction).lower()
            
            if "create_proposal" in tx_str or "proposal_create" in tx_str:
                return "proposal_create"
            elif "cast_vote" in tx_str or "vote_cast" in tx_str:
                return "vote_cast"
            elif "comment" in tx_str:
                return "comment"
            elif "execute" in tx_str:
                return "execution"
            elif "config" in tx_str:
                return "config_change"
            else:
                return "other"
                
        except Exception as e:
            logger.error(f"Error determining operation type: {str(e)}")
            return "other"
            
    def _extract_governance_details(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract governance details from a transaction"""
        try:
            # This is a placeholder - implement actual governance detail extraction
            # based on transaction data and instruction parsing
            return {
                'voter': transaction.get('signatures', [None])[0],
                'vote_type': 'abstain',  # Implement actual vote type detection
                'category': 'other',  # Implement proposal category detection
                'proposal_id': None,  # Implement proposal ID extraction
                'vote_weight': 0,  # Implement vote weight calculation
                'execution_status': None  # Implement execution status tracking
            }
            
        except Exception as e:
            logger.error(f"Error extracting governance details: {str(e)}")
            return None
            
    def get_results(self) -> Dict[str, Any]:
        """Get the accumulated results and statistics"""
        return {
            'governance_operations': self.governance_operations,
            'stats': {
                **self.stats,
                'voter_stats': {
                    **self.stats['voter_stats'],
                    'unique_voters': len(self.stats['voter_stats']['unique_voters'])
                }
            },
            'total_processed': len(self.processed_txs)
        }
        
    def reset(self) -> None:
        """Reset the extractor state"""
        self.governance_operations = []
        self.stats = {
            'total_governance_ops': 0,
            'operation_types': {
                'proposal_create': 0,
                'vote_cast': 0,
                'comment': 0,
                'execution': 0,
                'config_change': 0,
                'other': 0
            },
            'program_stats': {
                SPL_GOVERNANCE: 0,
                REALM_GOVERNANCE: 0,
                PROGRAM_GOVERNANCE: 0,
                STAKE_GOVERNANCE: 0
            },
            'voter_stats': {
                'unique_voters': set(),
                'vote_distribution': {
                    'yes': 0,
                    'no': 0,
                    'abstain': 0
                }
            },
            'proposal_stats': {
                'total': 0,
                'active': 0,
                'executed': 0,
                'defeated': 0,
                'by_category': {}
            }
        }
        self.processed_txs = set()
