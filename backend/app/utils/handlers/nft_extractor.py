"""
NFT Extractor - Handles extraction and analysis of NFT-related activities
"""

from typing import Dict, Any, List, Optional, Set
import logging

# Constants
METAPLEX_TOKEN_METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
CANDY_MACHINE_CORE_ID = "CndyV3LdqHUfDLmE5naZjVN8rBZz4tqhdefbAnjHG3JR"
CANDY_MACHINE_ID = "cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ"
CANDY_GUARD_ID = "Guard1JwRhJkVH6XZhzoYxeBVQe872VH6QggF4BWmS9g"
MPL_TOKEN_AUTH_RULES = "auth9SigNpDKz4sJJ1DfCTuZrZNSAgh9sFD3rboVmgg"

logger = logging.getLogger(__name__)

class NFTExtractor:
    """Handles extraction and analysis of NFT-related activities"""
    
    def __init__(self):
        """Initialize the NFT extractor"""
        self.nft_operations: List[Dict] = []
        self.stats = {
            'total_nft_ops': 0,
            'operation_types': {
                'mint': 0,
                'transfer': 0,
                'burn': 0,
                'metadata_update': 0,
                'other': 0
            },
            'program_stats': {
                METAPLEX_TOKEN_METADATA_PROGRAM_ID: 0,
                CANDY_MACHINE_CORE_ID: 0,
                CANDY_MACHINE_ID: 0,
                CANDY_GUARD_ID: 0,
                MPL_TOKEN_AUTH_RULES: 0
            },
            'collections': {}
        }
        self.processed_nfts: Set[str] = set()
        
    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a single block for NFT activities"""
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
        """Process a single transaction for NFT activities"""
        try:
            if not transaction:
                return
                
            # Extract program IDs
            program_ids = set()
            for instruction in transaction.get('message', {}).get('instructions', []):
                program_id = instruction.get('programId')
                if program_id:
                    program_ids.add(program_id)
                    
            # Check for NFT operations
            if self._is_nft_transaction(program_ids):
                self._process_nft_operation(transaction, program_ids)
                
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            
    def _is_nft_transaction(self, program_ids: Set[str]) -> bool:
        """Check if transaction involves NFT operations"""
        nft_programs = {
            METAPLEX_TOKEN_METADATA_PROGRAM_ID,
            CANDY_MACHINE_CORE_ID,
            CANDY_MACHINE_ID,
            CANDY_GUARD_ID,
            MPL_TOKEN_AUTH_RULES
        }
        return bool(program_ids & nft_programs)
        
    def _process_nft_operation(self, transaction: Dict[str, Any], program_ids: Set[str]) -> None:
        """Process NFT-related operations in a transaction"""
        try:
            # Update program stats
            for program_id in program_ids:
                if program_id in self.stats['program_stats']:
                    self.stats['program_stats'][program_id] += 1
                    
            # Determine operation type
            operation_type = self._determine_operation_type(transaction)
            self.stats['operation_types'][operation_type] += 1
            
            # Extract NFT data
            nft_address = self._extract_nft_address(transaction)
            if nft_address and nft_address not in self.processed_nfts:
                self.processed_nfts.add(nft_address)
                
                # Extract collection info
                collection = self._extract_collection_info(transaction)
                if collection:
                    self.stats['collections'][collection] = \
                        self.stats['collections'].get(collection, 0) + 1
                    
                # Store operation data
                self.nft_operations.append({
                    'nft_address': nft_address,
                    'operation_type': operation_type,
                    'collection': collection,
                    'signature': transaction.get('signatures', [None])[0],
                    'slot': transaction.get('slot'),
                    'block_time': transaction.get('blockTime'),
                    'program_ids': list(program_ids)
                })
                
            self.stats['total_nft_ops'] += 1
            
        except Exception as e:
            logger.error(f"Error processing NFT operation: {str(e)}")
            
    def _determine_operation_type(self, transaction: Dict[str, Any]) -> str:
        """Determine the type of NFT operation"""
        try:
            # This is a simplified version - implement actual logic based on
            # instruction data and program calls
            if CANDY_MACHINE_CORE_ID in str(transaction) or \
               CANDY_MACHINE_ID in str(transaction):
                return "mint"
            elif "transfer" in str(transaction).lower():
                return "transfer"
            elif "burn" in str(transaction).lower():
                return "burn"
            elif METAPLEX_TOKEN_METADATA_PROGRAM_ID in str(transaction):
                return "metadata_update"
            else:
                return "other"
                
        except Exception as e:
            logger.error(f"Error determining operation type: {str(e)}")
            return "other"
            
    def _extract_nft_address(self, transaction: Dict[str, Any]) -> Optional[str]:
        """Extract NFT address from a transaction"""
        try:
            # Implementation depends on specific transaction structure
            # This is a placeholder - implement based on actual transaction structure
            accounts = transaction.get('message', {}).get('accountKeys', [])
            return accounts[0] if accounts else None
            
        except Exception as e:
            logger.error(f"Error extracting NFT address: {str(e)}")
            return None
            
    def _extract_collection_info(self, transaction: Dict[str, Any]) -> Optional[str]:
        """Extract collection information from a transaction"""
        try:
            # Implementation depends on specific transaction structure
            # This is a placeholder - implement based on actual transaction structure
            return None
            
        except Exception as e:
            logger.error(f"Error extracting collection info: {str(e)}")
            return None
            
    def get_results(self) -> Dict[str, Any]:
        """Get the accumulated results and statistics"""
        return {
            'nft_operations': self.nft_operations,
            'stats': self.stats,
            'total_processed': len(self.processed_nfts)
        }
        
    def reset(self) -> None:
        """Reset the extractor state"""
        self.nft_operations = []
        self.stats = {
            'total_nft_ops': 0,
            'operation_types': {
                'mint': 0,
                'transfer': 0,
                'burn': 0,
                'metadata_update': 0,
                'other': 0
            },
            'program_stats': {
                METAPLEX_TOKEN_METADATA_PROGRAM_ID: 0,
                CANDY_MACHINE_CORE_ID: 0,
                CANDY_MACHINE_ID: 0,
                CANDY_GUARD_ID: 0,
                MPL_TOKEN_AUTH_RULES: 0
            },
            'collections': {}
        }
        self.processed_nfts = set()
