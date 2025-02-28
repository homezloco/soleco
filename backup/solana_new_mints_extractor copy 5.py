"""
Solana New Mints Extractor - Focused on detecting and analyzing newly created mint addresses
"""

from typing import Dict, List, Optional, Any, Union, Set
from datetime import datetime, timezone
import time
import asyncio
import logging
from fastapi import APIRouter, Query, HTTPException
from collections import defaultdict

from ..utils.solana_query import SolanaQueryHandler
from ..utils.solana_rpc import get_connection_pool
from ..utils.handlers.base_handler import BaseHandler
from ..utils.handlers.mint_handler import MintHandler
from ..utils.handlers.token_balance_handler import TokenBalanceHandler
from ..utils.handlers.transaction_stats_handler import TransactionStatsHandler
from ..utils.handlers.token_market_activity import TokenMarketActivityHandler
from ..utils.solana_types import EndpointConfig
from ..utils.solana_errors import RPCError, RetryableError
from ..utils.solana_rpc import AdaptiveRateConfig, get_connection_pool

# Configure logging
logger = logging.getLogger(__name__)

# Rate limiting configuration
rate_config = AdaptiveRateConfig(
    initial_rate=5,
    min_rate=2,
    max_rate=10,
    increase_threshold=0.6,
    decrease_threshold=0.4,
    adjustment_factor=1.1
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

class NewMintsExtractor(BaseHandler):
    """Extracts and analyzes new mint addresses from Solana blocks"""
    
    def __init__(self):
        """Initialize the extractor with specialized handlers"""
        super().__init__()  # Initialize BaseHandler
        
        # Initialize specialized handlers
        self.mint_handler = MintHandler()
        self.token_balance_handler = TokenBalanceHandler()
        self.stats_handler = TransactionStatsHandler()
        self.pump_detector = TokenMarketActivityHandler()
        
        # System program IDs for filtering
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
        
    async def process_block(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a block to find new mint addresses"""
        try:
            transactions = block_data.get('transactions', [])
            if not transactions:
                logger.warning("No transactions found in block data")
                return self._get_empty_result()

            block_stats = {
                'slot': block_data.get('slot', 0),
                'timestamp': block_data.get('blockTime', None),
                'transactions': 0,
                'transactions_with_mints': 0,
                'token_program_txs': 0,
                'mint_addresses': [],
                'pump_token_addresses': [],
                'transaction_stats': {},
                'program_stats': {},
                'processing_time': 0,
                'errors': []
            }

            start_time = time.time()
            
            # Process transactions
            for tx_index, tx in enumerate(transactions):
                if not tx or not isinstance(tx, dict):
                    logger.debug(f"Skipping invalid transaction at index {tx_index}")
                    continue
                    
                # Skip vote transactions early
                if self._is_vote_transaction(tx):
                    continue

                # Process transaction
                try:
                    result = await self._process_transaction(tx, tx_index)
                    
                    # Update block statistics
                    block_stats['transactions'] += 1
                    if result.get('mint_addresses'):
                        block_stats['transactions_with_mints'] += 1
                        block_stats['mint_addresses'].extend(result['mint_addresses'])
                        
                    if result.get('pump_token_addresses'):
                        block_stats['pump_token_addresses'].extend(result['pump_token_addresses'])
                        
                    # Update program statistics
                    for program_id, stats in result.get('program_stats', {}).items():
                        if program_id not in block_stats['program_stats']:
                            block_stats['program_stats'][program_id] = {
                                'calls': 0,
                                'mint_creations': 0,
                                'instruction_count': 0
                            }
                        prog_stats = block_stats['program_stats'][program_id]
                        prog_stats['calls'] += stats.get('calls', 0)
                        prog_stats['mint_creations'] += stats.get('mint_creations', 0)
                        prog_stats['instruction_count'] += stats.get('instruction_count', 0)
                        
                    # Track token program transactions
                    if result.get('token_program_calls'):
                        block_stats['token_program_txs'] += 1
                        
                except Exception as e:
                    error_msg = f"Error processing transaction {tx_index}: {str(e)}"
                    logger.error(error_msg)
                    block_stats['errors'].append(error_msg)

            # Calculate processing time
            block_stats['processing_time'] = time.time() - start_time
            
            # Remove duplicates from lists
            block_stats['mint_addresses'] = list(set(block_stats['mint_addresses']))
            block_stats['pump_token_addresses'] = list(set(block_stats['pump_token_addresses']))
            
            return block_stats
            
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            return self._get_empty_result(str(e))

    async def process_result(self, result: Any) -> Dict[str, Any]:
        """Process block result and extract mint addresses."""
        try:
            if not result or not isinstance(result, dict):
                logger.warning("Invalid result format")
                return {
                    "success": False,
                    "error": "Invalid result format",
                    "mint_addresses": [],
                    "statistics": self._get_empty_stats()
                }

            # Get block data
            block_data = result.get('result', {})
            if not isinstance(block_data, dict):
                logger.warning("Invalid block data format")
                return {
                    "success": False,
                    "error": "Invalid block data format",
                    "mint_addresses": [],
                    "statistics": self._get_empty_stats()
                }

            # Process block
            block_result = await self.process_block(block_data)
            
            # Log detailed statistics
            if block_result.get('statistics'):
                stats = block_result['statistics']
                logger.info("Block Analysis Summary:")
                logger.info(f"  Program IDs Found: {stats.get('program_ids_count', 0)}")
                logger.info(f"  Total Instructions: {stats.get('instruction_count', 0)}")
                logger.info(f"  Total Transactions: {stats.get('transaction_count', 0)}")
                logger.info(f"  Total Mint Addresses: {stats.get('mint_addresses_count', 0)}")
                logger.info(f"  New Mint Addresses: {stats.get('new_mint_addresses_count', 0)}")
                if stats.get('new_mint_addresses'):
                    logger.info("  New Mint Addresses List:")
                    for addr in stats['new_mint_addresses']:
                        logger.info(f"    - {addr}")
            
            # Format response
            return {
                "success": True,
                "slot": block_data.get('slot', 0),
                "timestamp": block_data.get('blockTime', int(time.time())),
                "mint_addresses": block_result.get('mint_addresses', []),
                "pump_token_addresses": block_result.get('pump_token_addresses', []),
                "statistics": block_result.get('statistics', self._get_empty_stats())
            }

        except Exception as e:
            error_msg = f"Error processing result: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "mint_addresses": [],
                "statistics": self._get_empty_stats()
            }

    async def handle_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle block response and extract mint addresses."""
        try:
            return await self.process_result(response)
        except Exception as e:
            logger.error(f"Error handling block response: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "mint_addresses": [],
                "statistics": self._get_empty_stats()
            }

    def _get_empty_stats(self) -> Dict[str, Any]:
        """Get empty statistics dictionary."""
        return {
            "total_transactions": 0,
            "transactions_with_mints": 0,
            "token_program_txs": 0,
            "program_stats": {},
            "processing_time_ms": 0
        }

    async def _process_transaction(self, tx: Dict[str, Any], tx_index: int) -> Dict[str, Any]:
        """Process a transaction to extract mint addresses with detailed tracking"""
        stats = {
            "instruction_count": 0,
            "token_program_calls": 0,
            "new_mints": 0,
            "programs_called": set(),
            "mint_addresses": [],
            "pump_token_addresses": [],
            "errors": [],
            "program_stats": defaultdict(lambda: {
                "calls": 0,
                "mint_creations": 0,
                "instruction_count": 0,
                "unique_signers": set()
            })
        }

        try:
            if not tx.get('meta'):
                logger.debug(f"Transaction {tx_index} has no metadata")
                return stats

            # Extract transaction message and account keys
            message = tx.get('transaction', {}).get('message', {})
            account_keys = message.get('accountKeys', [])
            if not account_keys:
                logger.debug(f"No account keys in transaction {tx_index}")
                return stats

            # Process instructions
            instructions = message.get('instructions', [])
            for idx, instruction in enumerate(instructions):
                try:
                    # Get program ID
                    program_id = self._extract_program_id(instruction, account_keys)
                    if not program_id:
                        continue

                    # Update program stats
                    stats['programs_called'].add(program_id)
                    prog_stats = stats['program_stats'][program_id]
                    prog_stats['calls'] += 1
                    prog_stats['instruction_count'] += 1
                    
                    # Check for token program usage
                    if program_id in [
                        'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
                        'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'   # Token2022
                    ]:
                        stats['token_program_calls'] += 1
                        
                        # Check for mint creation
                        if self._is_initialize_mint(instruction):
                            mint_address = self._extract_mint_address(instruction, account_keys)
                            if mint_address and self._is_valid_mint_address(mint_address):
                                stats['mint_addresses'].append(mint_address)
                                stats['new_mints'] += 1
                                prog_stats['mint_creations'] += 1

                    # Track instruction count
                    stats['instruction_count'] += 1

                except Exception as e:
                    error_msg = f"Error processing instruction {idx} in transaction {tx_index}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)

            # Process token balances for additional mint detection
            pre_balances = tx.get('meta', {}).get('preTokenBalances', [])
            post_balances = tx.get('meta', {}).get('postTokenBalances', [])
            
            new_balances = set(b['mint'] for b in post_balances) - set(b['mint'] for b in pre_balances)
            for mint in new_balances:
                if self._is_valid_mint_address(mint):
                    stats['mint_addresses'].append(mint)
                    stats['new_mints'] += 1

            # Process log messages for additional context
            log_messages = tx.get('meta', {}).get('logMessages', [])
            stats.update(self._process_log_messages(log_messages))

            # Check for errors
            if tx.get('meta', {}).get('err'):
                error_info = tx['meta']['err']
                stats['errors'].append(f"Transaction failed: {error_info}")

        except Exception as e:
            error_msg = f"Error processing transaction {tx_index}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            stats['errors'].append(error_msg)

        return stats

    def _extract_program_id(self, instruction: Dict[str, Any], account_keys: List[str]) -> Optional[str]:
        """Extract program ID from instruction"""
        try:
            program_idx = instruction.get('programIdIndex')
            if program_idx is not None and 0 <= program_idx < len(account_keys):
                return account_keys[program_idx]
        except Exception as e:
            logger.error(f"Error extracting program ID: {str(e)}")
        return None

    def _is_initialize_mint(self, instruction: Dict[str, Any]) -> bool:
        """Check if instruction is initializing a mint"""
        try:
            # Check for Token Program initialize mint (type 0)
            if instruction.get('data', '').startswith('0'):
                return True
                
            # Check for Token2022 Program initialize mint
            if instruction.get('data', '').startswith('1'):
                return True
        except Exception as e:
            logger.error(f"Error checking initialize mint: {str(e)}")
        return False

    def _extract_mint_address(self, instruction: Dict[str, Any], account_keys: List[str]) -> Optional[str]:
        """Extract mint address from instruction"""
        try:
            # For Token Program initialize mint, mint account is the first account
            accounts = instruction.get('accounts', [])
            if accounts and 0 <= accounts[0] < len(account_keys):
                return account_keys[accounts[0]]
        except Exception as e:
            logger.error(f"Error extracting mint address: {str(e)}")
        return None

    def _is_valid_mint_address(self, address: str) -> bool:
        """Validate if an address could be a valid mint"""
        try:
            # Basic validation
            if not address or len(address) != 44:  # Base58 encoded public key
                return False
                
            # Check if address is a known system address
            if address in self.SYSTEM_PROGRAM_IDS:
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error validating mint address: {str(e)}")
            return False

    def _process_log_messages(self, log_messages: List[str]) -> Dict[str, Any]:
        """Process transaction log messages for additional context"""
        stats = {
            "compute_units_consumed": 0,
            "program_invocations": defaultdict(int)
        }
        
        try:
            for log in log_messages:
                # Track compute units
                if "consumed" in log and "of" in log:
                    try:
                        consumed = int(log.split("consumed")[1].split("of")[0].strip())
                        stats["compute_units_consumed"] = consumed
                    except:
                        pass
                        
                # Track program invocations
                if "Program " in log and " invoke [" in log:
                    program_id = log.split("Program ")[1].split(" invoke")[0]
                    stats["program_invocations"][program_id] += 1
                    
        except Exception as e:
            logger.error(f"Error processing log messages: {str(e)}")
            
        return stats

    def _is_vote_transaction(self, tx: Dict[str, Any]) -> bool:
        """Check if transaction is a vote transaction"""
        try:
            if not tx.get('transaction', {}).get('message', {}).get('accountKeys'):
                return False
                
            account_keys = tx['transaction']['message']['accountKeys']
            return any(key == 'Vote111111111111111111111111111111111111111' for key in account_keys)
        except Exception as e:
            logger.error(f"Error checking vote transaction: {str(e)}")
            return False

    def _get_empty_result(self, error: str = None) -> Dict[str, Any]:
        """Get empty result structure"""
        result = {
            'slot': 0,
            'timestamp': None,
            'transactions': 0,
            'transactions_with_mints': 0,
            'token_program_txs': 0,
            'mint_addresses': [],
            'pump_token_addresses': [],
            'transaction_stats': self.stats_handler.get_summary()['transactions']['types'],
            'program_stats': {},
            'processing_time': 0,
            'errors': []
        }
        if error:
            result['errors'].append(error)
            logger.error(f"Returning empty result due to error: {error}")
        return result

async def get_query_handler() -> SolanaQueryHandler:
    """Get or create query handler with proper response handler"""
    try:
        # Get connection pool
        connection_pool = await get_connection_pool()
        
        # Initialize query handler
        query_handler = SolanaQueryHandler(connection_pool=connection_pool)
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
        query_handler = await get_query_handler()
        if not query_handler:
            logger.error("Failed to initialize query handler")
            return {"success": False, "error": "Failed to initialize query handler"}
            
        # Get latest block if not provided
        if start_block is None or end_block is None:
            client = await query_handler.connection_pool.get_client()
            current_block = await client.get_block_height()
            if not current_block:
                logger.error("Failed to get current block")
                return {"success": False, "error": "Failed to get current block"}
                
            if start_block is None:
                start_block = current_block
            if end_block is None:
                end_block = current_block
            
        extractor = NewMintsExtractor()
        
        logger.info(f"Processing blocks from {start_block} to {end_block} with batch size {batch_size}")
        results = await query_handler.process_blocks(
            num_blocks=end_block - start_block + 1,
            start_slot=start_block,
            end_slot=end_block,
            handlers=[extractor],
            batch_size=batch_size
        )
        
        if not results.get("success", False):
            logger.error("Block processing failed", extra={"errors": results.get("errors", [])})
            return {"success": False, "error": "Block processing failed", "errors": results.get("errors", [])}

        # Extract results from the extractor
        extractor_results = results.get(extractor.__class__.__name__, {})
        new_mints = extractor_results.get("mint_addresses", [])
        pump_tokens = extractor_results.get("pump_token_addresses", [])
        
        stats = {
            "total_blocks_analyzed": results.get("processed_blocks", 0),
            "total_new_mints": len(new_mints),
            "total_pump_tokens": len(pump_tokens),
            "success_rate": results.get("processed_blocks", 0) / (end_block - start_block + 1) if end_block - start_block + 1 > 0 else 0
        }
        
        logger.info("Successfully extracted new mints", extra={"stats": stats})
        return {
            "success": True,
            "start_block": results.get("start_slot"),
            "end_block": results.get("end_slot"),
            "blocks_processed": results.get("processed_blocks", 0),
            "blocks_failed": len(results.get("errors", [])),
            "new_mints": new_mints,
            "pump_tokens": pump_tokens,
            "stats": stats,
            "errors": results.get("errors", [])
        }
        
    except Exception as e:
        logger.error(f"Error extracting new mints: {str(e)}", exc_info=True)
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
        query_handler = await get_query_handler()
        
        # Get latest block
        client = await query_handler.connection_pool.get_client()
        latest_block = await client.get_block_height()
        if latest_block is None:
            logger.error("Failed to get latest block")
            return {"success": False, "error": "Failed to get latest block"}

        start_block = latest_block
        end_block = max(0, start_block - blocks + 1)

        logger.info(f"Analyzing blocks from {start_block} (newer) to {end_block} (older)")
        
        return await extract_new_mints(
            start_block=start_block,
            end_block=end_block,
            batch_size=min(blocks, 10)  # Use smaller batch size for recent blocks
        )
        
    except Exception as e:
        logger.error(f"Error getting recent new mints: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}

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
    try:
        query_handler = await get_query_handler()
        if not query_handler:
            logger.error("Failed to initialize query handler")
            raise HTTPException(status_code=503, detail="Failed to initialize Solana connection")
            
        extractor = NewMintsExtractor()
        start_time = time.time()
        end_time = start_time + duration
        
        monitored_mints = []
        monitored_pump_tokens = []
        last_block = None
        total_blocks_analyzed = 0
        errors = []
        
        logger.info(f"Starting mint monitoring for {duration} seconds with {interval} second intervals")
        
        while time.time() < end_time:
            try:
                # Get latest block
                client = await query_handler.connection_pool.get_client()
                current_block = await client.get_block_height()
                
                if current_block and (last_block is None or current_block > last_block):
                    start_block = last_block + 1 if last_block else current_block
                    
                    logger.debug(f"Processing blocks from {start_block} to {current_block}")
                    
                    # Process new blocks
                    results = await extract_new_mints(
                        start_block=start_block,
                        end_block=current_block,
                        batch_size=5  # Small batch size for monitoring
                    )
                    
                    if results.get("success", False):
                        monitored_mints.extend(results.get("new_mints", []))
                        monitored_pump_tokens.extend(results.get("pump_tokens", []))
                        total_blocks_analyzed += results.get("blocks_processed", 0)
                        
                        if results.get("errors"):
                            errors.extend(results.get("errors"))
                            
                        logger.info(
                            "Block processing complete",
                            extra={
                                "new_mints": len(results.get("new_mints", [])),
                                "pump_tokens": len(results.get("pump_tokens", [])),
                                "blocks_processed": results.get("blocks_processed", 0)
                            }
                        )
                    else:
                        logger.warning(f"Failed to process blocks: {results.get('error')}")
                        errors.append(results.get("error"))
                    
                    last_block = current_block
                    
            except Exception as e:
                error_msg = f"Error in monitoring loop: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                
            # Wait for next interval
            remaining_time = end_time - time.time()
            if remaining_time > 0:
                await asyncio.sleep(min(interval, remaining_time))
            else:
                break
                
        actual_duration = int(time.time() - start_time)
        stats = {
            "total_blocks_analyzed": total_blocks_analyzed,
            "total_new_mints": len(monitored_mints),
            "total_pump_tokens": len(monitored_pump_tokens),
            "mints_per_minute": (len(monitored_mints) * 60) / actual_duration if actual_duration > 0 else 0,
            "success_rate": (total_blocks_analyzed / (current_block - (last_block or current_block) + 1)) if current_block != last_block else 1.0
        }
        
        logger.info("Monitoring complete", extra={"stats": stats, "error_count": len(errors)})
        
        return {
            "success": True,
            "monitoring_duration": duration,
            "actual_duration": actual_duration,
            "new_mints": monitored_mints,
            "pump_tokens": monitored_pump_tokens,
            "stats": stats,
            "errors": errors
        }
        
    except Exception as e:
        error_msg = f"Error in mint monitoring: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=503, detail=error_msg)
