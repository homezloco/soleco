"""
DeFi Extractor - Handles extraction and analysis of DeFi-related activities on Solana
"""

from typing import Dict, Any, List, Optional, Set
import logging

# Constants for common DeFi programs
RAYDIUM_AMM_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
ORCA_SWAP_V2 = "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP"
JUPITER_V3 = "JUP3c2Uh3WA4Ng34tw6kPd2G4C5BB21Xo36Je1s32Ph"
MARINADE_FINANCE = "MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD"
SOLEND = "So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo"
SERUM_V3 = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"

logger = logging.getLogger(__name__)

class DefiExtractor:
    """Handles extraction and analysis of DeFi-related activities"""
    
    def __init__(self):
        """Initialize the DeFi extractor"""
        self.defi_operations: List[Dict] = []
        self.stats = {
            'total_defi_ops': 0,
            'operation_types': {
                'swap': 0,
                'provide_liquidity': 0,
                'remove_liquidity': 0,
                'stake': 0,
                'unstake': 0,
                'borrow': 0,
                'repay': 0,
                'other': 0
            },
            'protocol_stats': {
                RAYDIUM_AMM_V4: 0,
                ORCA_SWAP_V2: 0,
                JUPITER_V3: 0,
                MARINADE_FINANCE: 0,
                SOLEND: 0,
                SERUM_V3: 0
            },
            'volume_stats': {
                'total_volume_usd': 0,
                'by_protocol': {},
                'by_operation': {}
            }
        }
        self.processed_txs: Set[str] = set()
        
    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a single block for DeFi activities"""
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
        """Process a single transaction for DeFi activities"""
        try:
            if not transaction:
                return
                
            # Extract program IDs
            program_ids = set()
            for instruction in transaction.get('message', {}).get('instructions', []):
                program_id = instruction.get('programId')
                if program_id:
                    program_ids.add(program_id)
                    
            # Check for DeFi operations
            if self._is_defi_transaction(program_ids):
                self._process_defi_operation(transaction, program_ids)
                
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            
    def _is_defi_transaction(self, program_ids: Set[str]) -> bool:
        """Check if transaction involves DeFi operations"""
        defi_programs = {
            RAYDIUM_AMM_V4,
            ORCA_SWAP_V2,
            JUPITER_V3,
            MARINADE_FINANCE,
            SOLEND,
            SERUM_V3
        }
        return bool(program_ids & defi_programs)
        
    def _process_defi_operation(self, transaction: Dict[str, Any], program_ids: Set[str]) -> None:
        """Process DeFi-related operations in a transaction"""
        try:
            # Update protocol stats
            for program_id in program_ids:
                if program_id in self.stats['protocol_stats']:
                    self.stats['protocol_stats'][program_id] += 1
                    
            # Determine operation type and protocol
            operation_type = self._determine_operation_type(transaction)
            protocol = self._determine_protocol(program_ids)
            
            # Update operation type stats
            self.stats['operation_types'][operation_type] += 1
            
            # Extract transaction signature
            signature = transaction.get('signatures', [None])[0]
            if signature and signature not in self.processed_txs:
                self.processed_txs.add(signature)
                
                # Extract volume information
                volume_info = self._extract_volume_info(transaction)
                if volume_info:
                    # Update volume stats
                    self.stats['volume_stats']['total_volume_usd'] += volume_info['usd_amount']
                    
                    # Update protocol volume
                    if protocol:
                        self.stats['volume_stats']['by_protocol'][protocol] = \
                            self.stats['volume_stats']['by_protocol'].get(protocol, 0) + \
                            volume_info['usd_amount']
                            
                    # Update operation type volume
                    self.stats['volume_stats']['by_operation'][operation_type] = \
                        self.stats['volume_stats']['by_operation'].get(operation_type, 0) + \
                        volume_info['usd_amount']
                        
                # Store operation data
                self.defi_operations.append({
                    'signature': signature,
                    'operation_type': operation_type,
                    'protocol': protocol,
                    'volume_info': volume_info,
                    'slot': transaction.get('slot'),
                    'block_time': transaction.get('blockTime'),
                    'program_ids': list(program_ids)
                })
                
            self.stats['total_defi_ops'] += 1
            
        except Exception as e:
            logger.error(f"Error processing DeFi operation: {str(e)}")
            
    def _determine_operation_type(self, transaction: Dict[str, Any]) -> str:
        """Determine the type of DeFi operation"""
        try:
            # This is a simplified version - implement actual logic based on
            # instruction data and program calls
            tx_str = str(transaction).lower()
            
            if "swap" in tx_str:
                return "swap"
            elif "provide" in tx_str or "add_liquidity" in tx_str:
                return "provide_liquidity"
            elif "remove" in tx_str or "withdraw_liquidity" in tx_str:
                return "remove_liquidity"
            elif "stake" in tx_str and "unstake" not in tx_str:
                return "stake"
            elif "unstake" in tx_str:
                return "unstake"
            elif "borrow" in tx_str:
                return "borrow"
            elif "repay" in tx_str:
                return "repay"
            else:
                return "other"
                
        except Exception as e:
            logger.error(f"Error determining operation type: {str(e)}")
            return "other"
            
    def _determine_protocol(self, program_ids: Set[str]) -> Optional[str]:
        """Determine the DeFi protocol used"""
        protocol_map = {
            RAYDIUM_AMM_V4: "Raydium",
            ORCA_SWAP_V2: "Orca",
            JUPITER_V3: "Jupiter",
            MARINADE_FINANCE: "Marinade",
            SOLEND: "Solend",
            SERUM_V3: "Serum"
        }
        
        for program_id in program_ids:
            if program_id in protocol_map:
                return protocol_map[program_id]
        return None
        
    def _extract_volume_info(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract volume information from a transaction"""
        try:
            # This is a placeholder - implement actual volume extraction logic
            # based on transaction data and token prices
            return {
                'usd_amount': 0,  # Implement actual USD amount calculation
                'token_amounts': {}  # Implement token amount tracking
            }
            
        except Exception as e:
            logger.error(f"Error extracting volume info: {str(e)}")
            return None
            
    def get_results(self) -> Dict[str, Any]:
        """Get the accumulated results and statistics"""
        return {
            'defi_operations': self.defi_operations,
            'stats': self.stats,
            'total_processed': len(self.processed_txs)
        }
        
    def reset(self) -> None:
        """Reset the extractor state"""
        self.defi_operations = []
        self.stats = {
            'total_defi_ops': 0,
            'operation_types': {
                'swap': 0,
                'provide_liquidity': 0,
                'remove_liquidity': 0,
                'stake': 0,
                'unstake': 0,
                'borrow': 0,
                'repay': 0,
                'other': 0
            },
            'protocol_stats': {
                RAYDIUM_AMM_V4: 0,
                ORCA_SWAP_V2: 0,
                JUPITER_V3: 0,
                MARINADE_FINANCE: 0,
                SOLEND: 0,
                SERUM_V3: 0
            },
            'volume_stats': {
                'total_volume_usd': 0,
                'by_protocol': {},
                'by_operation': {}
            }
        }
        self.processed_txs = set()
