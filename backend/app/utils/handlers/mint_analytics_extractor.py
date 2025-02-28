"""
Mint Analytics Extractor - Handles extraction and analysis of mint-related activities
"""

from typing import Dict, Any, List, Optional, Set
import logging

# Constants
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"  # Standard SPL Token
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"  # Token 2022
METAPLEX_TOKEN_METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"  # Metaplex Token Metadata

logger = logging.getLogger(__name__)

class MintAnalyticsExtractor:
    """Handles extraction and analysis of mint-related activities"""
    
    def __init__(self):
        """Initialize the mint analytics extractor"""
        self.mint_operations: List[Dict] = []
        self.token_operations: List[Dict] = []
        self.stats = {
            'total_mints': 0,
            'total_token_ops': 0,
            'program_stats': {
                TOKEN_PROGRAM_ID: 0,
                TOKEN_2022_PROGRAM_ID: 0
            },
            'metadata_stats': {
                'with_metadata': 0,
                'without_metadata': 0
            }
        }
        self.processed_mints: Set[str] = set()
        
    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a single block for mint-related activities"""
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
        """Process a single transaction for mint-related activities"""
        try:
            if not transaction:
                return
                
            # Extract program IDs
            program_ids = set()
            for instruction in transaction.get('message', {}).get('instructions', []):
                program_id = instruction.get('programId')
                if program_id:
                    program_ids.add(program_id)
                    
            # Check for token operations
            if TOKEN_PROGRAM_ID in program_ids or TOKEN_2022_PROGRAM_ID in program_ids:
                self._process_token_operation(transaction, program_ids)
                
            # Check for metadata
            if METAPLEX_TOKEN_METADATA_PROGRAM_ID in program_ids:
                self._process_metadata_operation(transaction)
                
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            
    def _process_token_operation(self, transaction: Dict[str, Any], program_ids: Set[str]) -> None:
        """Process token-related operations in a transaction"""
        try:
            # Update program stats
            if TOKEN_PROGRAM_ID in program_ids:
                self.stats['program_stats'][TOKEN_PROGRAM_ID] += 1
            if TOKEN_2022_PROGRAM_ID in program_ids:
                self.stats['program_stats'][TOKEN_2022_PROGRAM_ID] += 1
                
            # Extract mint address if present
            mint_address = self._extract_mint_address(transaction)
            if mint_address and mint_address not in self.processed_mints:
                self.processed_mints.add(mint_address)
                self.stats['total_mints'] += 1
                self.mint_operations.append({
                    'mint_address': mint_address,
                    'signature': transaction.get('signatures', [None])[0],
                    'slot': transaction.get('slot'),
                    'block_time': transaction.get('blockTime'),
                    'program_id': TOKEN_2022_PROGRAM_ID if TOKEN_2022_PROGRAM_ID in program_ids else TOKEN_PROGRAM_ID
                })
                
            self.stats['total_token_ops'] += 1
            self.token_operations.append({
                'signature': transaction.get('signatures', [None])[0],
                'slot': transaction.get('slot'),
                'block_time': transaction.get('blockTime'),
                'program_ids': list(program_ids)
            })
            
        except Exception as e:
            logger.error(f"Error processing token operation: {str(e)}")
            
    def _process_metadata_operation(self, transaction: Dict[str, Any]) -> None:
        """Process metadata-related operations in a transaction"""
        try:
            mint_address = self._extract_mint_address(transaction)
            if mint_address:
                self.stats['metadata_stats']['with_metadata'] += 1
            else:
                self.stats['metadata_stats']['without_metadata'] += 1
                
        except Exception as e:
            logger.error(f"Error processing metadata operation: {str(e)}")
            
    def _extract_mint_address(self, transaction: Dict[str, Any]) -> Optional[str]:
        """Extract mint address from a transaction if present"""
        try:
            # Implementation depends on specific transaction structure
            # This is a placeholder - implement based on actual transaction structure
            accounts = transaction.get('message', {}).get('accountKeys', [])
            return accounts[0] if accounts else None
            
        except Exception as e:
            logger.error(f"Error extracting mint address: {str(e)}")
            return None
            
    def get_results(self) -> Dict[str, Any]:
        """Get the accumulated results and statistics"""
        return {
            'mint_operations': self.mint_operations,
            'token_operations': self.token_operations,
            'stats': self.stats,
            'total_processed': len(self.processed_mints)
        }
        
    def reset(self) -> None:
        """Reset the extractor state"""
        self.mint_operations = []
        self.token_operations = []
        self.stats = {
            'total_mints': 0,
            'total_token_ops': 0,
            'program_stats': {
                TOKEN_PROGRAM_ID: 0,
                TOKEN_2022_PROGRAM_ID: 0
            },
            'metadata_stats': {
                'with_metadata': 0,
                'without_metadata': 0
            }
        }
        self.processed_mints = set()
