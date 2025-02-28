"""
Solana New Mints Extractor - Focused on detecting and analyzing newly created mint addresses
"""

from typing import Dict, List, Optional, Any, Union, Set
import logging
import time
import asyncio
from fastapi import APIRouter, Query, HTTPException
from solders.pubkey import Pubkey
import json
from collections import defaultdict
import base58

from ..utils.solana_query import SolanaQueryHandler
from ..utils.solana_response import SolanaResponseManager
from ..utils.solana_helpers import DEFAULT_COMMITMENT
from ..utils.handlers.base_handler import BaseHandler
from ..utils.solana_types import EndpointConfig
from ..utils.solana_errors import RPCError, RetryableError
from ..utils.solana_rpc import AdaptiveRateConfig, SolanaRateLimiter

# Configure logging
logger = logging.getLogger(__name__)

# Constants
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"

# Constants for token programs and mint creation
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

# Known programs that create mints
MINT_CREATION_PROGRAMS = {
    "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s",  # Metaplex Token Metadata
    "M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K",  # Magic Eden v2
    "MEisE1HzehtrDpAAT8PnLHjpSSkRYakotTuJRPjTpo8",  # Magic Eden v3
    "hausS13jsjafwWwGqZTUQRmWyvyxn9EQpqMwV1PBBmk",  # Opensea
}

# Token program IDs
METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"

# Token program instruction discriminators
TOKEN_IX_DISCRIMINATORS = {
    "initializeMint": "0",
    "initializeMint2": "8",
    "createMetadata": "b",
    "createMasterEdition": "c"
}

# Known token mints to exclude
KNOWN_TOKEN_MINTS = {
    "So11111111111111111111111111111111111111112",  # Wrapped SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "7i5KKsX2weiTkry7jA4ZwSJ4zRWqW2PPkiupCAMMQCLQ",  # PYTH
}

# Rate limiting configuration
rate_config = AdaptiveRateConfig(
    initial_rate=5,      # Start conservatively
    min_rate=2,         # Lower bound for rate
    max_rate=10,        # Upper bound for rate
    increase_threshold=0.6,  # When to increase rate
    decrease_threshold=0.4,  # When to decrease rate
    adjustment_factor=1.1    # How much to adjust by
)

# Endpoint configuration
endpoint_config = EndpointConfig(
    url="https://api.mainnet-beta.solana.com",
    requests_per_second=5.0,
    burst_limit=10,
    max_retries=3,
    retry_delay=2.0
)

# Create FastAPI router
router = APIRouter(
    prefix="/solana/new-mints",
    tags=["solana", "mints"]
)

