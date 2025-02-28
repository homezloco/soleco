"""
Handler for detecting and analyzing pump tokens.
"""

from typing import Set, List, Dict, Any
import logging
import re
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)

class PumpTokenHandler(BaseHandler):
    """Handler for detecting pump tokens based on various heuristics"""
    
    def __init__(self):
        super().__init__()
        # Common pump token indicators in name/symbol
        self.PUMP_INDICATORS = {
            'pump', 'moon', 'safe', 'fair', 'gem', 'elon', 'doge',
            'shib', 'inu', 'pepe', 'ai', 'gpt', 'chad', 'wojak',
            'fomo', 'yolo', 'lambo', 'rocket', '🚀', '💎', '🌙'
        }
        
        # Suspicious patterns in addresses
        self.SUSPICIOUS_PATTERNS = [
            r'pump$',
            r'moon$',
            r'safe$',
            r'gem$',
            r'[A-Z]{4,}pump',
            r'[A-Z]{4,}moon'
        ]
        
        self.known_pump_tokens = set()
        self.validated_addresses = set()
        
    def analyze_token(self, 
                     address: str, 
                     metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze a token to determine if it's likely a pump token.
        
        Args:
            address: Token mint address
            metadata: Optional metadata about the token (name, symbol, etc)
            
        Returns:
            Dict with analysis results
        """
        if not address:
            return {'is_pump': False, 'confidence': 0, 'reasons': []}
            
        # Check cache
        if address in self.known_pump_tokens:
            return {'is_pump': True, 'confidence': 1.0, 'reasons': ['Previously identified']}
            
        if address in self.validated_addresses:
            return {'is_pump': False, 'confidence': 0.8, 'reasons': ['Previously validated']}
            
        reasons = []
        confidence = 0.0
        
        # Check address patterns
        address_lower = address.lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, address_lower):
                reasons.append(f'Suspicious address pattern: {pattern}')
                confidence += 0.3
                
        # Check metadata if provided
        if metadata:
            name = metadata.get('name', '').lower()
            symbol = metadata.get('symbol', '').lower()
            
            # Check name/symbol for pump indicators
            for indicator in self.PUMP_INDICATORS:
                if indicator in name:
                    reasons.append(f'Suspicious name contains: {indicator}')
                    confidence += 0.4
                if indicator in symbol:
                    reasons.append(f'Suspicious symbol contains: {indicator}')
                    confidence += 0.4
                    
            # Check other metadata red flags
            if metadata.get('supply') and int(metadata['supply']) > 1_000_000_000_000:
                reasons.append('Extremely large supply')
                confidence += 0.2
                
            if metadata.get('holders', 0) < 10:
                reasons.append('Very few holders')
                confidence += 0.2
                
        # Cap confidence at 1.0
        confidence = min(confidence, 1.0)
        
        # Cache result if confident
        if confidence > 0.7:
            self.known_pump_tokens.add(address)
        elif confidence < 0.2:
            self.validated_addresses.add(address)
            
        return {
            'is_pump': confidence > 0.5,
            'confidence': confidence,
            'reasons': reasons
        }
        
    def batch_analyze(self, addresses: List[str], 
                     metadata: Dict[str, Dict] = None) -> Dict[str, Dict]:
        """
        Analyze multiple tokens in batch.
        
        Args:
            addresses: List of token addresses to analyze
            metadata: Optional dict mapping addresses to their metadata
            
        Returns:
            Dict mapping addresses to their analysis results
        """
        results = {}
        for address in addresses:
            token_metadata = metadata.get(address) if metadata else None
            results[address] = self.analyze_token(address, token_metadata)
        return results
