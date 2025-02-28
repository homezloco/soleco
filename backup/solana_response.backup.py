"""
Main interface for Solana response handling.
Provides a clean public interface for the modularized codebase.
"""

import logging
import asyncio
import time
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass
from collections import defaultdict

from solders.rpc.responses import GetBlockResp
from solana.rpc.async_api import AsyncClient

from .base_handler import (
    BaseResponseHandler,
    NodeBehindError,
    SlotSkippedError,
    MissingBlocksError,
    NodeUnhealthyError
)
from .rate_limiter import RateLimiter, RateLimitConfig, RateLimitError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Public exports
__all__ = [
    'SolanaResponseManager',
    'MintResponseHandler',
    'NodeBehindError',
    'SlotSkippedError',
    'MissingBlocksError',
    'NodeUnhealthyError',
    'RateLimitError'
]

@dataclass
class EndpointConfig:
    """Configuration for RPC endpoint."""
    url: str
    requests_per_second: float = 40.0
    burst_limit: int = 80
    max_retries: int = 3
    retry_delay: float = 1.0

class SolanaResponseManager:
    """
    Main interface for handling Solana RPC responses.
    Coordinates between different handlers and manages rate limiting.
    """

    def __init__(self, config: EndpointConfig):
        """
        Initialize Solana response manager.
        
        Args:
            config: Endpoint configuration
        """
        self.config = config
        self.client = AsyncClient(config.url)
        
        # Initialize handlers
        self.base_handler = BaseResponseHandler()
        self.mint_handler = MintResponseHandler()
        
        # Configure rate limiter
        rate_limit_config = RateLimitConfig(
            requests_per_second=config.requests_per_second,
            burst_limit=config.burst_limit
        )
        self.rate_limiter = RateLimiter(rate_limit_config)
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retried_requests": 0
        }

    async def process_response(self, 
                             response: Any,
                             response_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Process an RPC response using appropriate handler.
        
        Args:
            response: Raw RPC response
            response_type: Type of response to process ('mint', etc)
            
        Returns:
            Processed response data
        """
        try:
            # Check rate limits
            await self.rate_limiter.acquire()
            
            self._stats["total_requests"] += 1
            
            # Handle based on response type
            if response_type == "mint":
                result = self.mint_handler.handle_response(response)
            else:
                result = self.base_handler.handle_response(response)
                
            if "error" not in result:
                self._stats["successful_requests"] += 1
            else:
                self._stats["failed_requests"] += 1
                
            return result
            
        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            self._stats["failed_requests"] += 1
            raise

    async def process_block(self, block_data: Union[Dict[str, Any], GetBlockResp]) -> Dict[str, Any]:
        """
        Process block data to extract transaction information.
        
        Args:
            block_data: Block data from RPC response
            
        Returns:
            Processed block information
        """
        try:
            # Convert GetBlockResp to dict if needed
            if isinstance(block_data, GetBlockResp):
                block_data = block_data.to_json()
                
            if not isinstance(block_data, dict):
                raise ValueError("Invalid block data format")
                
            # Extract transactions
            transactions = block_data.get("transactions", [])
            results = []
            
            for tx_data in transactions:
                try:
                    await self.rate_limiter.acquire()
                    result = self.mint_handler.handle_transaction(tx_data)
                    if result:
                        results.append(result)
                except RateLimitError:
                    logger.warning("Rate limit reached during block processing")
                    break
                    
            return {
                "success": True,
                "transactions_processed": len(results),
                "results": results,
                "mint_stats": self.mint_handler.get_stats()
            }
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def retry_with_backoff(self, 
                               operation: Any,
                               *args,
                               **kwargs) -> Any:
        """
        Retry an operation with exponential backoff.
        
        Args:
            operation: Async function to retry
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Operation result
        """
        retries = 0
        last_error = None
        
        while retries < self.config.max_retries:
            try:
                return await operation(*args, **kwargs)
            except (NodeBehindError, NodeUnhealthyError) as e:
                last_error = e
                retries += 1
                self._stats["retried_requests"] += 1
                
                if retries < self.config.max_retries:
                    delay = self.config.retry_delay * (2 ** retries)
                    logger.warning(f"Retrying after {delay}s due to {str(e)}")
                    await asyncio.sleep(delay)
                    
        logger.error(f"Max retries reached: {str(last_error)}")
        raise last_error

    @property
    def stats(self) -> Dict[str, Any]:
        """Get combined statistics from all handlers."""
        return {
            **self._stats,
            "rate_limiter": self.rate_limiter.stats,
            "base_handler": self.base_handler.stats,
            "mint_handler": self.mint_handler.get_stats()
        }

    def reset_stats(self) -> None:
        """Reset statistics for all handlers."""
        self._stats = {key: 0 for key in self._stats}
        self.rate_limiter.reset_stats()
        self.base_handler.reset_stats()
        self.mint_handler.reset_stats()

    async def close(self) -> None:
        """Clean up resources."""
        await self.client.close()

class MintResponseHandler:
    """Handler for processing mint-related responses from Solana transactions"""
    
    def __init__(self):
        """Initialize the MintResponseHandler"""
        # System and program addresses
        self.SYSTEM_ADDRESSES = {
            'system_program': 'Sys1111111111111111111111111111111111111111',
            'token_program': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
            'token2022_program': 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',
            'associated_token': 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',
            'metadata_program': 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'
        }
        
        self.PROGRAM_ADDRESSES = {
            'Vote111111111111111111111111111111111111111',  # Vote Program
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
            'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',  # Token-2022
            'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s',  # Metadata Program
            'p1exdMJcjVao65QdewkaZRUnU6VPSXhus9n2GzWfh98',  # Metaplex Program
            'vau1zxA2LbssAUEF7Gpw91zMM1LvXrvpzJtmZ58rPsn',  # Metaplex Program v2
            'cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ',  # Candy Machine Program
            'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB',  # Jupiter v4
            'JUP6i4ozu5ydDCnLiMogSckDPpbtr7BJ4FtzYWkb5Rk'   # Jupiter v6
        }
        
        self.PROGRAM_TYPES = {
            'Vote111111111111111111111111111111111111111': 'vote',
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'token',
            'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb': 'token2022',
            'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s': 'metadata',
            'p1exdMJcjVao65QdewkaZRUnU6VPSXhus9n2GzWfh98': 'metaplex',
            'vau1zxA2LbssAUEF7Gpw91zMM1LvXrvpzJtmZ58rPsn': 'metaplex',
            'cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ': 'candy_machine',
            'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB': 'jupiter',
            'JUP6i4ozu5ydDCnLiMogSckDPpbtr7BJ4FtzYWkb5Rk': 'jupiter'
        }
        
        self.PROGRAM_IDS = {
            'token': ['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'],
            'token2022': ['TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'],
            'metadata': ['metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'],
            'jupiter': [
                'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB',
                'JUP6i4ozu5ydDCnLiMogSckDPpbtr7BJ4FtzYWkb5Rk'
            ]
        }
        
        # Initialize sets for tracking addresses
        self.mint_addresses: set[str] = set()
        self.pump_tokens: set[str] = set()
        self.processed_addresses: set[str] = set()
        self.errors: list[str] = []
        self.pump_token_stats: dict[str, dict[str, Any]] = {}
        self.transaction_history: dict[str, list[dict]] = {}
        self.time_based_metrics: dict[str, dict[str, Any]] = {}
        self.program_interactions: dict[str, dict[str, int]] = {}
        
        # Performance tracking
        self.performance_metrics = {
            "start_time": time.time(),
            "block_times": [],
            "transaction_times": [],
            "memory_samples": []
        }
        
        # Rate limit tracking
        self.rate_limits = {
            "hits": 0,
            "backoffs": 0,
            "cooldown_periods": 0,
            "total_delay_ms": 0,
            "rate_limit_stats": {
                "method_remaining": 40,
                "rps_remaining": 100,
                "conn_remaining": 40
            }
        }
        
        # Error tracking
        self.error_stats = {
            "total": 0,
            "by_type": defaultdict(int),
            "error_rates": {
                "total_error_rate": 0.0,
                "retryable_error_rate": 0.0,
                "fatal_error_rate": 0.0
            },
            "common_errors": []
        }
        
        # Configure logging
        self.logger = logging.getLogger("solana.response")

    def analyze_transaction_patterns(self, token_address: str) -> Dict[str, int]:
        """
        Analyze transaction patterns for a specific token
        
        Args:
            token_address: The token address to analyze
            
        Returns:
            Dict containing pattern counts
        """
        patterns = {
            "circular_transfers": 0,
            "self_transfers": 0,
            "large_transfers": 0,
            "rapid_transfers": 0
        }
        
        if token_address not in self.transaction_history:
            return patterns
            
        transactions = self.transaction_history[token_address]
        seen_addresses = set()
        last_transfer_time = 0
        
        for tx in transactions:
            # Check for self transfers
            if tx.get("from_address") == tx.get("to_address"):
                patterns["self_transfers"] += 1
                
            # Check for large transfers
            if tx.get("amount", 0) > self.pump_token_stats[token_address].get("avg_transfer_amount", 0) * 3:
                patterns["large_transfers"] += 1
                
            # Check for rapid transfers
            current_time = tx.get("timestamp", 0)
            if last_transfer_time > 0 and current_time - last_transfer_time < 10:  # Less than 10 seconds
                patterns["rapid_transfers"] += 1
            last_transfer_time = current_time
            
            # Track addresses for circular transfer detection
            if tx.get("from_address"):
                seen_addresses.add(tx.get("from_address"))
                
            # Check for circular transfers
            if tx.get("to_address") in seen_addresses:
                patterns["circular_transfers"] += 1
                
        return patterns

    def analyze_time_based_metrics(self, token_address: str) -> Dict[str, Any]:
        """
        Analyze time-based metrics for a specific token
        
        Args:
            token_address: The token address to analyze
            
        Returns:
            Dict containing time-based metrics
        """
        metrics = {
            "hourly_volume": [],
            "hourly_transactions": [],
            "peak_activity_hours": [],
            "inactive_periods": []
        }
        
        if token_address not in self.transaction_history:
            return metrics
            
        transactions = self.transaction_history[token_address]
        hourly_data = defaultdict(lambda: {"volume": 0.0, "count": 0})
        
        # Process transactions by hour
        for tx in transactions:
            hour = int(tx.get("timestamp", 0) / 3600)
            hourly_data[hour]["volume"] += tx.get("amount", 0)
            hourly_data[hour]["count"] += 1
        
        # Sort hours and calculate metrics
        sorted_hours = sorted(hourly_data.keys())
        if not sorted_hours:
            return metrics
            
        # Calculate hourly metrics
        for hour in sorted_hours:
            metrics["hourly_volume"].append(hourly_data[hour]["volume"])
            metrics["hourly_transactions"].append(hourly_data[hour]["count"])
            
            # Identify peak activity hours (top 10% by transaction count)
            if hourly_data[hour]["count"] > sum(metrics["hourly_transactions"]) / len(metrics["hourly_transactions"]) * 1.5:
                metrics["peak_activity_hours"].append(hour)
                
        # Find inactive periods (gaps > 1 hour)
        for i in range(len(sorted_hours) - 1):
            gap = sorted_hours[i + 1] - sorted_hours[i]
            if gap > 1:
                metrics["inactive_periods"].append({
                    "start": sorted_hours[i],
                    "end": sorted_hours[i + 1],
                    "duration": gap
                })
                
        return metrics

    def get_pump_tokens_with_stats(self) -> List[Dict[str, Any]]:
        """
        Get pump tokens with their associated statistics
        
        Returns:
            List of dicts containing pump tokens and detailed statistics
        """
        result = []
        for token in self.pump_tokens:
            if token not in self.pump_token_stats:
                continue
                
            stats = self.pump_token_stats[token]
            
            # Calculate growth rates
            time_range = stats.get("last_seen", 0) - stats.get("first_seen", 0)
            if time_range > 0:
                holder_growth_rate = stats.get("holder_count", 0) / (time_range / 3600)  # Per hour
                volume_growth_rate = stats.get("total_volume", 0) / (time_range / 3600)  # Per hour
            else:
                holder_growth_rate = 0
                volume_growth_rate = 0
                
            # Calculate transactions per hour
            transactions_per_hour = stats.get("transaction_count", 0) / (time_range / 3600) if time_range > 0 else 0
            
            token_data = {
                "address": token,
                "first_seen": stats.get("first_seen", 0),
                "last_seen": stats.get("last_seen", 0),
                "transaction_count": stats.get("transaction_count", 0),
                "mint_operations": stats.get("mint_operations", 0),
                "transfer_operations": stats.get("transfer_operations", 0),
                "holder_count": stats.get("holder_count", 0),
                "total_volume": stats.get("total_volume", 0),
                "confidence_score": stats.get("confidence_score", 0),
                "activity_metrics": {
                    "unique_senders": len(stats.get("unique_senders", set())),
                    "unique_receivers": len(stats.get("unique_receivers", set())),
                    "avg_transfer_amount": stats.get("avg_transfer_amount", 0),
                    "max_transfer_amount": stats.get("max_transfer_amount", 0),
                    "initial_mint_amount": stats.get("initial_mint_amount", 0),
                    "transactions_per_hour": transactions_per_hour,
                    "holder_growth_rate": holder_growth_rate,
                    "volume_growth_rate": volume_growth_rate
                },
                "transaction_patterns": self.analyze_transaction_patterns(token),
                "program_interactions": self.program_interactions.get(token, {}),
                "activity_intervals": stats.get("activity_intervals", []),
                "time_based_metrics": self.analyze_time_based_metrics(token)
            }
            
            result.append(token_data)
            
        return result

    def handle_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a raw RPC response"""
        if not response or "result" not in response:
            return self._create_response()
            
        result = response["result"]
        return self.handle_block(result)

    def handle_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process block data and extract mint information"""
        if not block_data:
            return self._create_response()

        # Extract transactions from block
        transactions = block_data.get("transactions", [])
        if transactions:
            for tx_data in transactions:
                self.handle_transaction(tx_data)

        return self._create_response()

    def handle_transaction(self, tx_data: Any) -> Dict[str, Any]:
        """Process a transaction to extract mint addresses and related info
        
        Args:
            tx_data: Transaction data from RPC response
            
        Returns:
            Dict containing mint addresses and transaction details
        """
        # Initialize/reset state for this transaction
        self._init_response_data()
        
        try:
            logger.debug("Starting transaction processing")
            
            # Get message data - it should already be properly structured from extract_mints_from_block
            message = None
            meta = {}
            
            if isinstance(tx_data, dict):
                # Try to get message from various locations in dict
                message = tx_data.get("message")
                meta = tx_data.get("meta", {})
                
                if not message and "transaction" in tx_data:
                    # Try to get message from transaction object if it exists
                    transaction = tx_data.get("transaction", {})
                    if isinstance(transaction, dict):
                        message = transaction.get("message")
                        meta = transaction.get("meta", {})
                        logger.debug(f"Found message in transaction object, meta keys: {meta.keys() if meta else 'None'}")
            elif isinstance(tx_data, (list, tuple)):
                # Handle list/tuple format - assume first element is the message
                message = tx_data[0] if tx_data else None
                logger.debug("Processing list/tuple format transaction")
            else:
                # Handle non-dict objects (e.g. Solders objects)
                message = getattr(tx_data, "message", None)
                meta = getattr(tx_data, "meta", None)
                logger.debug(f"Processing non-dict transaction, type: {type(tx_data)}")
        
            if not message:
                logger.debug(f"No message data found in handle_transaction. Data type: {type(tx_data)}")
                return
                
            logger.debug(f"Transaction message type: {type(message)}")
            
            # Get account keys
            account_keys = []
            if isinstance(message, dict):
                account_keys = message.get("accountKeys", [])
                if not account_keys and 'accounts' in message:
                    # Some formats use 'accounts' instead of 'accountKeys'
                    account_keys = message.get('accounts', [])
            elif isinstance(message, (list, tuple)):
                # Handle list/tuple format - assume these are the account keys
                account_keys = message
            else:
                # Handle non-dict message (e.g. Solders objects)
                account_keys = getattr(message, "account_keys", [])
                if not account_keys:
                    # Try alternate attribute names
                    account_keys = getattr(message, "accounts", [])
        
            if not account_keys:
                logger.debug("No account keys found in message")
                return
                
            logger.debug(f"Found {len(account_keys)} account keys")
            
            # Process instructions
            instructions = []
            if isinstance(message, dict):
                instructions = message.get("instructions", [])
            elif isinstance(message, (list, tuple)):
                # Handle list/tuple format - assume second element contains instructions
                instructions = message[1] if len(message) > 1 else []
            else:
                # Handle non-dict message
                instructions = getattr(message, "instructions", [])
        
            if not instructions:
                logger.debug("No instructions found in message")
                return
                
            logger.debug(f"Processing {len(instructions)} instructions")
            
            # Process each instruction
            for idx, instruction in enumerate(instructions):
                logger.debug(f"Processing instruction {idx+1}/{len(instructions)}")
                self._process_instruction(instruction, account_keys)
        
            # Process token balances if available
            if isinstance(meta, dict):
                pre_token_balances = meta.get("preTokenBalances", [])
                post_token_balances = meta.get("postTokenBalances", [])
                
                if pre_token_balances:
                    logger.debug(f"Processing {len(pre_token_balances)} pre-token balances")
                    self._process_token_balances(pre_token_balances, 'pre')
                if post_token_balances:
                    logger.debug(f"Processing {len(post_token_balances)} post-token balances")
                    self._process_token_balances(post_token_balances, 'post')
        
            result = self._create_response()
            logger.debug(f"Transaction processing complete. Found mint addresses: {result.get('mint_addresses', [])}")
            return result
        
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}", exc_info=True)
            return self._create_response()

    def _init_response_data(self) -> None:
        """Initialize/reset response data for a new transaction"""
        # Reset transaction-specific data
        self.current_transaction = {
            'mint_addresses': set(),
            'pump_tokens': set(),
            'processed_addresses': set(),
            'errors': [],
            'program_ids': set(),
            'instruction_types': [],
            'transaction_type': 'unknown',
            'stats': {
                'total_instructions': 0,
                'total_accounts': 0,
                'total_signers': 0,
                'total_writable': 0
            }
        }
        
        # Log initialization
        logger.debug("Initialized response data for new transaction")

    def _process_instruction(self, instruction: Any, account_keys: List[str]) -> None:
        """Process a single instruction to extract mint addresses"""
        try:
            if not instruction or not account_keys:
                logger.debug("Skipping instruction processing - missing instruction or account keys")
                return

            # Extract program ID
            program_id = None
            if isinstance(instruction, dict):
                if 'programIdIndex' in instruction:
                    program_idx = instruction['programIdIndex']
                    if isinstance(program_idx, int) and program_idx < len(account_keys):
                        program_id = str(account_keys[program_idx])

            if not program_id:
                logger.debug("Could not extract program ID from instruction")
                return

            logger.debug(f"Processing instruction for program: {program_id}")

            # Process token program instructions
            if program_id in [self.SYSTEM_ADDRESSES['token_program'], self.SYSTEM_ADDRESSES['token2022_program']]:
                logger.debug(f"Found token program instruction: {program_id}")
                
                # Extract accounts
                accounts = []
                if isinstance(instruction, dict):
                    # Get accounts from instruction data
                    if 'accounts' in instruction:
                        accounts = instruction['accounts']
                    # Get accounts from parsed data
                    if 'parsed' in instruction:
                        parsed = instruction['parsed']
                        if isinstance(parsed, dict):
                            info = parsed.get('info', {})
                            # Check common fields that might contain mint addresses
                            mint_fields = ['mint', 'mintAuthority', 'tokenMint', 'mintAccount']
                            for field in mint_fields:
                                if field in info:
                                    addr = str(info[field])
                                    if self._is_valid_mint_address(addr):
                                        self._add_mint_address(addr, 'token_program_parsed')
                            
                            # Check account keys in info
                            if 'account' in info:
                                accounts.append(info['account'])
                            if 'source' in info:
                                accounts.append(info['source'])
                            if 'destination' in info:
                                accounts.append(info['destination'])

                # Process each account
                for account_idx in accounts:
                    if isinstance(account_idx, int) and account_idx < len(account_keys):
                        addr = str(account_keys[account_idx])
                        # Check if this could be a mint address
                        if self._is_valid_mint_address(addr):
                            self._add_mint_address(addr, 'token_program')

            # Process associated token program instructions
            elif program_id == self.SYSTEM_ADDRESSES['associated_token']:
                logger.debug("Found associated token program instruction")
                
                # Get accounts from instruction
                accounts = []
                if isinstance(instruction, dict):
                    if 'accounts' in instruction:
                        accounts = instruction['accounts']
                    if 'parsed' in instruction:
                        parsed = instruction['parsed']
                        if isinstance(parsed, dict):
                            info = parsed.get('info', {})
                            if 'mint' in info:
                                addr = str(info['mint'])
                                if self._is_valid_mint_address(addr):
                                    self._add_mint_address(addr, 'associated_token_program')
                
                # Process each account
                for account_idx in accounts:
                    if isinstance(account_idx, int) and account_idx < len(account_keys):
                        addr = str(account_keys[account_idx])
                        if self._is_valid_mint_address(addr):
                            self._add_mint_address(addr, 'associated_token_program')

            # Process metadata program instructions
            elif program_id == self.SYSTEM_ADDRESSES['metadata_program']:
                logger.debug("Found metadata program instruction")
                
                # Get accounts from instruction
                accounts = []
                if isinstance(instruction, dict):
                    if 'accounts' in instruction:
                        accounts = instruction['accounts']
                    if 'parsed' in instruction:
                        parsed = instruction['parsed']
                        if isinstance(parsed, dict):
                            info = parsed.get('info', {})
                            if 'mint' in info:
                                addr = str(info['mint'])
                                if self._is_valid_mint_address(addr):
                                    self._add_mint_address(addr, 'metadata_program')
                            if 'metadata' in info:
                                addr = str(info['metadata'])
                                if self._is_valid_mint_address(addr):
                                    self._add_mint_address(addr, 'metadata_program')
                
                # Process each account
                for account_idx in accounts:
                    if isinstance(account_idx, int) and account_idx < len(account_keys):
                        addr = str(account_keys[account_idx])
                        if self._is_valid_mint_address(addr):
                            self._add_mint_address(addr, 'metadata_program')

        except Exception as e:
            logger.error(f"Error processing instruction: {str(e)}", exc_info=True)
            self.errors.append(f"Error processing instruction: {str(e)}")

    def _is_valid_mint_address(self, address: str) -> bool:
        """Validate if an address is likely to be a mint address"""
        if not address:
            logger.debug("Empty address provided for mint validation")
            return False
            
        try:
            # First check if it's a system address
            if self._is_system_address(address):
                logger.debug(f"Address {address} rejected - System address")
                return False
                
            # Check length (should be 32-44 characters)
            if len(address) < 32 or len(address) > 44:
                logger.debug(f"Address {address} rejected - Invalid length ({len(address)} chars)")
                return False
                
            # Should only contain base58 characters
            if not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address):
                logger.debug(f"Address {address} rejected - Invalid base58 characters")
                return False
                
            # Additional validation for pump tokens
            if 'pump' in address.lower() and not address.endswith('pump'):
                logger.debug(f"Address {address} rejected - Invalid pump token format")
                return False
                
            logger.debug(f"Address {address} validated as potential mint address")
            return True
            
        except Exception as e:
            logger.error(f"Error validating mint address {address}: {str(e)}", exc_info=True)
            return False

    def _add_mint_address(self, address: str, source: str) -> None:
        """Add a mint address if it's valid and not already processed"""
        try:
            if not address:
                logger.debug(f"Skipping empty address from {source}")
                return

            if address in self.processed_addresses:
                logger.debug(f"Already processed address {address} from {source}")
                return

            self.processed_addresses.add(address)
            
            # Validate the address
            if not self._is_valid_mint_address(address):
                logger.debug(f"Invalid mint address {address} from {source}")
                return
                
            # Check for pump tokens
            if self._is_pump_token(address):
                logger.info(f"Found pump token: {address} from {source}")
                self.pump_tokens.add(address)
            else:
                logger.info(f"Found mint address: {address} from {source}")
                self.mint_addresses.add(address)
                
        except Exception as e:
            logger.warning(f"Error adding mint address {address} from {source}: {str(e)}")
            self.errors.append(f"Error adding mint address {address} from {source}: {str(e)}")

    def get_pump_tokens_with_stats(self) -> Dict[str, dict[str, Any]]:
        """Get pump tokens with their associated statistics

        Returns:
            Dict[str, dict[str, Any]]: Dictionary containing pump tokens and detailed statistics
        """
        # Start timing
        start_time = time.time()
        
        result = {
            "pump_tokens": {},
            "summary": {
                "total_pump_tokens": 0,
                "total_transactions": 0,
                "total_volume": 0.0,
                "total_unique_holders": 0,
                "total_mint_operations": 0,
                "total_transfer_operations": 0,
                "processing_time_ms": 0,
                "blocks_processed": len(self.processed_blocks) if hasattr(self, 'processed_blocks') else 0
            }
        }

        for token in self.pump_tokens:
            stats = self.pump_token_stats.get(token, {})
            token_data = {
                "address": token,
                "first_seen": stats.get("first_seen", 0),
                "last_seen": stats.get("last_seen", 0),
                "transaction_count": stats.get("transaction_count", 0),
                "mint_operations": stats.get("mint_operations", 0),
                "transfer_operations": stats.get("transfer_operations", 0),
                "holder_count": stats.get("holder_count", 0),
                "total_volume": stats.get("total_volume", 0.0),
                "confidence_score": stats.get("confidence_score", 0.0),
                "unique_senders": len(stats.get("unique_senders", set())),
                "unique_receivers": len(stats.get("unique_receivers", set())),
                "avg_transfer_amount": stats.get("avg_transfer_amount", 0.0),
                "max_transfer_amount": stats.get("max_transfer_amount", 0.0),
                "initial_mint_amount": stats.get("initial_mint_amount", 0.0)
            }
            
            # Update summary statistics
            result["summary"]["total_transactions"] += token_data["transaction_count"]
            result["summary"]["total_volume"] += token_data["total_volume"]
            result["summary"]["total_unique_holders"] += token_data["holder_count"]
            result["summary"]["total_mint_operations"] += token_data["mint_operations"]
            result["summary"]["total_transfer_operations"] += token_data["transfer_operations"]
            
            result["pump_tokens"][token] = token_data

        # Sort pump tokens by confidence score
        sorted_pump_tokens = sorted(result["pump_tokens"].items(), key=lambda x: x[1]["confidence_score"], reverse=True)
        
        # Update final summary stats
        result["summary"]["total_pump_tokens"] = len(result["pump_tokens"])
        result["summary"]["processing_time_ms"] = int((time.time() - start_time) * 1000)
        
        # Log summary statistics
        logger.info("=== Pump Token Analysis Summary ===")
        logger.info(f"Total Pump Tokens Found: {result['summary']['total_pump_tokens']}")
        logger.info(f"Total Transactions Processed: {result['summary']['total_transactions']}")
        logger.info(f"Total Volume: {result['summary']['total_volume']:.2f}")
        logger.info(f"Total Unique Holders: {result['summary']['total_unique_holders']}")
        logger.info(f"Total Mint Operations: {result['summary']['total_mint_operations']}")
        logger.info(f"Total Transfer Operations: {result['summary']['total_transfer_operations']}")
        logger.info(f"Blocks Processed: {result['summary']['blocks_processed']}")
        logger.info(f"Processing Time: {result['summary']['processing_time_ms']}ms")
        logger.info("================================")

        return result

    def _create_response(self, errors: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create the response dictionary
        
        Args:
            errors: Optional list of errors to include in the response
        
        Returns:
            Dict containing mint addresses, pump tokens, and any errors
        """
        response = {
            'mint_addresses': list(self.mint_addresses),
            'pump_tokens': list(self.pump_tokens),
            'errors': errors if errors is not None else self.errors
        }
        
        # Log summary
        logger.info(f"Found {len(response['mint_addresses'])} mint addresses and {len(response['pump_tokens'])} pump tokens")
        if response['errors']:
            logger.warning(f"Encountered {len(response['errors'])} errors during processing")
            
        return response

    def get_transaction_type(self, program_id: str) -> Optional[str]:
        """Get the transaction type for a program ID"""
        return self.PROGRAM_TYPES.get(program_id)

    def _get_program_id_from_instruction(self, instruction: Dict[str, Any], account_keys: List[str]) -> Optional[str]:
        """Extract program ID from instruction using multiple methods"""
        try:
            # Method 1: Direct program_id field
            if 'programId' in instruction:
                return str(instruction['programId'])
                
            # Method 2: Program ID index
            if 'programIdIndex' in instruction:
                idx = instruction['programIdIndex']
                if isinstance(idx, int) and idx < len(account_keys):
                    return str(account_keys[idx])
                    
            # Method 3: Last account in accounts array
            if 'accounts' in instruction:
                accounts = instruction['accounts']
                if accounts and isinstance(accounts[-1], int) and accounts[-1] < len(account_keys):
                    return str(account_keys[accounts[-1]])
                    
            # Method 4: Parsed data program field
            if 'parsed' in instruction:
                parsed = instruction['parsed']
                if isinstance(parsed, dict):
                    if 'program' in parsed:
                        return str(parsed['program'])
                    if 'info' in parsed and isinstance(parsed['info'], dict):
                        info = parsed['info']
                        if 'program' in info:
                            return str(info['program'])
                            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting program ID: {str(e)}")
            return None

    def _is_system_address(self, address: str) -> bool:
        """
        Check if an address is a system address that should be filtered out
        
        Args:
            address: The address to check
            
        Returns:
            bool: True if address is a system address
        """
        try:
            # Check exact matches for common system addresses
            if (address in [
                '11111111111111111111111111111111',  # System program
                'SysvarRent111111111111111111111111111111111',  # Rent sysvar
                'So11111111111111111111111111111111111111112',  # Wrapped SOL
                'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token program
                'Token2022111111111111111111111111111111111',  # Token2022 program
                'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',  # Associated token program
                'ComputeBudget111111111111111111111111111111',  # Compute budget program
                'Vote111111111111111111111111111111111111111',  # Vote program
                'Stake111111111111111111111111111111111111111',  # Stake program
                'Meta111111111111111111111111111111111111111'  # Metadata program
            ]):
                logger.debug(f"System address detected - Exact match: {address}")
                return True
                
            # Check known program/system address collections
            if (address in self.SYSTEM_ADDRESSES.values() or 
                address in self.PROGRAM_ADDRESSES):
                logger.debug(f"System address detected - Known collection match: {address}")
                return True
                
            # Check common prefixes
            system_prefixes = [
                '11111111',  # System program variants
                'SysvarRent',  # Rent sysvar variants
                'Vote111111111111111111',  # Vote program variants
                'Stake111111111111111111',  # Stake program variants
                'Meta',  # Metadata program variants
                'AToken',  # Associated token program variants
                'Token',  # Token program variants
                'Compute'  # Compute budget program variants
            ]
            
            if any(address.startswith(prefix) for prefix in system_prefixes):
                matching_prefix = next(prefix for prefix in system_prefixes if address.startswith(prefix))
                logger.debug(f"System address detected - Prefix match '{matching_prefix}': {address}")
                return True
                
            logger.debug(f"Address {address} is not a system address")
            return False
            
        except Exception as e:
            logger.error(f"Error checking system address {address}: {str(e)}", exc_info=True)
            return False

    def _process_token_balances(self, balances: List[Dict], tx_index: int, balance_type: str,
                              processed_addresses: Set[str], mint_addresses: Set[str], 
                              pump_tokens: Set[str]) -> bool:
        """Process token balances to extract mint addresses"""
        found_mints = False
        
        for balance in balances:
            if not isinstance(balance, dict):
                continue
                
            try:
                mint = balance.get('mint')
                if not mint or mint in processed_addresses:
                    continue
                    
                processed_addresses.add(mint)
                
                if self._is_valid_mint_address(mint):
                    if mint.lower().endswith('pump'):
                        pump_tokens.add(mint)
                        logger.info(f"Found pump token: {mint} in {balance_type} balance (tx {tx_index})")
                    else:
                        mint_addresses.add(mint)
                        logger.info(f"Found mint in {balance_type} balance: {mint} (tx {tx_index})")
                    found_mints = True
                    
            except Exception as e:
                logger.error(f"Error processing token balance: {str(e)}")
                
        return found_mints

    def _process_instructions(self, instructions: List[Dict], account_keys: List[str], tx_index: int,
                            processed_addresses: Set[str], mint_addresses: Set[str], 
                            pump_tokens: Set[str]) -> bool:
        """Process transaction instructions to extract mint addresses"""
        found_mints = False
        
        for instr_index, instr in enumerate(instructions):
            if not isinstance(instr, dict):
                continue
                
            try:
                program_id = self._extract_program_id(instr, account_keys)
                if not program_id:
                    continue

                # Process token program instructions
                if program_id in [self.TOKEN_PROGRAM_ID, self.TOKEN_2022_PROGRAM_ID]:
                    # Check first few accounts for mint
                    for i in range(min(3, len(account_keys))):
                        account = account_keys[i]
                        if account in processed_addresses:
                            continue

                        # Skip system addresses
                        if (account in self.SYSTEM_ADDRESSES.values() or 
                            account in self.PROGRAM_ADDRESSES or
                            account.startswith('11111111') or  # System program
                            account.startswith('SysvarRent') or  # Rent sysvar
                            account == 'So11111111111111111111111111111111111111112' or  # Wrapped SOL
                            account.startswith('Vote111111111111111111') or  # Vote program
                            account.startswith('Stake111111111111111111') or  # Stake program
                            account.startswith('Meta') or  # Metadata program
                            account.startswith('AToken') or  # Associated token program
                            account.startswith('Token') or  # Token program
                            account.startswith('Compute')  # Compute budget program
                        ):
                            continue

                        processed_addresses.add(account)
                        if self._is_valid_mint_address(account):
                            if account.lower().endswith('pump'):
                                pump_tokens.add(account)
                                logger.info(f"Found pump token in token program: {account} (tx {tx_index})")
                            else:
                                mint_addresses.add(account)
                                logger.info(f"Found mint in token program: {account} (tx {tx_index})")
                            found_mints = True

                # Process associated token program
                elif program_id == self.ASSOCIATED_TOKEN_PROGRAM_ID:
                    accounts = instr.get('accounts', [])
                    if len(accounts) >= 3:
                        mint_index = accounts[2]
                        if isinstance(mint_index, int) and mint_index < len(account_keys):
                            mint = account_keys[mint_index]
                            if mint not in processed_addresses:
                                processed_addresses.add(mint)

                                # Skip system addresses
                                if (mint in self.SYSTEM_ADDRESSES.values() or 
                                    mint in self.PROGRAM_ADDRESSES or
                                    mint.startswith('11111111') or  # System program
                                    mint.startswith('SysvarRent') or  # Rent sysvar
                                    mint == 'So11111111111111111111111111111111111111112' or  # Wrapped SOL
                                    mint.startswith('Vote111111111111111111') or  # Vote program
                                    mint.startswith('Stake111111111111111111') or  # Stake program
                                    mint.startswith('Meta') or  # Metadata program
                                    mint.startswith('AToken') or  # Associated token program
                                    mint.startswith('Token') or  # Token program
                                    mint.startswith('Compute')  # Compute budget program
                                ):
                                    continue

                                if self._is_valid_mint_address(mint):
                                    if mint.lower().endswith('pump'):
                                        pump_tokens.add(mint)
                                        logger.info(f"Found pump token in ATA: {mint} (tx {tx_index})")
                                    else:
                                        mint_addresses.add(mint)
                                        logger.info(f"Found mint in ATA: {mint} (tx {tx_index})")
                                    found_mints = True
            except Exception as e:
                logger.error(f"Error processing instruction {instr_index} in tx {tx_index}: {str(e)}")
                continue
                
        return found_mints

    def _is_valid_mint_address(self, address: str) -> bool:
        """Validate if an address is likely to be a mint address"""
        if not address:
            return False
            
        # Check if it's a system address
        if self._is_system_address(address):
            return False
            
        try:
            # Check length (should be 32-44 characters)
            if len(address) < 32 or len(address) > 44:
                return False
                
            # Should only contain base58 characters
            if not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address):
                return False
                
            # Additional validation for pump tokens
            if 'pump' in address.lower() and not address.endswith('pump'):
                return False
                
            return True
            
        except Exception as e:
            return False

    def _categorize_transaction(self, tx: Dict[str, Any]) -> List[str]:
        """Categorize a transaction based on its contents"""
        tx_types = set()
        
        try:
            message = tx.get('transaction', {}).get('message', {})
            if not message:
                return ['other']
                
            # Get program IDs from instructions
            instructions = message.get('instructions', [])
            for instr in instructions:
                if not isinstance(instr, dict):
                    continue
                    
                program_id = self._extract_program_id(instr, message.get('accountKeys', []))
                if program_id:
                    if program_id in self.PROGRAM_TYPES:
                        tx_types.add(self.PROGRAM_TYPES[program_id])
                        
            # Add NFT type if metadata programs found
            if any(pid in self.NFT_PROGRAM_IDS for pid in 
                  [self._extract_program_id(i, message.get('accountKeys', [])) for i in instructions 
                   if isinstance(i, dict)]):
                tx_types.add('nft')
                
            # Default to other if no types found
            if not tx_types:
                tx_types.add('other')
                
        except Exception as e:
            logger.error(f"Error categorizing transaction: {str(e)}")
            tx_types.add('other')
            
        return list(tx_types)

    def get_pump_tokens(self) -> List[str]:
        """Get list of pump tokens (backward compatibility method)"""
        return list(self.pump_tokens)

    def get_pump_tokens_with_stats(self) -> List[Dict[str, Any]]:
        """Get pump tokens with their associated statistics"""
        result = []
        for token in self.pump_tokens:
            stats = self.pump_token_stats.get(token, {})
            result.append({
                'address': token,
                'first_seen': stats.get('first_seen'),
                'transaction_count': stats.get('transaction_count', 0),
                'mint_operations': stats.get('mint_operations', 0),
                'transfer_operations': stats.get('transfer_operations', 0),
                'holder_count': len(stats.get('holders', set())),
                'total_volume': stats.get('total_volume', 0.0)
            })
        return result

    def _is_pump_token(self, address: str, instruction: Any = None, account_keys: List[str] = None) -> bool:
        """
        Check if a token is likely to be a pump token based on various criteria
        
        Args:
            address: Token mint address
            instruction: Optional instruction data for additional context
            account_keys: Optional list of account keys for additional context
            
        Returns:
            bool: True if token matches pump criteria
        """
        try:
            # Skip if address is invalid
            if not address or not isinstance(address, str):
                logger.debug(f"Invalid pump token input: {address}")
                return False

            # Skip system addresses
            if (address in self.SYSTEM_ADDRESSES.values() or 
                address in self.PROGRAM_ADDRESSES or
                address.startswith('11111111') or  # System program
                address.startswith('SysvarRent') or  # Rent sysvar
                address == 'So11111111111111111111111111111111111111112' or  # Wrapped SOL
                address.startswith('Vote111111111111111111') or  # Vote program
                address.startswith('Stake111111111111111111') or  # Stake program
                address.startswith('Meta') or  # Metadata program
                address.startswith('AToken') or  # Associated token program
                address.startswith('Token') or  # Token program
                address.startswith('Compute')  # Compute budget program
            ):
                logger.debug(f"Address {address} rejected as pump token - System address")
                return False

            # Check if address ends in 'pump' (case insensitive)
            if not address.lower().endswith('pump'):
                logger.debug(f"Address {address} rejected as pump token - Does not end with 'pump'")
                return False

            # Initialize stats if not exists
            if address not in self.pump_token_stats:
                logger.info(f"Initializing stats for new pump token: {address}")
                self.pump_token_stats[address] = {
                    'first_seen': time.time(),
                    'transaction_count': 0,
                    'mint_operations': 0,
                    'transfer_operations': 0,
                    'holder_count': 0,
                    'unique_senders': set(),
                    'unique_receivers': set(),
                    'total_volume': 0.0,
                    'last_activity': time.time()
                }
            
            stats = self.pump_token_stats[address]
            stats['transaction_count'] += 1
            
            # Update stats based on instruction type
            if instruction:
                if self.is_token_mint_instruction(instruction):
                    stats['mint_operations'] += 1
                    logger.debug(f"Pump token {address} - Mint operation detected")
                else:
                    stats['transfer_operations'] += 1
                    logger.debug(f"Pump token {address} - Transfer operation detected")

            # Log detection
            if address not in self.pump_tokens:
                logger.info(f"New pump token detected: {address} - Initial stats: {stats}")

            return True

        except Exception as e:
            logger.error(f"Error in _is_pump_token for {address}: {str(e)}", exc_info=True)
            return False

    def is_token_mint_instruction(self, instruction: Any) -> bool:
        """Check if an instruction is a token mint instruction"""
        try:
            if isinstance(instruction, dict):
                # Check parsed data
                if 'parsed' in instruction:
                    parsed = instruction['parsed']
                    if isinstance(parsed, dict):
                        # Check instruction type
                        if parsed.get('type') in ['mintTo', 'initializeMint']:
                            logger.debug(f"Found mint operation: {parsed.get('type')}")
                            return True
                        
                        # Check info
                        info = parsed.get('info', {})
                        if isinstance(info, dict):
                            if info.get('mintAuthority') or info.get('mint'):
                                logger.debug("Found mint authority in instruction")
                                return True
                        
                        # Check for mint-related accounts
                        accounts = info.get('accounts', {})
                        mint_related = ['mint', 'tokenMint', 'mintAccount']
                        if any(acc in accounts for acc in mint_related):
                            logger.debug("Found mint-related accounts")
                            return True
            return False
            
        except Exception as e:
            logger.error(f"Error checking mint instruction: {str(e)}", exc_info=True)
            return False

    def handle_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block response to extract mint information"""
        start_time = time.time()
        
        if not block_data or not isinstance(block_data, dict):
            logger.error("Invalid block data format")
            return self._create_response(errors=["Invalid block data format"])

        try:
            # Extract transactions safely
            transactions = block_data.get("transactions", [])
            if transactions:
                for tx_data in transactions:
                    self.handle_transaction(tx_data)

            return self._create_response()

        except Exception as e:
            error_msg = f"Error processing block: {str(e)}"
            logger.error(error_msg)
            return self._create_response(errors=[error_msg])

    def _process_token_balances(self, balances: List[Dict], tx_index: int, balance_type: str,
                              processed_addresses: Set[str], mint_addresses: Set[str], 
                              pump_tokens: Set[str]) -> bool:
        """Process token balances to extract mint addresses"""
        found_mints = False
        
        for balance in balances:
            if not isinstance(balance, dict):
                continue
                
            try:
                mint = balance.get('mint')
                if not mint or mint in processed_addresses:
                    continue
                    
                processed_addresses.add(mint)
                
                if self._is_valid_mint_address(mint):
                    if mint.lower().endswith('pump'):
                        pump_tokens.add(mint)
                        logger.info(f"Found pump token: {mint} in {balance_type} balance (tx {tx_index})")
                    else:
                        mint_addresses.add(mint)
                        logger.info(f"Found mint in {balance_type} balance: {mint} (tx {tx_index})")
                    found_mints = True
                    
            except Exception as e:
                logger.error(f"Error processing token balance: {str(e)}")
                
        return found_mints

    def _process_instructions(self, instructions: List[Dict], account_keys: List[str], tx_index: int,
                            processed_addresses: Set[str], mint_addresses: Set[str], 
                            pump_tokens: Set[str]) -> bool:
        """Process transaction instructions to extract mint addresses"""
        found_mints = False
        
        for instr_index, instr in enumerate(instructions):
            if not isinstance(instr, dict):
                continue
                
            try:
                program_id = self._extract_program_id(instr, account_keys)
                if not program_id:
                    continue

                # Process token program instructions
                if program_id in [self.TOKEN_PROGRAM_ID, self.TOKEN_2022_PROGRAM_ID]:
                    # Check first few accounts for mint
                    for i in range(min(3, len(account_keys))):
                        account = account_keys[i]
                        if account in processed_addresses:
                            continue

                        # Skip system addresses
                        if (account in self.SYSTEM_ADDRESSES.values() or 
                            account in self.PROGRAM_ADDRESSES or
                            account.startswith('11111111') or  # System program
                            account.startswith('SysvarRent') or  # Rent sysvar
                            account == 'So11111111111111111111111111111111111111112' or  # Wrapped SOL
                            account.startswith('Vote111111111111111111') or  # Vote program
                            account.startswith('Stake111111111111111111') or  # Stake program
                            account.startswith('Meta') or  # Metadata program
                            account.startswith('AToken') or  # Associated token program
                            account.startswith('Token') or  # Token program
                            account.startswith('Compute')  # Compute budget program
                        ):
                            continue

                        processed_addresses.add(account)
                        if self._is_valid_mint_address(account):
                            if account.lower().endswith('pump'):
                                pump_tokens.add(account)
                                logger.info(f"Found pump token in token program: {account} (tx {tx_index})")
                            else:
                                mint_addresses.add(account)
                                logger.info(f"Found mint in token program: {account} (tx {tx_index})")
                            found_mints = True

                # Process associated token program
                elif program_id == self.ASSOCIATED_TOKEN_PROGRAM_ID:
                    accounts = instr.get('accounts', [])
                    if len(accounts) >= 3:
                        mint_index = accounts[2]
                        if isinstance(mint_index, int) and mint_index < len(account_keys):
                            mint = account_keys[mint_index]
                            if mint not in processed_addresses:
                                processed_addresses.add(mint)

                                # Skip system addresses
                                if (mint in self.SYSTEM_ADDRESSES.values() or 
                                    mint in self.PROGRAM_ADDRESSES or
                                    mint.startswith('11111111') or  # System program
                                    mint.startswith('SysvarRent') or  # Rent sysvar
                                    mint == 'So11111111111111111111111111111111111111112' or  # Wrapped SOL
                                    mint.startswith('Vote111111111111111111') or  # Vote program
                                    mint.startswith('Stake111111111111111111') or  # Stake program
                                    mint.startswith('Meta') or  # Metadata program
                                    mint.startswith('AToken') or  # Associated token program
                                    mint.startswith('Token') or  # Token program
                                    mint.startswith('Compute')  # Compute budget program
                                ):
                                    continue

                                if self._is_valid_mint_address(mint):
                                    if mint.lower().endswith('pump'):
                                        pump_tokens.add(mint)
                                        logger.info(f"Found pump token in ATA: {mint} (tx {tx_index})")
                                    else:
                                        mint_addresses.add(mint)
                                        logger.info(f"Found mint in ATA: {mint} (tx {tx_index})")
                                    found_mints = True
            except Exception as e:
                logger.error(f"Error processing instruction {instr_index} in tx {tx_index}: {str(e)}")
                continue
                
        return found_mints

    def _is_valid_mint_address(self, address: str) -> bool:
        """Validate if an address is likely to be a mint address"""
        if not address:
            return False
            
        # Check if it's a system address
        if self._is_system_address(address):
            return False
            
        try:
            # Check length (should be 32-44 characters)
            if len(address) < 32 or len(address) > 44:
                return False
                
            # Should only contain base58 characters
            if not all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address):
                return False
                
            # Additional validation for pump tokens
            if 'pump' in address.lower() and not address.endswith('pump'):
                return False
                
            return True
            
        except Exception as e:
            return False

    def _categorize_transaction(self, tx: Dict[str, Any]) -> List[str]:
        """Categorize a transaction based on its contents"""
        tx_types = set()
        
        try:
            message = tx.get('transaction', {}).get('message', {})
            if not message:
                return ['other']
                
            # Get program IDs from instructions
            instructions = message.get('instructions', [])
            for instr in instructions:
                if not isinstance(instr, dict):
                    continue
                    
                program_id = self._extract_program_id(instr, message.get('accountKeys', []))
                if program_id:
                    if program_id in self.PROGRAM_TYPES:
                        tx_types.add(self.PROGRAM_TYPES[program_id])
                        
            # Add NFT type if metadata programs found
            if any(pid in self.NFT_PROGRAM_IDS for pid in 
                  [self._extract_program_id(i, message.get('accountKeys', [])) for i in instructions 
                   if isinstance(i, dict)]):
                tx_types.add('nft')
                
            # Default to other if no types found
            if not tx_types:
                tx_types.add('other')
                
        except Exception as e:
            logger.error(f"Error categorizing transaction: {str(e)}")
            tx_types.add('other')
            
        return list(tx_types)

    def get_pump_tokens(self) -> List[str]:
        """Get list of pump tokens (backward compatibility method)"""
        return list(self.pump_tokens)

    def get_pump_tokens_with_stats(self) -> List[Dict[str, Any]]:
        """Get pump tokens with their associated statistics"""
        result = []
        for token in self.pump_tokens:
            stats = self.pump_token_stats.get(token, {})
            result.append({
                'address': token,
                'first_seen': stats.get('first_seen'),
                'transaction_count': stats.get('transaction_count', 0),
                'mint_operations': stats.get('mint_operations', 0),
                'transfer_operations': stats.get('transfer_operations', 0),
                'holder_count': len(stats.get('holders', set())),
                'total_volume': stats.get('total_volume', 0.0)
            })
        return result

    def _is_pump_token(self, address: str, instruction: Any = None, account_keys: List[str] = None) -> bool:
        """
        Check if a token is likely to be a pump token based on various criteria
        
        Args:
            address: Token mint address
            instruction: Optional instruction data for additional context
            account_keys: Optional list of account keys for additional context
            
        Returns:
            bool: True if token matches pump criteria
        """
        try:
            # Skip if address is invalid
            if not address or not isinstance(address, str):
                logger.debug(f"Invalid pump token input: {address}")
                return False

            # Skip system addresses
            if (address in self.SYSTEM_ADDRESSES.values() or 
                address in self.PROGRAM_ADDRESSES or
                address.startswith('11111111') or  # System program
                address.startswith('SysvarRent') or  # Rent sysvar
                address == 'So11111111111111111111111111111111111111112' or  # Wrapped SOL
                address.startswith('Vote111111111111111111') or  # Vote program
                address.startswith('Stake111111111111111111') or  # Stake program
                address.startswith('Meta') or  # Metadata program
                address.startswith('AToken') or  # Associated token program
                address.startswith('Token') or  # Token program
                address.startswith('Compute')  # Compute budget program
            ):
                logger.debug(f"Address {address} rejected as pump token - System address")
                return False

            # Check if address ends in 'pump' (case insensitive)
            if not address.lower().endswith('pump'):
                logger.debug(f"Address {address} rejected as pump token - Does not end with 'pump'")
                return False

            # Initialize stats if not exists
            if address not in self.pump_token_stats:
                logger.info(f"Initializing stats for new pump token: {address}")
                self.pump_token_stats[address] = {
                    'first_seen': time.time(),
                    'transaction_count': 0,
                    'mint_operations': 0,
                    'transfer_operations': 0,
                    'holder_count': 0,
                    'unique_senders': set(),
                    'unique_receivers': set(),
                    'total_volume': 0.0,
                    'last_activity': time.time()
                }
            
            stats = self.pump_token_stats[address]
            stats['transaction_count'] += 1
            
            # Update stats based on instruction type
            if instruction:
                if self.is_token_mint_instruction(instruction):
                    stats['mint_operations'] += 1
                    logger.debug(f"Pump token {address} - Mint operation detected")
                else:
                    stats['transfer_operations'] += 1
                    logger.debug(f"Pump token {address} - Transfer operation detected")

            # Log detection
            if address not in self.pump_tokens:
                logger.info(f"New pump token detected: {address} - Initial stats: {stats}")

            return True

        except Exception as e:
            logger.error(f"Error in _is_pump_token for {address}: {str(e)}", exc_info=True)
            return False

    def is_token_mint_instruction(self, instruction: Any) -> bool:
        """Check if an instruction is a token mint instruction"""
        try:
            if isinstance(instruction, dict):
                # Check parsed data
                if 'parsed' in instruction:
                    parsed = instruction['parsed']
                    if isinstance(parsed, dict):
                        # Check instruction type
                        if parsed.get('type') in ['mintTo', 'initializeMint']:
                            logger.debug(f"Found mint operation: {parsed.get('type')}")
                            return True
                        
                        # Check info
                        info = parsed.get('info', {})
                        if isinstance(info, dict):
                            if info.get('mintAuthority') or info.get('mint'):
                                logger.debug("Found mint authority in instruction")
                                return True
                        
                        # Check for mint-related accounts
                        accounts = info.get('accounts', {})
                        mint_related = ['mint', 'tokenMint', 'mintAccount']
                        if any(acc in accounts for acc in mint_related):
                            logger.debug("Found mint-related accounts")
                            return True
            return False
            
        except Exception as e:
            logger.error(f"Error checking mint instruction: {str(e)}", exc_info=True)
            return False

    def handle_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block response to extract mint information"""
        start_time = time.time()
        
        if not block_data or not isinstance(block_data, dict):
            logger.error("Invalid block data format")
            return self._create_response(errors=["Invalid block data format"])

        try:
            # Extract transactions safely
            transactions = block_data.get("transactions", [])
            if transactions:
                for tx_data in transactions:
                    self.handle_transaction(tx_data)

            return self._create_response()

        except Exception as e:
            error_msg = f"Error processing block: {str(e)}"
            logger.error(error_msg)
            return self._create_response(errors=[error_msg])
