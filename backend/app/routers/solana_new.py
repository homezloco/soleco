"""
Solana router module for handling Solana blockchain interactions
"""
from typing import Dict, List, Optional, Any, Union
import traceback
from fastapi import APIRouter, HTTPException, Query, Path
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.system_program import ID as SYSTEM_PROGRAM_ID
import time
import logging
import json
from datetime import datetime, timezone
from collections import defaultdict

from ..utils.solana_rpc import (
    SolanaConnectionPool, 
    get_connection_pool,
    SolanaClient,
    create_robust_client
)
from ..utils.solana_errors import RetryableError, RPCError
from ..utils.solana_query import SolanaQueryHandler
from ..utils.solana_response import (
    MintHandler
)
from ..utils.handlers.network_status_handler import NetworkStatusHandler
from ..utils.handlers.rpc_node_extractor import RPCNodeExtractor

# Configure logging
logger = logging.getLogger(__name__)

# Program IDs
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
TOKEN_2022_PROGRAM_ID = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
VOTE_PROGRAM_ID = Pubkey.from_string("Vote111111111111111111111111111111111111111")

# Configuration for RPC connection
RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-api.projectserum.com",
    "https://rpc.ankr.com/solana"
]
