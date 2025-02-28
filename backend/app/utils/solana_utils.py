"""
Solana utility functions for transaction and account data processing.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import Transaction
from solders.message import Message
from datetime import datetime
import base58
import json

from .solana_rpc import SolanaConnectionPool
from .solana_errors import RetryableError, RPCError

logger = logging.getLogger(__name__)

def decode_instruction_data(data: str) -> Optional[bytes]:
    """Decode base58 encoded instruction data"""
    try:
        return base58.b58decode(data)
    except BaseException as e:
        logger.debug(f"Error decoding instruction data: {e}")
        return None

def format_timestamp(timestamp: Optional[int]) -> Optional[str]:
    """Format a Unix timestamp into ISO format"""
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(timestamp).isoformat()
    except BaseException as e:
        logger.error(f"Error formatting timestamp {timestamp}: {e}")
        return None
