"""
Common utility functions for the Soleco application.
"""

import logging
import time
import base58
import base64
from typing import Dict, List, Any, Optional, Union
from solders.pubkey import Pubkey

logger = logging.getLogger(__name__)

class Utils:
    """
    Utility class with static methods for common operations.
    """
    
    @staticmethod
    def encode_bs58(data: bytes) -> str:
        """
        Encode bytes as base58 string.
        
        Args:
            data: Bytes to encode
            
        Returns:
            Base58 encoded string
        """
        return base58.b58encode(data).decode('utf-8')
    
    @staticmethod
    def decode_bs58(data: str) -> bytes:
        """
        Decode base58 string to bytes.
        
        Args:
            data: Base58 encoded string
            
        Returns:
            Decoded bytes
        """
        return base58.b58decode(data)
    
    @staticmethod
    def encode_base64(data: bytes) -> str:
        """
        Encode bytes as base64 string.
        
        Args:
            data: Bytes to encode
            
        Returns:
            Base64 encoded string
        """
        return base64.b64encode(data).decode('utf-8')
    
    @staticmethod
    def decode_base64(data: str) -> bytes:
        """
        Decode base64 string to bytes.
        
        Args:
            data: Base64 encoded string
            
        Returns:
            Decoded bytes
        """
        return base64.b64decode(data)
    
    @staticmethod
    def pubkey_to_string(pubkey: Pubkey) -> str:
        """
        Convert Pubkey to string.
        
        Args:
            pubkey: Solana public key
            
        Returns:
            String representation of public key
        """
        return str(pubkey)
    
    @staticmethod
    def string_to_pubkey(pubkey_str: str) -> Pubkey:
        """
        Convert string to Pubkey.
        
        Args:
            pubkey_str: String representation of public key
            
        Returns:
            Solana public key
        """
        return Pubkey.from_string(pubkey_str)
    
    @staticmethod
    def format_timestamp(timestamp: float) -> str:
        """
        Format Unix timestamp to ISO format.
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            Formatted timestamp string
        """
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
    
    @staticmethod
    def truncate_string(text: str, max_length: int = 10) -> str:
        """
        Truncate string to specified length.
        
        Args:
            text: String to truncate
            max_length: Maximum length
            
        Returns:
            Truncated string
        """
        if len(text) <= max_length:
            return text
        return f"{text[:max_length]}..."
