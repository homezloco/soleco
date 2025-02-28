"""
Block Extractor - Handles extraction and analysis of Solana block data
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class BlockExtractor:
    """Handles extraction and analysis of block data"""
    
    def __init__(self):
        """Initialize the block extractor"""
        self.blocks: List[Dict] = []
        self.stats: Dict[str, Any] = {
            'total_transactions': 0,
            'avg_transactions': 0,
            'block_times': [],
            'slots': []
        }
        
    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a single block and update statistics"""
        if not block:
            logger.warning("Empty block data received")
            return
            
        try:
            # Store block
            self.blocks.append(block)
            
            # Update statistics
            transactions = block.get('transactions', [])
            self.stats['total_transactions'] += len(transactions)
            
            if block.get('blockTime'):
                self.stats['block_times'].append(block['blockTime'])
                
            if block.get('slot'):
                self.stats['slots'].append(block['slot'])
                
            # Update average
            if self.blocks:
                self.stats['avg_transactions'] = self.stats['total_transactions'] / len(self.blocks)
                
            logger.debug(f"Processed block {block.get('slot')} with {len(transactions)} transactions")
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            
    def get_results(self) -> Dict[str, Any]:
        """Get the accumulated results and statistics"""
        return {
            'blocks': self.blocks,
            'stats': self.stats,
            'blocks_processed': len(self.blocks)
        }
        
    def reset(self) -> None:
        """Reset the extractor state"""
        self.blocks = []
        self.stats = {
            'total_transactions': 0,
            'avg_transactions': 0,
            'block_times': [],
            'slots': []
        }
