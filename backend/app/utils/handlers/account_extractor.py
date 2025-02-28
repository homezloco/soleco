"""
Account Extractor - Handles extraction and analysis of Solana account activities
"""

from typing import Dict, Any, List, Optional, Set
import logging

logger = logging.getLogger(__name__)

class AccountExtractor:
    """Handles extraction and analysis of account data"""
    
    def __init__(self):
        """Initialize the account extractor"""
        self.accounts: List[Dict] = []
        self.stats = {
            'total_accounts': 0,
            'total_transactions': 0,
            'program_interactions': {},
            'account_types': {
                'system': 0,
                'token': 0,
                'program': 0,
                'other': 0
            },
            'balance_changes': {
                'total_sol_change': 0,
                'accounts_modified': 0
            }
        }
        self.processed_accounts: Set[str] = set()
        
    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a single block for account activities"""
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
        """Process a single transaction for account activities"""
        try:
            if not transaction:
                return
                
            # Update transaction count
            self.stats['total_transactions'] += 1
            
            # Process account keys
            accounts = transaction.get('message', {}).get('accountKeys', [])
            for account in accounts:
                if account not in self.processed_accounts:
                    self._process_account(account, transaction)
                    
            # Process program interactions
            for instruction in transaction.get('message', {}).get('instructions', []):
                program_id = instruction.get('programId')
                if program_id:
                    self.stats['program_interactions'][program_id] = \
                        self.stats['program_interactions'].get(program_id, 0) + 1
                        
            # Process balance changes
            pre_balances = transaction.get('meta', {}).get('preBalances', [])
            post_balances = transaction.get('meta', {}).get('postBalances', [])
            if pre_balances and post_balances:
                self._process_balance_changes(pre_balances, post_balances)
                
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            
    def _process_account(self, account: str, transaction: Dict[str, Any]) -> None:
        """Process a single account"""
        try:
            if account in self.processed_accounts:
                return
                
            self.processed_accounts.add(account)
            self.stats['total_accounts'] += 1
            
            # Determine account type
            account_type = self._determine_account_type(account, transaction)
            self.stats['account_types'][account_type] += 1
            
            # Store account data
            self.accounts.append({
                'address': account,
                'type': account_type,
                'first_seen_slot': transaction.get('slot'),
                'first_seen_signature': transaction.get('signatures', [None])[0]
            })
            
        except Exception as e:
            logger.error(f"Error processing account {account}: {str(e)}")
            
    def _determine_account_type(self, account: str, transaction: Dict[str, Any]) -> str:
        """Determine the type of an account"""
        try:
            # Check if it's a system account
            if account == "11111111111111111111111111111111":
                return "system"
                
            # Check if it's a token account
            for instruction in transaction.get('message', {}).get('instructions', []):
                if instruction.get('programId') == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                    return "token"
                    
            # Check if it's a program account
            if any(instruction.get('programId') == account 
                  for instruction in transaction.get('message', {}).get('instructions', [])):
                return "program"
                
            return "other"
            
        except Exception as e:
            logger.error(f"Error determining account type: {str(e)}")
            return "other"
            
    def _process_balance_changes(self, pre_balances: List[int], post_balances: List[int]) -> None:
        """Process balance changes in a transaction"""
        try:
            modified = False
            total_change = 0
            
            for pre, post in zip(pre_balances, post_balances):
                if pre != post:
                    modified = True
                    total_change += post - pre
                    
            if modified:
                self.stats['balance_changes']['accounts_modified'] += 1
                self.stats['balance_changes']['total_sol_change'] += total_change
                
        except Exception as e:
            logger.error(f"Error processing balance changes: {str(e)}")
            
    def get_results(self) -> Dict[str, Any]:
        """Get the accumulated results and statistics"""
        return {
            'accounts': self.accounts,
            'stats': self.stats,
            'total_processed': len(self.processed_accounts)
        }
        
    def reset(self) -> None:
        """Reset the extractor state"""
        self.accounts = []
        self.stats = {
            'total_accounts': 0,
            'total_transactions': 0,
            'program_interactions': {},
            'account_types': {
                'system': 0,
                'token': 0,
                'program': 0,
                'other': 0
            },
            'balance_changes': {
                'total_sol_change': 0,
                'accounts_modified': 0
            }
        }
        self.processed_accounts = set()