class TransactionStats:
    """Track transaction processing statistics"""
    
    def __init__(self):
        # Basic stats
        self.start_time = time.time()
        self.total_processed = 0
        self.total_instructions = 0
        self.total_mints = 0
        self.total_programs = set()
        
        # Mint tracking
        self.mint_addresses = set()
        self.mint_activity = defaultdict(lambda: {
            'first_seen': None,
            'last_seen': None,
            'transaction_count': 0,
            'total_transfers': 0
        })
        
        # Program tracking
        self.program_stats = defaultdict(lambda: {
            'calls': 0,
            'mint_creations': 0,
            'instruction_count': 0,
            'unique_signers': set()
        })
        
        # Error tracking
        self.error_counts = defaultdict(int)
        self.error_details = defaultdict(list)
        
    def update_mint_stats(self, mint_address: str, timestamp: Optional[int] = None):
        """Update statistics for a specific mint address"""
        if not mint_address:
            return
            
        self.mint_addresses.add(mint_address)
        
        if mint_address not in self.mint_activity:
            self.mint_activity[mint_address] = {
                'first_seen': timestamp or int(time.time()),
                'last_seen': timestamp or int(time.time()),
                'transaction_count': 1,
                'total_transfers': 0
            }
        else:
            stats = self.mint_activity[mint_address]
            stats['transaction_count'] += 1
            if timestamp:
                if not stats['first_seen'] or timestamp < stats['first_seen']:
                    stats['first_seen'] = timestamp
                if not stats['last_seen'] or timestamp > stats['last_seen']:
                    stats['last_seen'] = timestamp
                    
    def update_program_stats(self, program_id: str, instruction_count: int = 1, 
                           mint_created: bool = False, signer: Optional[str] = None):
        """Update statistics for a specific program"""
        if not program_id:
            return
            
        stats = self.program_stats[program_id]
        stats['calls'] += 1
        stats['instruction_count'] += instruction_count
        
        if mint_created:
            stats['mint_creations'] += 1
            
        if signer:
            stats['unique_signers'].add(signer)
            
    def log_summary(self):
        """Log comprehensive statistics summary"""
        duration = time.time() - self.start_time
        
        logger.info(
            f"\nTransaction Processing Summary:\n"
            f"Performance:\n"
            f"- Total processed: {self.total_processed}\n"
            f"- Total instructions: {self.total_instructions}\n"
            f"- Duration: {duration:.2f}s\n"
            f"- Avg time per tx: {(duration/max(1, self.total_processed))*1000:.2f}ms\n\n"
            f"Mint Statistics:\n"
            f"- Total mints: {self.total_mints}\n"
            f"- Unique mint addresses: {len(self.mint_addresses)}\n\n"
            f"Program Statistics:\n"
            f"- Unique programs: {len(self.total_programs)}\n"
            f"- Program details:\n"
            f"{json.dumps(self.get_program_summary(), indent=2)}\n\n"
            f"Error Statistics:\n"
            f"- Total errors: {sum(self.error_counts.values())}\n"
            f"- By type: {json.dumps(dict(self.error_counts), indent=2)}"
        )
        
    def get_program_summary(self) -> Dict[str, Any]:
        """Get a summary of program statistics"""
        return {
            program_id: {
                'calls': stats['calls'],
                'mint_creations': stats['mint_creations'],
                'instruction_count': stats['instruction_count'],
                'unique_signers': len(stats['unique_signers'])
            }
            for program_id, stats in self.program_stats.items()
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary format"""
        return {
            "timing": {
                "start_time": self.start_time,
                "duration": time.time() - self.start_time
            },
            "transactions": {
                "total_processed": self.total_processed,
                "total_instructions": self.total_instructions,
                "avg_time_per_tx": (time.time() - self.start_time) / max(1, self.total_processed)
            },
            "mints": {
                "total_mints": self.total_mints,
                "unique_addresses": len(self.mint_addresses),
                "mint_activity": {
                    addr: {
                        k: list(v) if isinstance(v, set) else v 
                        for k, v in stats.items()
                    }
                    for addr, stats in self.mint_activity.items()
                }
            },
            "programs": {
                "unique_count": len(self.total_programs),
                "stats": self.get_program_summary()
            },
            "errors": {
                "counts": dict(self.error_counts),
                "details": {
                    error_type: details[:100]  # Limit details to avoid huge payloads
                    for error_type, details in self.error_details.items()
                }
            }
        }

class NewMintsResponseHandler(BaseHandler):
    """Handler for new mints responses"""
    
    def __init__(self, response_manager: SolanaResponseManager):
        """Initialize with response manager"""
        super().__init__()  # Call BaseHandler's init without args
        self.response_manager = response_manager
        self.stats = TransactionStats()
        self.SYSTEM_PROGRAM_IDS = {
            'So11111111111111111111111111111111111111112',  # Wrapped SOL
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
            'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',  # Associated Token Program
            'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',  # Token Program 2022
            '11111111111111111111111111111111',  # System Program
            'ComputeBudget111111111111111111111111111111',  # Compute Budget
            'Vote111111111111111111111111111111111111111',  # Vote Program
            'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr',  # Memo Program
        }
        
    async def process_result(self, result: Any) -> Dict[str, Any]:
        """
        Process block result and extract mint addresses with enhanced error handling and logging.
        
        Args:
            result: Block data from Solana RPC
            
        Returns:
            Dict containing processed results and statistics
        """
        start_time = time.time()
        stats = self._get_empty_stats()
        
        try:
            if not result or not isinstance(result, dict):
                logger.error("Invalid block result format")
                stats["invalid_tx_formats"] += 1
                return stats
                
            transactions = result.get("transactions", [])
            if not transactions:
                logger.debug("No transactions in block")
                return stats
                
            # Get block timestamp
            block_timestamp = self._get_block_timestamp(result)
            stats["timestamp"] = block_timestamp
            
            # Process each transaction
            for tx_index, tx in enumerate(transactions):
                try:
                    # Skip vote transactions early
                    if self._is_vote_transaction(tx):
                        continue
                        
                    # Process transaction and update stats
                    tx_stats = self._process_transaction(tx, tx_index)
                    
                    # Update block statistics
                    stats["total_transactions"] += 1
                    stats["total_instructions"] += tx_stats.get("instruction_count", 0)
                    stats["token_program_txs"] += tx_stats.get("token_program_calls", 0)
                    stats["new_mints"] += tx_stats.get("new_mints", 0)
                    
                    # Track errors
                    if tx_stats.get("errors"):
                        stats["transaction_errors"] += 1
                        stats["error_details"].extend(tx_stats["errors"])
                        
                    # Update program statistics
                    for program_id in tx_stats.get("programs_called", set()):
                        stats["programs_called"].add(program_id)
                        
                except Exception as e:
                    logger.error(f"Error processing transaction {tx_index}: {str(e)}", exc_info=True)
                    stats["transaction_errors"] += 1
                    stats["error_details"].append({
                        "type": "transaction_processing_error",
                        "index": tx_index,
                        "error": str(e)
                    })
                    
            # Calculate processing duration
            stats["processing_duration_ms"] = int((time.time() - start_time) * 1000)
            
            # Log summary statistics
            logger.info(
                f"Block processing complete:\n"
                f"Total transactions: {stats['total_transactions']}\n"
                f"New mints found: {stats['new_mints']}\n"
                f"Errors: {stats['transaction_errors']}\n"
                f"Duration: {stats['processing_duration_ms']}ms"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error processing block result: {str(e)}", exc_info=True)
            stats["error_details"].append({
                "type": "block_processing_error",
                "error": str(e)
            })
            return stats
            
    def _process_transaction(self, tx: Dict[str, Any], tx_index: int) -> Dict[str, Any]:
        """
        Process a transaction to extract mint addresses with detailed tracking.
        
        Args:
            tx: Transaction data
            tx_index: Index of transaction in block
            
        Returns:
            Dict containing transaction statistics and found mint addresses
        """
        stats = {
            "instruction_count": 0,
            "token_program_calls": 0,
            "new_mints": 0,
            "programs_called": set(),
            "errors": []
        }
        
        try:
            # Get transaction data
            if not tx or not isinstance(tx, dict):
                logger.debug(f"Invalid transaction format at index {tx_index}")
                return stats
                
            # Skip failed transactions
            meta = tx.get("meta", {})
            if meta.get("err") is not None:
                logger.debug(f"Skipping failed transaction at index {tx_index}")
                return stats
                
            # Process transaction message
            message = tx.get("transaction", {}).get("message", {})
            if not message:
                logger.debug(f"No message in transaction at index {tx_index}")
                return stats
                
            # Get account keys
            account_keys = message.get("accountKeys", [])
            if not account_keys:
                logger.debug(f"No account keys in transaction at index {tx_index}")
                return stats
                
            # Process instructions
            instructions = message.get("instructions", [])
            stats["instruction_count"] = len(instructions)
            
            for ix in instructions:
                try:
                    # Track program calls
                    program_id = ix.get("programId")
                    if program_id:
                        stats["programs_called"].add(str(program_id))
                        
                    # Check for token program usage
                    if program_id in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID, METADATA_PROGRAM_ID]:
                        stats["token_program_calls"] += 1
                        
                    # Extract mint addresses
                    mint_address = self._extract_mint_address(ix, account_keys)
                    if mint_address:
                        stats["new_mints"] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing instruction in tx {tx_index}: {str(e)}")
                    stats["errors"].append({
                        "type": "instruction_processing_error",
                        "tx_index": tx_index,
                        "error": str(e)
                    })
                    
            # Process inner instructions
            inner_instructions = meta.get("innerInstructions", [])
            for inner_ix_group in inner_instructions:
                for inner_ix in inner_ix_group.get("instructions", []):
                    try:
                        stats["instruction_count"] += 1
                        program_id = inner_ix.get("programId")
                        if program_id:
                            stats["programs_called"].add(str(program_id))
                            
                        # Check for token program usage
                        if program_id in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID, METADATA_PROGRAM_ID]:
                            stats["token_program_calls"] += 1
                            
                        # Extract mint addresses
                        mint_address = self._extract_mint_address(inner_ix, account_keys)
                        if mint_address:
                            stats["new_mints"] += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing inner instruction in tx {tx_index}: {str(e)}")
                        stats["errors"].append({
                            "type": "inner_instruction_processing_error",
                            "tx_index": tx_index,
                            "error": str(e)
                        })
                        
            # Process token balances
            pre_balances = meta.get("preTokenBalances", [])
            post_balances = meta.get("postTokenBalances", [])
            if pre_balances and post_balances:
                self._process_token_balances(pre_balances, post_balances, tx_index)
                
            return stats
            
        except Exception as e:
            logger.error(f"Error in transaction processing: {str(e)}", exc_info=True)
            stats["errors"].append({
                "type": "transaction_processing_error",
                "tx_index": tx_index,
                "error": str(e)
            })
            return stats
            
    def _is_vote_transaction(self, tx: Dict[str, Any]) -> bool:
        """Check if transaction is a vote transaction to skip processing"""
        try:
            message = tx.get("transaction", {}).get("message", {})
            if not message:
                return False
                
            # Check program ID in first instruction
            instructions = message.get("instructions", [])
            if not instructions:
                return False
                
            first_ix = instructions[0]
            program_id = first_ix.get("programId")
            
            return program_id == "Vote111111111111111111111111111111111111111"
            
        except Exception as e:
            logger.debug(f"Error checking vote transaction: {str(e)}")
            return False

    def _get_empty_stats(self) -> Dict[str, Any]:
        """Get empty statistics dictionary with enhanced metrics"""
        return {
            "total_transactions": 0,
            "total_instructions": 0,
            "token_program_txs": 0,
            "new_mints": 0,
            "transaction_errors": 0,
            "instruction_errors": 0,
            "inner_instruction_errors": 0,
            "invalid_tx_formats": 0,
            "skipped_base58_txs": 0,
            "missing_data_txs": 0,
            "missing_account_keys": 0,
            "token_balance_changes": 0,
            "large_transfers": 0,
            "slot_errors": 0,
            "processing_duration_ms": 0,
            "programs_called": set(),
            "error_details": [],
            "timestamp": int(time.time())
        }
        
    def _has_token_program(self, tx: Dict[str, Any]) -> bool:
        """Check if transaction involves token program"""
        try:
            # Get parsed transaction data
            parsed_tx = tx.get("transaction")
            if isinstance(parsed_tx, str):
                # Handle base58 encoded transaction
                logger.debug("Found base58 encoded transaction")
                return False
                
            message = parsed_tx.get("message", {})
            if not message:
                logger.debug("No message found in transaction")
                return False
                
            # Check account keys
            account_keys = message.get("accountKeys", [])
            if not account_keys:
                logger.debug("No account keys found")
                return False
                
            # Check for token program in account keys
            for key in account_keys:
                if isinstance(key, dict):
                    pubkey = key.get("pubkey")
                else:
                    pubkey = key
                if str(pubkey) in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID, METADATA_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID]:
                    logger.debug(f"Found token program in account keys: {pubkey}")
                    return True
            
            # Check program IDs in instructions
            instructions = message.get("instructions", [])
            for ix in instructions:
                program_id = None
                if isinstance(ix, dict):
                    program_id = ix.get("programId")
                elif hasattr(ix, "program_id"):
                    program_id = str(ix.program_id)
                
                if str(program_id) in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID, METADATA_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID]:
                    logger.debug(f"Found token program in instructions: {program_id}")
                    return True
                    
            # Check inner instructions if available
            meta = tx.get("meta", {})
            inner_instructions = meta.get("innerInstructions", [])
            for inner_ix_group in inner_instructions:
                for inner_ix in inner_ix_group.get("instructions", []):
                    program_id = None
                    if isinstance(inner_ix, dict):
                        program_id = inner_ix.get("programId")
                    elif hasattr(inner_ix, "program_id"):
                        program_id = str(inner_ix.program_id)
                    
                    if str(program_id) in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID, METADATA_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID]:
                        logger.debug(f"Found token program in inner instructions: {program_id}")
                        return True
            
            logger.debug("No token program found in transaction")
            return False
            
        except Exception as e:
            logger.error(f"Error checking for token program: {str(e)}")
            return False
            
    def _is_initialize_mint(self, instruction: Dict[str, Any]) -> bool:
        """Check if instruction is InitializeMint"""
        try:
            # Log instruction for debugging
            logger.debug(f"Checking instruction: {json.dumps(instruction, indent=2)}")
            
            # Check program ID first
            program_id = instruction.get("programId")
            if not program_id:
                logger.debug("No program ID found")
                return False
                
            program_id = str(program_id)
            
            # Handle different program types
            if program_id in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                return self._check_token_initialize_mint(instruction, program_id)
            elif program_id == METADATA_PROGRAM_ID:
                return self._check_metadata_initialize_mint(instruction)
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking initialize mint: {str(e)}", exc_info=True)
            return False
            
    def _check_token_initialize_mint(self, instruction: Dict[str, Any], program_id: str) -> bool:
        """Check if instruction is a token program initialize mint"""
        try:
            # Check instruction data
            data = instruction.get("data")
            if not data:
                return False
                
            # Check discriminator
            if program_id == TOKEN_PROGRAM_ID and data.startswith(TOKEN_IX_DISCRIMINATORS["initializeMint"]):
                logger.debug("Found InitializeMint instruction (Token)")
                return True
            elif program_id == TOKEN_2022_PROGRAM_ID and data.startswith(TOKEN_IX_DISCRIMINATORS["initializeMint2"]):
                logger.debug("Found InitializeMint2 instruction (Token-2022)")
                return True
                
            # Check parsed data
            parsed = instruction.get("parsed", {})
            if isinstance(parsed, dict):
                program = parsed.get("program")
                type_ = parsed.get("type")
                if (program == "spl-token" and type_ == "initializeMint") or \
                   (program == "spl-token-2022" and type_ == "initializeMint2"):
                    logger.debug(f"Found initialize mint in parsed data: {program} - {type_}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking token initialize mint: {str(e)}", exc_info=True)
            return False
            
    def _check_metadata_initialize_mint(self, instruction: Dict[str, Any]) -> bool:
        """Check if instruction is a metadata program initialize mint"""
        try:
            data = instruction.get("data")
            if not data:
                return False
                
            # Check for metadata creation instructions
            if data.startswith(TOKEN_IX_DISCRIMINATORS["createMetadata"]) or \
               data.startswith(TOKEN_IX_DISCRIMINATORS["createMasterEdition"]):
                logger.debug("Found metadata creation instruction")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking metadata initialize mint: {str(e)}", exc_info=True)
            return False

    def _is_valid_mint_address(self, address: str) -> bool:
        """
        Validate if an address is likely to be a mint address.
        Uses multiple validation steps to ensure accuracy.
        
        Args:
            address: The address to validate
            
        Returns:
            bool: True if address appears to be a valid mint address
        """
        if not address:
            return False
            
        # Filter out known system addresses and programs
        EXCLUDED_ADDRESSES = {
            # System and Token Programs
            'So11111111111111111111111111111111111111112',  # Wrapped SOL
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
            'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',  # Associated Token Program
            'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',  # Token Program 2022
            '11111111111111111111111111111111',  # System Program
            'ComputeBudget111111111111111111111111111111',  # Compute Budget
            
            # Voting and Governance
            'Vote111111111111111111111111111111111111111',  # Vote Program
            'Stake11111111111111111111111111111111111111',  # Stake Program
            'Gov1111111111111111111111111111111111111111',  # Governance
            
            # Utility Programs
            'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr',  # Memo Program
            'AddressLookupTab1e1111111111111111111111111',  # Address Lookup Table
            'BPFLoaderUpgradeab1e11111111111111111111111',  # BPF Loader
            'Config1111111111111111111111111111111111111',  # Config Program
            
            # Common DEX Programs
            'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4',  # Jupiter
            'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc',  # Whirlpool
            '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8',  # Raydium
            
            # NFT Marketplaces
            'M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K',  # Magic Eden v2
            'MEisE1HzehtrDpAAT8PnLHjpSSkRYakotTuJRPjTpo8',  # Magic Eden v3
            'hausS13jsjafwWwGqZTUQRmWyvyxn9EQpqMwV1PBBmk',  # Opensea
        }
        
        if address in EXCLUDED_ADDRESSES:
            return False
            
        # Filter out known token mints (stablecoins, major tokens)
        KNOWN_TOKEN_MINTS = {
            'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
            'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',  # USDT
            'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',  # BONK
            '7i5KKsX2weiTkry7jA4ZwSJ4zRWqW2PPkiupCAMMQCLQ',  # PYTH
        }
        
        if address in KNOWN_TOKEN_MINTS:
            return False
            
        # Validate address format
        try:
            # Check if it's a valid base58 address of correct length
            decoded = base58.b58decode(address)
            if len(decoded) != 32:  # Solana addresses are 32 bytes
                logger.debug(f"Invalid address length: {len(decoded)} bytes")
                return False
                
            # Additional heuristic checks
            if address.startswith('1111') or address.endswith('1111'):
                logger.debug(f"Address likely a program ID: {address}")
                return False
                
            # Check for common program ID patterns
            if any(pattern in address for pattern in ['Program', 'Config', 'Loader', 'Table']):
                logger.debug(f"Address matches program pattern: {address}")
                return False
                
            return True
            
        except Exception as e:
            logger.debug(f"Error validating address {address}: {str(e)}")
            return False
            
    def _extract_mint_address(self, instruction: Dict[str, Any], account_keys: List[str]) -> Optional[str]:
        """Extract mint address from instruction"""
        try:
            # Log inputs at debug level
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Extracting mint address from instruction: {json.dumps(instruction, indent=2)}")
                logger.debug(f"Account keys: {json.dumps(account_keys, indent=2)}")
            
            # Get program ID and accounts
            program_id = str(instruction.get("programId", ""))
            accounts = instruction.get("accounts", [])
            
            if not program_id or not accounts:
                logger.debug("Missing program ID or accounts")
                return None
                
            # Handle different program types
            mint_address = None
            if program_id in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                mint_address = self._extract_token_mint_address(instruction, accounts, account_keys)
            elif program_id == METADATA_PROGRAM_ID:
                mint_address = self._extract_metadata_mint_address(instruction, accounts, account_keys)
            elif program_id == ASSOCIATED_TOKEN_PROGRAM_ID:
                mint_address = self._extract_ata_mint_address(instruction, accounts, account_keys)
                
            # Validate extracted address
            if mint_address and self._is_valid_mint_address(mint_address):
                logger.info(f"Found valid mint address: {mint_address} from program {program_id}")
                return mint_address
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting mint address: {str(e)}", exc_info=True)
            return None
            
    def _extract_token_mint_address(self, instruction: Dict[str, Any], accounts: List[Any], account_keys: List[str]) -> Optional[str]:
        """Extract mint address from token program instruction"""
        try:
            # For Token/Token-2022 InitializeMint:
            # accounts[0] = mint account being initialized
            if not accounts:
                return None
                
            # Get mint account index
            mint_idx = accounts[0]
            if isinstance(mint_idx, int) and mint_idx < len(account_keys):
                mint_address = account_keys[mint_idx]
                if isinstance(mint_address, dict):
                    return mint_address.get("pubkey")
                return str(mint_address)
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting token mint address: {str(e)}", exc_info=True)
            return None
            
    def _extract_metadata_mint_address(self, instruction: Dict[str, Any], accounts: List[Any], account_keys: List[str]) -> Optional[str]:
        """Extract mint address from metadata program instruction"""
        try:
            # For Metadata instructions:
            # createMetadata/createMasterEdition:
            # accounts[1] = mint account
            if len(accounts) < 2:
                return None
                
            mint_idx = accounts[1]
            if isinstance(mint_idx, int) and mint_idx < len(account_keys):
                mint_address = account_keys[mint_idx]
                if isinstance(mint_address, dict):
                    return mint_address.get("pubkey")
                return str(mint_address)
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting metadata mint address: {str(e)}", exc_info=True)
            return None
            
    def _extract_ata_mint_address(self, instruction: Dict[str, Any], accounts: List[Any], account_keys: List[str]) -> Optional[str]:
        """Extract mint address from associated token account instruction"""
        try:
            # For Create ATA:
            # accounts[1] = mint account
            if len(accounts) < 2:
                return None
                
            mint_idx = accounts[1]
            if isinstance(mint_idx, int) and mint_idx < len(account_keys):
                mint_address = account_keys[mint_idx]
                if isinstance(mint_address, dict):
                    return mint_address.get("pubkey")
                return str(mint_address)
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting ATA mint address: {str(e)}", exc_info=True)
            return None

    def _process_token_balances(self, pre_balances: List[Dict], post_balances: List[Dict], program_id: str) -> None:
        """Process token balance changes with detailed tracking"""
        if not pre_balances or not post_balances:
            return

        # Track balance changes
        for pre, post in zip(pre_balances, post_balances):
            if not (isinstance(pre, dict) and isinstance(post, dict)):
                continue
                
            pre_amount = int(pre.get('uiTokenAmount', {}).get('amount', 0))
            post_amount = int(post.get('uiTokenAmount', {}).get('amount', 0))
            mint = pre.get('mint')
            
            if not mint:
                continue
                
            # Calculate absolute change
            change = abs(post_amount - pre_amount)
            
            if change > 0:
                self.stats.token_transfers += 1
                
                # Track large transfers
                if change > 1000:
                    owner = pre.get("owner", "unknown")
                    logger.info(
                        f"Large token transfer detected:\n"
                        f"Program: {program_id}\n"
                        f"Amount: {change:,.2f}\n" 
                        f"Mint: {mint}\n"
                        f"Owner: {owner}"
                    )
                    self.stats.large_transfers += 1
                    
            # Track token activity by mint
            self.stats.token_activity[mint] = {
                'total_volume': self.stats.token_activity.get(mint, {}).get('total_volume', 0) + change,
                'transaction_count': self.stats.token_activity.get(mint, {}).get('transaction_count', 0) + 1
            }
            
            # Track program-specific token stats
            if program_id:
                if program_id not in self.stats.program_token_stats:
                    self.stats.program_token_stats[program_id] = defaultdict(int)
                self.stats.program_token_stats[program_id][mint] += change

    def _process_compute_units(self, meta: Dict[str, Any]) -> None:
        """Process compute unit consumption with monitoring"""
        try:
            if not isinstance(meta, dict):
                return
            
            compute_units = meta.get('computeUnitsConsumed', 0)
            if not isinstance(compute_units, (int, float)):
                return
            
            self.stats.total_compute_units += compute_units
            
            # Track high compute usage
            if compute_units > 200000:
                self.stats.high_compute_transactions += 1
                logger.warning(
                    f"High compute units detected: {compute_units:,}\n"
                    f"Total consumed: {self.stats.total_compute_units:,}\n"
                    f"Max per tx: {self.stats.max_compute_units:,}"
                )
                
            # Update compute unit distribution
            if compute_units <= 20000:
                self.stats.compute_distribution['low'] += 1
            elif compute_units <= 100000:
                self.stats.compute_distribution['medium'] += 1
            else:
                self.stats.compute_distribution['high'] += 1
                
            # Track program-specific compute units
            if 'innerInstructions' in meta:
                for inner_ix in meta['innerInstructions']:
                    if isinstance(inner_ix, dict) and 'instructions' in inner_ix:
                        for ix in inner_ix['instructions']:
                            if isinstance(ix, dict) and 'programId' in ix:
                                program_id = ix['programId']
                                if program_id not in self.stats.program_compute_units:
                                    self.stats.program_compute_units[program_id] = 0
                                self.stats.program_compute_units[program_id] += compute_units

        except Exception as e:
            self.stats.error_counts["compute_unit_processing_failed"] += 1
            logger.exception(f"Failed to process compute units: {str(e)}")

    def _process_program_error(self, error: Any, transaction: Dict[str, Any]) -> None:
        """Process program errors with enhanced error tracking"""
        try:
            # Handle InstructionError format
            if isinstance(error, dict) and 'InstructionError' in error:
                instruction_idx, error_detail = error['InstructionError']
                
                # Get program ID from instruction
                program_id = self._get_program_id_from_instruction(transaction, instruction_idx)
                if not program_id:
                    self.stats.error_counts["unknown_program_error"] += 1
                    return
                    
                # Track error by program
                self.stats.program_errors[program_id][str(error_detail)] += 1
                
                # Handle custom program errors
                if isinstance(error_detail, dict) and 'Custom' in error_detail:
                    error_code = error_detail['Custom']
                    self.stats.error_counts[f"custom_error_{error_code}"] += 1
                    
                    # Log detailed error context
                    logger.warning(
                        f"Custom program error:\n"
                        f"Program: {program_id}\n"
                        f"Error code: {error_code}\n"
                        f"Instruction index: {instruction_idx}"
                    )
                    
                    # Track specific Jupiter errors
                    if program_id == "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4":
                        if error_code == 0x1771:  # 6001 decimal
                            self.stats.error_counts["jupiter_route_not_found"] += 1
                        elif error_code == 0x1772:  # 6002 decimal
                            self.stats.error_counts["jupiter_slippage_exceeded"] += 1
                    
                # Handle system program errors
                elif isinstance(error_detail, str):
                    self.stats.error_counts[f"system_{error_detail}"] += 1
                    logger.warning(f"System program error: {error_detail} in {program_id}")
                    
            # Handle raw custom errors
            elif isinstance(error, dict) and 'Custom' in error:
                error_code = error['Custom']
                self.stats.error_counts[f"raw_custom_{error_code}"] += 1
                logger.warning(f"Raw custom error: {error_code}")
                
            else:
                self.stats.error_counts["unknown_format"] += 1
                logger.warning(f"Unknown error format: {error}")
                
        except Exception as e:
            self.stats.error_counts["error_processing_failed"] += 1
            logger.exception(f"Failed to process program error: {str(e)}")

    def _get_program_id_from_instruction(self, transaction: Dict[str, Any], instruction_idx: int) -> Optional[str]:
        """Extract program ID from transaction instruction"""
        try:
            if not transaction or 'message' not in transaction:
                return None
                
            message = transaction['message']
            if 'instructions' not in message:
                return None
                
            instructions = message['instructions']
            if not instructions or instruction_idx >= len(instructions):
                return None
                
            instruction = instructions[instruction_idx]
            if 'programIdIndex' not in instruction:
                return None
                
            program_idx = instruction['programIdIndex']
            if 'accountKeys' not in message:
                return None
                
            account_keys = message['accountKeys']
            if not account_keys or program_idx >= len(account_keys):
                return None
                
            return account_keys[program_idx]
            
        except Exception as e:
            logger.error(f"Failed to extract program ID: {str(e)}")
            return None

    def _is_mint_creation(self, instruction: Dict[str, Any]) -> bool:
        """Check if an instruction is creating a new mint."""
        try:
            # Check for Token Program mint initialization
            if instruction.get('programId') in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                data = instruction.get('data', '')
                # Check for InitializeMint instruction
                if data and data.startswith('1'):  # InitializeMint instruction code
                    return True
                    
            # Check for known mint creation programs
            program_id = instruction.get('programId', '')
            if program_id in MINT_CREATION_PROGRAMS:
                return True
                
        except Exception as e:
            logger.debug(f"Error checking mint creation: {str(e)}")
            
        return False
        
    def _get_block_timestamp(self, result: Dict[str, Any]) -> Optional[int]:
        """Extract timestamp from block data."""
        try:
            # Try to get block time from metadata
            if 'blockTime' in result:
                return result['blockTime']
                
            # Fallback to current time
            return int(time.time())
            
        except Exception as e:
            logger.debug(f"Error getting block timestamp: {str(e)}")
            return None
            
    def _extract_program_id(self, instruction: Dict[str, Any], 
                          account_keys: List[str]) -> Optional[str]:
        """Extract program ID from instruction."""
        try:
            program_idx = instruction.get('programIdIndex')
            if program_idx is not None and program_idx < len(account_keys):
                return account_keys[program_idx]
        except Exception as e:
            logger.debug(f"Error extracting program ID: {str(e)}")
        return None
        
    def _extract_mints_from_instruction(self, instruction: Dict[str, Any], account_keys: List[str], tx_index: int) -> List[str]:
        """Extract potential mint addresses from an instruction."""
        found_mints = []
        try:
            # Get program ID - try multiple methods
            program_id = None
            
            # Method 1: Direct program_id field
            if isinstance(instruction, dict):
                program_id = instruction.get("programId")
            elif hasattr(instruction, "program_id"):
                program_id = str(instruction.program_id)
                
            # Method 2: Program ID from account keys
            if not program_id and hasattr(instruction, "program_id_index"):
                try:
                    idx = instruction.program_id_index
                    if isinstance(idx, int) and idx < len(account_keys):
                        program_id = str(account_keys[idx])
                except Exception as e:
                    logger.debug(f"Error getting program_id from index: {e}")
                    
            # Method 3: Last account in accounts array (common pattern)
            if not program_id and hasattr(instruction, "accounts"):
                try:
                    accounts = instruction.accounts
                    if accounts and isinstance(accounts[-1], int) and accounts[-1] < len(account_keys):
                        program_id = str(account_keys[accounts[-1]])
                except Exception as e:
                    logger.debug(f"Error getting program_id from accounts: {e}")
                    
            if not program_id:
                logger.debug(f"Could not determine program ID for instruction in tx {tx_index}")
                return found_mints
                
            # Convert to string if needed
            program_id = str(program_id)
            
            # Process token program instructions
            if program_id in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                # Token program typically has mint account in first few accounts
                for i in range(min(3, len(account_keys))):
                    account = account_keys[i]
                    account_str = str(account)
                    if self._is_valid_mint_address(account_str):
                        found_mints.append(account_str)
                        logger.info(f"Found mint in token program account {i}: {account_str}")
                        
            # Process associated token program instructions
            elif program_id == ASSOCIATED_TOKEN_PROGRAM_ID:
                accounts = getattr(instruction, "accounts", []) or []
                if len(accounts) >= 3:  # ATA typically has mint as 3rd account
                    mint_index = accounts[2]
                    if isinstance(mint_index, int) and mint_index < len(account_keys):
                        mint_account = str(account_keys[mint_index])
                        if self._is_valid_mint_address(mint_account):
                            found_mints.append(mint_account)
                            logger.info(f"Found mint in ATA instruction: {mint_account}")
                            
            # Process metadata program instructions
            elif program_id == METADATA_PROGRAM_ID:
                accounts = getattr(instruction, "accounts", []) or []
                if len(accounts) >= 2:  # Metadata has mint as 2nd account
                    mint_index = accounts[1]
                    if isinstance(mint_index, int) and mint_index < len(account_keys):
                        mint_account = str(account_keys[mint_index])
                        if self._is_valid_mint_address(mint_account):
                            found_mints.append(mint_account)
                            logger.info(f"Found mint in metadata instruction: {mint_account}")
                            
            # Process all accounts for potential mint addresses
            accounts = getattr(instruction, "accounts", []) or []
            for i, account_index in enumerate(accounts):
                if isinstance(account_index, int) and account_index < len(account_keys):
                    account = account_keys[account_index]
                    account_str = str(account)
                    if self._is_valid_mint_address(account_str):
                        found_mints.append(account_str)
                        logger.info(f"Found mint in instruction account {i}: {account_str}")
                        
            # Check instruction data for potential mint references
            data = instruction.get("data") if isinstance(instruction, dict) else getattr(instruction, "data", None)
            if data and isinstance(data, (str, bytes)):
                try:
                    data_str = str(data)
                    if len(data_str) >= 32 and len(data_str) <= 44:
                        if self._is_valid_mint_address(data_str):
                            found_mints.append(data_str)
                            logger.info(f"Found mint in instruction data: {data_str}")
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error processing instruction in tx {tx_index}: {str(e)}")
            
        # Remove duplicates while preserving order
        return list(dict.fromkeys(found_mints))  # Remove duplicates
        
    def _is_valid_mint_address(self, address: str) -> bool:
        """Validate a potential mint address"""
        try:
            if not address:
                return False
                
            address_str = str(address)
            
            # Basic format validation
            if len(address_str) < 32 or len(address_str) > 44:
                return False
                
            # Check for valid Base58 characters
            if not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address_str):
                return False
                
            # Check if it's a known system address
            if address_str in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID, METADATA_PROGRAM_ID, 
                             ASSOCIATED_TOKEN_PROGRAM_ID, COMPUTE_BUDGET_ID]:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating mint address {address}: {str(e)}")
            return False
            
    def _process_token_balances(self, balances: List[Dict[str, Any]]) -> Set[str]:
        """Process token balances to extract mint addresses."""
        mint_addresses = set()
        try:
            for balance in balances:
                mint = balance.get('mint')
                if mint and self._is_valid_mint_address(mint):
                    mint_addresses.add(mint)
                    # Track mint usage statistics
                    self.stats['mint_usage'][mint] = self.stats['mint_usage'].get(mint, 0) + 1
                    
                    # Track token amounts for analysis
                    token_amount = balance.get('uiTokenAmount', {})
                    if token_amount.get('uiAmount') is not None:
                        self.stats['mint_amounts'][mint] = self.stats['mint_amounts'].get(mint, 0) + float(token_amount['uiAmount'])
                        
        except Exception as e:
            logger.error(f"Error processing token balances: {str(e)}")
            self.stats['errors']['token_balance_error'] += 1
            
        return mint_addresses

    def _update_transaction_stats(self, transaction: Dict[str, Any], meta: Dict[str, Any]) -> None:
        """Update transaction-related statistics."""
        try:
            # Track program invocations
            message = transaction.get('message', {})
            instructions = message.get('instructions', [])
            
            for instruction in instructions:
                if 'programIdIndex' in instruction:
                    program_id = message['accountKeys'][instruction['programIdIndex']]
                    self.stats['program_invocations'][program_id] = self.stats['program_invocations'].get(program_id, 0) + 1

            # Track transaction status
            if meta.get('err'):
                self.stats['failed_transactions'] += 1
                error_type = str(meta['err'])
                self.stats['error_types'][error_type] = self.stats['error_types'].get(error_type, 0) + 1
            else:
                self.stats['successful_transactions'] += 1

            # Track compute units
            if 'computeUnitsConsumed' in meta:
                self.stats['total_compute_units'] += meta['computeUnitsConsumed']
                self.stats['avg_compute_units'] = (
                    self.stats['total_compute_units'] / 
                    (self.stats['successful_transactions'] + self.stats['failed_transactions'])
                )

        except Exception as e:
            logger.error(f"Error updating transaction stats: {str(e)}")
            self.stats['errors']['stats_update_error'] += 1
            
    def _initialize_stats_tracking(self) -> Dict[str, Any]:
        """Initialize comprehensive statistics tracking."""
        return {
            'start_time': time.time(),
            'total_transactions': 0,
            'successful_transactions': 0,
            'failed_transactions': 0,
            'total_compute_units': 0,
            'avg_compute_units': 0,
            'total_instructions': 0,
            'program_invocations': defaultdict(int),
            'mint_usage': defaultdict(int),
            'mint_amounts': defaultdict(float),
            'error_types': defaultdict(int),
            'errors': defaultdict(int),
            'new_mints_found': set(),
            'mint_creation_programs': {
                'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 0,
                'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL': 0
            }
        }

    def _is_valid_mint_address(self, address: str) -> bool:
        """
        Validate if an address could be a valid mint address.
        
        Args:
            address: The address to validate
            
        Returns:
            bool: True if the address could be a valid mint, False otherwise
        """
        try:
            # Basic validation
            if not address or not isinstance(address, str):
                return False
                
            # Check length (Solana addresses are 32-44 characters)
            if not (32 <= len(address) <= 44):
                return False
                
            # Check for valid base58 characters
            valid_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
            if not all(c in valid_chars for c in address):
                return False
                
            # Check if address is a known system program
            if address in self.SYSTEM_PROGRAM_IDS:
                return False
                
            # Track validation attempts
            self.stats['address_validations'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating mint address {address}: {str(e)}")
            self.stats['errors']['address_validation_error'] += 1
            return False
            
    def _extract_mints_from_logs(self, log_messages: List[str]) -> Set[str]:
        """
        Extract potential mint addresses from transaction log messages.
        
        Args:
            log_messages: List of log messages from the transaction
            
        Returns:
            Set[str]: Set of potential mint addresses found in logs
        """
        mint_addresses = set()
        try:
            for message in log_messages:
                # Look for common mint-related log patterns
                if any(pattern in message.lower() for pattern in [
                    "initialize mint",
                    "create mint",
                    "mint to",
                    "token program",
                    "associated token"
                ]):
                    # Extract potential addresses from the message
                    words = message.split()
                    for word in words:
                        if self._is_valid_mint_address(word):
                            mint_addresses.add(word)
                            logger.debug(f"Found potential mint address in logs: {word}")
                            
        except Exception as e:
            logger.error(f"Error extracting mints from logs: {str(e)}")
            self.stats['errors']['log_extraction_error'] += 1
            
        return mint_addresses

    def _extract_program_metrics(self, log_messages: List[str]) -> Dict[str, Any]:
        """
        Extract program execution metrics from transaction logs.
        
        Args:
            log_messages: List of log messages from the transaction
            
        Returns:
            Dict containing program metrics including compute units and invocations
        """
        metrics = {
            'compute_units': {
                'total_consumed': 0,
                'by_program': defaultdict(int)
            },
            'program_invocations': defaultdict(int),
            'instruction_types': defaultdict(int)
        }
        
        current_program = None
        
        try:
            for message in log_messages:
                # Track program invocations
                if 'invoke [' in message:
                    program = message.split('Program ')[1].split(' invoke')[0]
                    current_program = program
                    metrics['program_invocations'][program] += 1
                    
                # Track instruction types
                elif 'Instruction:' in message:
                    instruction = message.split('Instruction: ')[1]
                    if current_program:
                        metrics['instruction_types'][f"{current_program}:{instruction}"] += 1
                        
                # Track compute units
                elif 'consumed' in message and 'compute units' in message:
                    try:
                        consumed = int(message.split('consumed ')[1].split(' of ')[0])
                        if current_program:
                            metrics['compute_units']['by_program'][current_program] += consumed
                            metrics['compute_units']['total_consumed'] += consumed
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Error parsing compute units: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Error extracting program metrics: {str(e)}")
            self.stats['errors']['program_metrics_error'] += 1
            
        return metrics
        
    def _analyze_token_program_activity(self, log_messages: List[str], token_balances: List[Dict]) -> Dict[str, Any]:
        """
        Analyze token program activity to detect mint-related operations.
        
        Args:
            log_messages: List of log messages from the transaction
            token_balances: List of pre/post token balance changes
            
        Returns:
            Dict containing token program analysis results
        """
        analysis = {
            'mint_operations': [],
            'token_transfers': [],
            'account_operations': []
        }
        
        try:
            for message in log_messages:
                if 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA' in message:
                    if 'InitializeMint' in message:
                        # Extract mint initialization details
                        analysis['mint_operations'].append({
                            'type': 'initialize',
                            'program': 'token',
                            'timestamp': time.time()
                        })
                    elif 'MintTo' in message:
                        # Track mint-to operations
                        analysis['mint_operations'].append({
                            'type': 'mint_to',
                            'program': 'token',
                            'timestamp': time.time()
                        })
                        
            # Analyze token balance changes
            if token_balances:
                for balance in token_balances:
                    if 'mint' in balance:
                        mint_address = balance.get('mint')
                        if self._is_valid_mint_address(mint_address):
                            analysis['token_transfers'].append({
                                'mint': mint_address,
                                'owner': balance.get('owner'),
                                'amount': balance.get('uiTokenAmount', {}).get('uiAmount')
                            })
                            
        except Exception as e:
            logger.error(f"Error analyzing token program activity: {str(e)}")
            self.stats['errors']['token_analysis_error'] += 1
            
        return analysis

class NewMintAnalyzer:
    """Analyzes blocks for new mint addresses"""
    
    def __init__(self):
        self.mint_handler = MintHandler()
        
        # Initialize response handler with config
        response_manager = SolanaResponseManager(endpoint_config)
        self.response_handler = NewMintsResponseHandler(response_manager=response_manager)
        
    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block to find new mint addresses"""
        try:
            if not block_data or not isinstance(block_data, dict):
                return {"success": False, "error": "Invalid block data"}
                
            # Use the mint handler to process the block
            result = self.mint_handler.handle_block(block_data)
            
            # Format the response
            return {
                "success": True,
                "block_number": block_data.get("parentSlot", 0) + 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mint_addresses": list(self.mint_handler.mint_addresses),
                "errors": self.mint_handler.errors
            }
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            return {"success": False, "error": str(e)}

async def get_query_handler() -> SolanaQueryHandler:
    """Get or create query handler with proper response handler"""
    try:
        # Create response manager with config
        response_manager = SolanaResponseManager(endpoint_config)
        
        # Create new mints response handler with manager
        response_handler = NewMintsResponseHandler(response_manager=response_manager)
        
        # Initialize query handler with our response handler
        query_handler = SolanaQueryHandler(response_handler=response_handler)
        await query_handler.initialize()
        
        return query_handler
        
    except Exception as e:
        logger.error(f"Failed to initialize query handler: {str(e)}")
        raise

async def extract_new_mints(
    start_block: Optional[int] = None,
    end_block: Optional[int] = None,
    batch_size: int = 10
) -> Dict[str, Any]:
    """Extract new mint addresses from specified blocks"""
    try:
        # Get query handler
        query_handler = await get_query_handler()
        if not query_handler:
            return {"error": "Failed to initialize query handler"}
            
        # Get current block
        current_block = await get_current_block()
        if not current_block:
            return {"error": "Failed to get current block"}
            
        # Initialize analyzer
        analyzer = NewMintAnalyzer()
        
        # Process blocks with mint response handler
        results = await query_handler.process_blocks(
            num_blocks=end_block - start_block + 1,
            start_slot=start_block,    # Lower slot (older)
            end_slot=end_block,        # Higher slot (newer)
            handlers=[analyzer.response_handler],  # Use analyzer's response handler
            batch_size=batch_size
        )
        
        # Extract new mints from results
        new_mints = []
        if results.get("success", False):
            for handler_name, handler_result in results.items():
                if handler_name not in ("success", "processed_blocks", "total_blocks", "start_slot", "end_slot", "errors"):
                    if isinstance(handler_result, dict) and "mint_addresses" in handler_result:
                        new_mints.extend(handler_result["mint_addresses"])
        
        return {
            "success": True,
            "start_block": results.get("start_slot"),
            "end_block": results.get("end_slot"),
            "blocks_processed": results.get("processed_blocks", 0),
            "blocks_failed": len(results.get("errors", [])),
            "new_mints": new_mints,
            "stats": {
                "total_blocks_analyzed": results.get("processed_blocks", 0),
                "total_new_mints": len(new_mints),
                "success_rate": results.get("processed_blocks", 0) / (end_block - start_block + 1) if end_block - start_block + 1 > 0 else 0
            },
            "errors": results.get("errors", [])
        }
        
    except Exception as e:
        logger.error(f"Error extracting new mints: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/recent")
async def get_recent_new_mints(
    blocks: int = Query(
        default=5,
        description="Number of recent blocks to analyze",
        ge=1,
        le=20
    )
) -> Dict[str, Any]:
    """
    Get newly created mint addresses from recent blocks
    
    Args:
        blocks: Number of recent blocks to analyze (default: 5)
        
    Returns:
        Dict containing new mint addresses and analysis
    """
    try:
        # Get query handler
        query_handler = await get_query_handler()
        
        # Get latest block
        latest_block_resp = await query_handler.get_latest_block()
        if not latest_block_resp or not isinstance(latest_block_resp, dict):
            logger.error("Failed to get latest block")
            return {"success": False, "error": "Failed to get latest block"}

        # Extract slot
        latest_block = latest_block_resp.get("slot")
        if latest_block is None:
            logger.error("Invalid block response format: missing slot")
            return {"success": False, "error": "Invalid block response format: missing slot"}

        # Calculate block range
        start_block = latest_block
        end_block = max(0, start_block - blocks + 1)

        logger.info(f"Analyzing blocks from {start_block} (newer) to {end_block} (older)")
        
        # Process blocks
        results = []
        total_stats = {
            "total_transactions": 0,
            "total_programs": set(),
            "total_instructions": 0,
            "total_mints": 0,
            "blocks_processed": 0,
            "start_time": int(time.time())
        }
        
        for slot in range(start_block, end_block - 1, -1):
            try:
                # Get block data
                block_data = await query_handler.get_block(slot)
                if not block_data:
                    raise HTTPException(status_code=500, detail=f"Failed to get block {slot}")
                    
                # Process block
                result = await query_handler.process_block(block_data)
                if result and result.get("success"):
                    results.append(result)
                    
                    # Update statistics
                    stats = result.get("statistics", {})
                    total_stats["total_transactions"] += stats.get("total_transactions", 0)
                    total_stats["total_instructions"] += stats.get("total_instructions", 0)
                    total_stats["total_programs"].update(stats.get("total_programs", []))
                    total_stats["total_mints"] += stats.get("total_mints", 0)
                    total_stats["blocks_processed"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing block {slot}: {str(e)}")
                continue
                
        # Calculate processing duration
        total_stats["duration_seconds"] = int(time.time()) - total_stats["start_time"]
        
        # Log summary statistics
        logger.info("\nProcessing Summary:")
        logger.info(f"  Blocks Processed: {total_stats['blocks_processed']}/{blocks}")
        logger.info(f"  Total Transactions: {total_stats['total_transactions']}")
        logger.info(f"  Total Instructions: {total_stats['total_instructions']}")
        logger.info(f"  Total Programs: {len(total_stats['total_programs'])}")
        logger.info(f"  New Mints Found: {total_stats['total_mints']}")
        logger.info(f"  Processing Time: {total_stats['duration_seconds']}s")
        
        return {
            "success": True,
            "results": results,
            "statistics": total_stats,
            "block_range": {
                "start": start_block,
                "end": end_block,
                "requested": blocks
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_recent_new_mints: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitor")
async def monitor_new_mints(
    interval: int = Query(
        default=60,
        description="Monitoring interval in seconds",
        ge=10,
        le=300
    ),
    duration: int = Query(
        default=3600,
        description="Total monitoring duration in seconds",
        ge=60,
        le=86400
    )
) -> Dict[str, Any]:
    """
    Monitor for new mint addresses over a specified duration
    
    Args:
        interval: Seconds between each check (10-300)
        duration: Total monitoring duration in seconds (60-86400)
        
    Returns:
        Dict containing monitored new mint addresses and statistics
    """
    query_handler = await get_query_handler()
    if not query_handler:
        raise HTTPException(
            status_code=503,
            detail="Failed to initialize Solana connection"
        )
        
    try:
        analyzer = NewMintAnalyzer()
        start_time = time.time()
        end_time = start_time + duration
        
        monitored_mints = []
        last_block = None
        
        while time.time() < end_time:
            try:
                # Get latest block
                client = await query_handler.connection_pool.get_client()
                current_block = await client.get_block_height()
                
                if current_block and (last_block is None or current_block > last_block):
                    # Process new blocks
                    start_block = last_block + 1 if last_block else current_block
                    
                    results = await query_handler.process_blocks(
                        num_blocks=current_block - start_block + 1,
                        start_slot=start_block,    # Lower slot (older)
                        end_slot=current_block,    # Higher slot (newer)
                        handlers=[analyzer.response_handler],  # Use analyzer's response handler
                        batch_size=5
                    )
                    
                    # Process results
                    new_mints = []
                    if results.get("success", False):
                        for handler_name, handler_result in results.items():
                            if handler_name not in ("success", "processed_blocks", "total_blocks", "start_slot", "end_slot", "errors"):
                                if isinstance(handler_result, dict) and "mint_addresses" in handler_result:
                                    new_mints.extend(handler_result["mint_addresses"])
                    
                    monitored_mints.extend(new_mints)
                    
                    last_block = current_block
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                
            # Wait for next interval
            remaining_time = end_time - time.time()
            if remaining_time > 0:
                await asyncio.sleep(min(interval, remaining_time))
            else:
                break
                
        # Sort monitored mints by block time (newest first)
        monitored_mints.sort(key=lambda x: x.get("block_time", 0), reverse=True)
        
        return {
            "success": True,
            "monitoring_duration": duration,
            "actual_duration": int(time.time() - start_time),
            "new_mints": monitored_mints,
            "stats": {
                "total_blocks_analyzed": 0,
                "total_new_mints": len(monitored_mints),
                "total_pump_tokens": 0,
                "mints_per_minute": (len(monitored_mints) * 60) / duration
            },
            "errors": []
        }
        
    except Exception as e:
        logger.error(f"Error in mint monitoring: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Internal server error in mint monitoring: {str(e)}"
        )

class NewMintsResponseHandler(BaseHandler):
    """Handler for new mints responses"""
    
    def __init__(self, response_manager: SolanaResponseManager):
        """Initialize with response manager"""
        super().__init__()  # Call BaseHandler's init without args
        self.response_manager = response_manager
        self.stats = TransactionStats()
        self.SYSTEM_PROGRAM_IDS = {
            'So11111111111111111111111111111111111111112',  # Wrapped SOL
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
            'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',  # Associated Token Program
            'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',  # Token Program 2022
            '11111111111111111111111111111111',  # System Program
            'ComputeBudget111111111111111111111111111111',  # Compute Budget
            'Vote111111111111111111111111111111111111111',  # Vote Program
            'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr',  # Memo Program
        }
        
    async def process_result(self, result: Any) -> Dict[str, Any]:
        """
        Process block result and extract mint addresses with enhanced error handling and logging.
        
        Args:
            result: Block data from Solana RPC
            
        Returns:
            Dict containing processed results and statistics
        """
        start_time = time.time()
        stats = self._get_empty_stats()
        
        try:
            if not result or not isinstance(result, dict):
                logger.error("Invalid block result format")
                stats["invalid_tx_formats"] += 1
                return stats
                
            transactions = result.get("transactions", [])
            if not transactions:
                logger.debug("No transactions in block")
                return stats
                
            # Get block timestamp
            block_timestamp = self._get_block_timestamp(result)
            stats["timestamp"] = block_timestamp
            
            # Process each transaction
            for tx_index, tx in enumerate(transactions):
                try:
                    # Skip vote transactions early
                    if self._is_vote_transaction(tx):
                        continue
                        
                    # Process transaction and update stats
                    tx_stats = self._process_transaction(tx, tx_index)
                    
                    # Update block statistics
                    stats["total_transactions"] += 1
                    stats["total_instructions"] += tx_stats.get("instruction_count", 0)
                    stats["token_program_txs"] += tx_stats.get("token_program_calls", 0)
                    stats["new_mints"] += tx_stats.get("new_mints", 0)
                    
                    # Track errors
                    if tx_stats.get("errors"):
                        stats["transaction_errors"] += 1
                        stats["error_details"].extend(tx_stats["errors"])
                        
                    # Update program statistics
                    for program_id in tx_stats.get("programs_called", set()):
                        stats["programs_called"].add(program_id)
                        
                except Exception as e:
                    logger.error(f"Error processing transaction {tx_index}: {str(e)}", exc_info=True)
                    stats["transaction_errors"] += 1
                    stats["error_details"].append({
                        "type": "transaction_processing_error",
                        "index": tx_index,
                        "error": str(e)
                    })
                    
            # Calculate processing duration
            stats["processing_duration_ms"] = int((time.time() - start_time) * 1000)
            
            # Log summary statistics
            logger.info(
                f"Block processing complete:\n"
                f"Total transactions: {stats['total_transactions']}\n"
                f"New mints found: {stats['new_mints']}\n"
                f"Errors: {stats['transaction_errors']}\n"
                f"Duration: {stats['processing_duration_ms']}ms"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error processing block result: {str(e)}", exc_info=True)
            stats["error_details"].append({
                "type": "block_processing_error",
                "error": str(e)
            })
            return stats
            
    def _process_transaction(self, tx: Dict[str, Any], tx_index: int) -> Dict[str, Any]:
        """
        Process a transaction to extract mint addresses with detailed tracking.
        
        Args:
            tx: Transaction data
            tx_index: Index of transaction in block
            
        Returns:
            Dict containing transaction statistics and found mint addresses
        """
        stats = {
            "instruction_count": 0,
            "token_program_calls": 0,
            "new_mints": 0,
            "programs_called": set(),
            "errors": []
        }
        
        try:
            # Get transaction data
            if not tx or not isinstance(tx, dict):
                logger.debug(f"Invalid transaction format at index {tx_index}")
                return stats
                
            # Skip failed transactions
            meta = tx.get("meta", {})
            if meta.get("err") is not None:
                logger.debug(f"Skipping failed transaction at index {tx_index}")
                return stats
                
            # Process transaction message
            message = tx.get("transaction", {}).get("message", {})
            if not message:
                logger.debug(f"No message in transaction at index {tx_index}")
                return stats
                
            # Get account keys
            account_keys = message.get("accountKeys", [])
            if not account_keys:
                logger.debug(f"No account keys in transaction at index {tx_index}")
                return stats
                
            # Process instructions
            instructions = message.get("instructions", [])
            stats["instruction_count"] = len(instructions)
            
            for ix in instructions:
                try:
                    # Track program calls
                    program_id = ix.get("programId")
                    if program_id:
                        stats["programs_called"].add(str(program_id))
                        
                    # Check for token program usage
                    if program_id in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID, METADATA_PROGRAM_ID]:
                        stats["token_program_calls"] += 1
                        
                    # Extract mint addresses
                    mint_address = self._extract_mint_address(ix, account_keys)
                    if mint_address:
                        stats["new_mints"] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing instruction in tx {tx_index}: {str(e)}")
                    stats["errors"].append({
                        "type": "instruction_processing_error",
                        "tx_index": tx_index,
                        "error": str(e)
                    })
                    
            # Process inner instructions
            inner_instructions = meta.get("innerInstructions", [])
            for inner_ix_group in inner_instructions:
                for inner_ix in inner_ix_group.get("instructions", []):
                    try:
                        stats["instruction_count"] += 1
                        program_id = inner_ix.get("programId")
                        if program_id:
                            stats["programs_called"].add(str(program_id))
                            
                        # Check for token program usage
                        if program_id in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID, METADATA_PROGRAM_ID]:
                            stats["token_program_calls"] += 1
                            
                        # Extract mint addresses
                        mint_address = self._extract_mint_address(inner_ix, account_keys)
                        if mint_address:
                            stats["new_mints"] += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing inner instruction in tx {tx_index}: {str(e)}")
                        stats["errors"].append({
                            "type": "inner_instruction_processing_error",
                            "tx_index": tx_index,
                            "error": str(e)
                        })
                        
            # Process token balances
            pre_balances = meta.get("preTokenBalances", [])
            post_balances = meta.get("postTokenBalances", [])
            if pre_balances and post_balances:
                self._process_token_balances(pre_balances, post_balances, tx_index)
                
            return stats
            
        except Exception as e:
            logger.error(f"Error in transaction processing: {str(e)}", exc_info=True)
            stats["errors"].append({
                "type": "transaction_processing_error",
                "tx_index": tx_index,
                "error": str(e)
            })
            return stats
            
    def _is_vote_transaction(self, tx: Dict[str, Any]) -> bool:
        """Check if transaction is a vote transaction to skip processing"""
        try:
            message = tx.get("transaction", {}).get("message", {})
            if not message:
                return False
                
            # Check program ID in first instruction
            instructions = message.get("instructions", [])
            if not instructions:
                return False
                
            first_ix = instructions[0]
            program_id = first_ix.get("programId")
            
            return program_id == "Vote111111111111111111111111111111111111111"
            
        except Exception as e:
            logger.debug(f"Error checking vote transaction: {str(e)}")
            return False

    def _get_mint_statistics(self) -> Dict[str, Any]:
        """
        Generate comprehensive statistics about mint activity.
        
        Returns:
            Dict containing mint statistics and metrics
        """
        stats = {
            'total_unique_mints': len(self.stats['mint_activity']),
            'active_mints': 0,  # Mints with recent activity
            'activity_by_type': defaultdict(int),
            'hourly_activity': defaultdict(int)
        }
        
        current_time = time.time()
        try:
            for mint_address, activity in self.stats['mint_activity'].items():
                # Count recently active mints (last hour)
                if current_time - activity['last_seen'] < 3600:
                    stats['active_mints'] += 1
                    
                # Aggregate activity types
                for act in activity['activities']:
                    stats['activity_by_type'][act['type']] += 1
                    
                    # Track hourly activity
                    hour = int(act['timestamp'] / 3600)
                    stats['hourly_activity'][hour] += 1
                    
        except Exception as e:
            logger.error(f"Error generating mint statistics: {str(e)}")
            self.stats['errors']['stats_generation_error'] += 1
            
        return stats

    def _is_token_program(self, instruction: Dict[str, Any], account_keys: List[str]) -> bool:
        """Check if instruction uses token program"""
        try:
            program_idx = instruction.get('programIdIndex')
            if program_idx is not None and program_idx < len(account_keys):
                program_id = account_keys[program_idx]
                return program_id == 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
                
            logger.debug("No token program found in transaction")
            return False
            
        except Exception as e:
            logger.debug(f"Error checking token program: {str(e)}")
            return False

    def _process_transaction(self, tx: Dict[str, Any], tx_index: int) -> List[str]:
        """Process a transaction to extract mint addresses"""
        found_mints = []
        try:
            # Skip if no transaction data
            if not tx or not isinstance(tx, dict):
                return found_mints
                
            # Get transaction and meta data
            transaction = tx.get('transaction', {})
            meta = tx.get('meta', {})
            
            if not transaction or not meta:
                return found_mints
                
            # Check if transaction failed
            if meta.get('err') is not None:
                return found_mints
                
            # Get message data
            message = transaction.get('message', {})
            if not message:
                return found_mints
                
            # Get account keys
            account_keys = []
            raw_keys = message.get('accountKeys', [])
            for key in raw_keys:
                if isinstance(key, dict):
                    account_keys.append(key.get('pubkey'))
                else:
                    account_keys.append(str(key))
                    
            if not account_keys:
                return found_mints
                
            # Process instructions
            instructions = message.get('instructions', [])
            for instruction in instructions:
                # Skip if instruction is empty
                if not instruction:
                    continue
                    
                # Get program ID
                program_id = None
                if isinstance(instruction, dict):
                    if 'programId' in instruction:
                        program_id = instruction['programId']
                    elif 'programIdIndex' in instruction:
                        idx = instruction['programIdIndex']
                        if isinstance(idx, int) and idx < len(account_keys):
                            program_id = account_keys[idx]
                            
                if not program_id:
                    continue
                    
                # Convert program ID to string
                program_id = str(program_id)
                
                # Skip if not a relevant program
                if program_id not in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID, 
                                    METADATA_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID]:
                    continue
                    
                # Extract mints from instruction
                instruction_mints = self._extract_mints_from_instruction(instruction, account_keys, tx_index)
                found_mints.extend(instruction_mints)
                
            # Process inner instructions
            inner_instructions = meta.get('innerInstructions', [])
            for inner_group in inner_instructions:
                for inner_ix in inner_group.get('instructions', []):
                    instruction_mints = self._extract_mints_from_instruction(inner_ix, account_keys, tx_index)
                    found_mints.extend(instruction_mints)
                    
            # Process token balances for additional mint addresses
            for balance in meta.get('preTokenBalances', []) + meta.get('postTokenBalances', []):
                mint = balance.get('mint')
                if mint and self._is_valid_mint_address(mint):
                    found_mints.append(mint)
                    logger.info(f"Found mint in token balances: {mint}")
                    
        except Exception as e:
            logger.error(f"Error processing transaction {tx_index}: {str(e)}")
            self.stats['errors']['transaction_processing_error'] += 1
            
        # Remove duplicates while preserving order
        return list(dict.fromkeys(found_mints))  # Remove duplicates
        
    def _extract_mint_address(self, instruction: Dict[str, Any], account_keys: List[str]) -> Optional[str]:
        """
        Extract mint address from instruction with enhanced validation and logging.
        Handles multiple mint creation patterns and program types.
        
        Args:
            instruction: The instruction to analyze
            account_keys: List of account keys involved
            
        Returns:
            Optional[str]: The extracted mint address if found and valid
        """
        try:
            # Log instruction for debugging
            logger.debug(f"Extracting mint address from instruction: {json.dumps(instruction, indent=2)}")
            logger.debug(f"Account keys: {json.dumps(account_keys, indent=2)}")
            
            # Get program ID and accounts
            program_id = instruction.get("programId")
            if not program_id:
                logger.debug("No program ID found")
                return None
                
            program_id = str(program_id)
            accounts = instruction.get("accounts", [])
            
            if not program_id or not accounts:
                logger.debug("Missing program ID or accounts")
                return None
                
            # Handle different program types
            if program_id in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                return self._extract_token_mint_address(instruction, accounts, account_keys)
            elif program_id == METADATA_PROGRAM_ID:
                return self._extract_metadata_mint_address(instruction, accounts, account_keys)
            elif program_id == ASSOCIATED_TOKEN_PROGRAM_ID:
                return self._extract_ata_mint_address(instruction, accounts, account_keys)
                
            # Check other known mint creation programs
            elif program_id in MINT_CREATION_PROGRAMS:
                # Extract potential mint address from accounts
                for account_idx in accounts:
                    if isinstance(account_idx, int) and account_idx < len(account_keys):
                        potential_mint = account_keys[account_idx]
                        if self._is_valid_mint_address(potential_mint):
                            logger.info(f"Found potential mint address from program {program_id}: {potential_mint}")
                            return potential_mint
                            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting mint address: {str(e)}", exc_info=True)
            return None
            
    def _extract_token_mint_address(self, instruction: Dict[str, Any], accounts: List[Any], account_keys: List[str]) -> Optional[str]:
        """Extract mint address from token program instruction"""
        try:
            # For Token/Token-2022 InitializeMint:
            # accounts[0] = mint account being initialized
            # accounts[1] = rent sysvar
            if not accounts:
                logger.debug("No accounts in token instruction")
                return None
                
            # Get mint account index
            mint_idx = accounts[0]
            if isinstance(mint_idx, int) and mint_idx < len(account_keys):
                mint_address = account_keys[mint_idx]
                if isinstance(mint_address, dict):
                    return mint_address.get("pubkey")
                return str(mint_address)
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting token mint address: {str(e)}")
            return None
            
    def _extract_metadata_mint_address(self, instruction: Dict[str, Any], accounts: List[Any], account_keys: List[str]) -> Optional[str]:
        """Extract mint address from metadata program instruction"""
        try:
            # For Metadata instructions:
            # CreateMetadata/CreateMasterEdition:
            # accounts[0] = metadata account
            # accounts[1] = mint account
            if len(accounts) < 2:
                logger.debug("Not enough accounts in metadata instruction")
                return None
                
            # Get mint account index
            mint_idx = accounts[1]
            if isinstance(mint_idx, int) and mint_idx < len(account_keys):
                mint_address = account_keys[mint_idx]
                if isinstance(mint_address, dict):
                    return mint_address.get("pubkey")
                return str(mint_address)
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting metadata mint address: {str(e)}")
            return None
            
    def _extract_ata_mint_address(self, instruction: Dict[str, Any], accounts: List[Any], account_keys: List[str]) -> Optional[str]:
        """Extract mint address from associated token account instruction"""
        try:
            # For Associated Token Account Creation:
            # accounts[0] = associated token account
            # accounts[1] = wallet
            # accounts[2] = mint account
            if len(accounts) < 3:
                logger.debug("Not enough accounts in ATA instruction")
                return None
                
            # Get mint account index
            mint_idx = accounts[2]
            if isinstance(mint_idx, int) and mint_idx < len(account_keys):
                mint_address = account_keys[mint_idx]
                if isinstance(mint_address, dict):
                    return mint_address.get("pubkey")
                return str(mint_address)
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting ATA mint address: {str(e)}")
            return None
