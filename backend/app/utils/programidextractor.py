"""
Program ID extraction and analysis utilities for Solana transactions.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict
import asyncio
import time

from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.message import Message
from solders.instruction import Instruction

from .solana_response import SolanaResponseManager, EndpointConfig
from .solana_query import SolanaQueryHandler
from .solana_errors import RetryableError, RPCError
from .logging_config import setup_logging

# Get logger
logger = setup_logging('solana.programid')

class ProgramIdExtractor(SolanaResponseManager):
    """
    Extracts and analyzes program IDs from Solana transactions.
    Inherits from SolanaResponseManager to leverage existing response handling.
    """
    
    # Known program IDs
    SYSTEM_PROGRAM_IDS = {
        "11111111111111111111111111111111",  # System Program
        "Vote111111111111111111111111111111111111111",  # Vote Program
        "Stake11111111111111111111111111111111111111",  # Stake Program
        "BPFLoader2111111111111111111111111111111111",  # BPF Loader
        "ComputeBudget111111111111111111111111111111",  # Compute Budget
        "BPFLoaderUpgradeab1e11111111111111111111111",  # BPF Loader Upgradeable
    }
    
    TOKEN_PROGRAM_IDS = {
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # SPL Token
        "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",  # Token2022
        "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",  # Associated Token Account
    }
    
    KNOWN_DEFI_PROGRAMS = {
        "JUP6LkbZbjS1jKKwapdHF3G3kVhEmMYPV6Ma9QyGNPp",  # Jupiter
        "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",  # Orca Whirlpool
        "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP",  # Raydium
        "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",  # Raydium CMMM
        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Raydium Concentrated AMM
        "TSWAPaqyCSx2KABk68Shruf4rp7CxcNi8hAsbdwmHbN",  # Tensor Swap
        "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY",  # Phoenix DEX
        "MaestroAAe9ge5HTc64VbBQZ6fP77pwvrhM8i1XWSAx",  # Maestro
        "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD",  # Kamino Lending
    }
    
    KNOWN_NFT_PROGRAMS = {
        "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s",  # Metaplex Token Metadata
        "cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ",  # Candy Machine
        "hausS13jsjafwWwGqZTUQRmWyvyxn9EQpqMwV1PBBmk",  # Auction House
        "TSWAPaqyCSx2KABk68Shruf4rp7CxcNi8hAsbdwmHbN",  # Tensor
    }
    
    KNOWN_ORACLE_PROGRAMS = {
        "pythWSnswVUd12oZpeFP8e9CVaEqJg25g1Vtc2biRsT",  # Pyth
        "DcpnfYk9NBFkd8N6Fy6zQxjBpRXHzJuQE5G7DRtYKo3d",  # Switchboard
    }
    
    KNOWN_MEMO_PROGRAMS = {
        "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo",  # Memo Program
        "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",  # Memo Program v2
    }
    
    def __init__(self):
        """Initialize the ProgramIdExtractor"""
        config = EndpointConfig(
            url="https://api.mainnet-beta.solana.com",
            requests_per_second=40.0,
            burst_limit=80,
            max_retries=3,
            retry_delay=1.0
        )
        super().__init__(config)
        self.logger = logging.getLogger("solana.programid")
        
        # Track program activity
        self.program_stats = defaultdict(lambda: {
            'call_count': 0,
            'unique_callers': set(),
            'instruction_types': defaultdict(int),
            'first_seen': None,
            'last_seen': None,
            'error_count': 0,
            'success_count': 0,
            'avg_compute_units': 0.0,
            'total_compute_units': 0,
            'interacts_with': set()
        })
        
        # Track unknown programs
        self.unknown_programs = set()
        
        # Initialize stats
        self.stats = {
            'total_transactions': 0,
            'total_instructions': 0,
            'unique_programs': 0,
            'error_rate': 0.0
        }

    def handle_transaction(self, tx_data: Any) -> Dict[str, Any]:
        """
        Process a transaction to extract program ID information.
        
        Args:
            tx_data: Transaction data from RPC response
            
        Returns:
            Dict containing program ID statistics and transaction details
        """
        if not tx_data or not isinstance(tx_data, dict):
            self.logger.warning("Invalid transaction data format")
            return {}
            
        self.stats['total_transactions'] += 1
        current_time = int(time.time())
        
        try:
            # Extract message and account keys
            message = tx_data.get('transaction', {}).get('message', {})
            if not message:
                message = tx_data.get('message', {})
                
            # Get account keys, handling both string and object formats
            account_keys = []
            raw_keys = message.get('accountKeys', [])
            if isinstance(raw_keys, list):
                try:
                    account_keys = []
                    for k in raw_keys:
                        if isinstance(k, dict):
                            pubkey = k.get('pubkey')
                            if pubkey:
                                account_keys.append(str(pubkey))
                        else:
                            account_keys.append(str(k))
                except Exception as e:
                    self.logger.debug(f"Error processing account key: {str(e)}")
                    return {}
            
            # Get instructions, handling both parsed and raw formats
            instructions = []
            if 'instructions' in message:
                instructions = message['instructions']
            elif 'innerInstructions' in tx_data.get('meta', {}):
                for inner in tx_data['meta']['innerInstructions']:
                    instructions.extend(inner.get('instructions', []))
            
            self.logger.debug(f"Processing transaction with {len(instructions)} instructions")
            
            # Process each instruction
            for instruction in instructions:
                self._process_instruction(instruction, account_keys)
                
            # Update error stats if present
            meta = tx_data.get('meta', {})
            if meta and meta.get('err'):
                self._handle_transaction_error(tx_data)
                
            return self._create_response()
            
        except Exception as e:
            self.logger.error(f"Error processing transaction: {str(e)}")
            return {}

    def _process_instruction(self, instruction: Any, account_keys: List[str]) -> None:
        """
        Process a single instruction to extract program ID information.
        
        Args:
            instruction: Instruction data
            account_keys: List of account keys from the transaction
        """
        if not instruction or not account_keys:
            return
            
        try:
            self.stats['total_instructions'] += 1
            current_time = int(time.time())
            
            # Get program ID
            program_idx = instruction.get('programIdIndex')
            if program_idx is None:
                # Try alternate formats
                program_id = instruction.get('programId')
                if not program_id:
                    return
            else:
                try:
                    # Convert program_idx to integer if it's a string
                    program_idx = int(program_idx) if isinstance(program_idx, str) else program_idx
                    if program_idx >= len(account_keys):
                        return
                    program_id = account_keys[program_idx]
                except (ValueError, TypeError) as e:
                    self.logger.debug(f"Invalid program index format: {program_idx}, error: {str(e)}")
                    return
            
            # Update program stats even for system programs
            stats = self.program_stats[program_id]
            stats['call_count'] += 1
            
            # Track timing
            if not stats['first_seen']:
                stats['first_seen'] = current_time
            stats['last_seen'] = current_time
            
            # Track instruction types
            instruction_type = self._get_instruction_type(instruction)
            stats['instruction_types'][instruction_type] += 1
            
            # Track program interactions
            self._track_program_interactions(instruction, account_keys, program_id)
            
            # Track compute units if available
            meta = instruction.get('meta', {})
            if meta and 'computeUnits' in meta:
                compute_units = meta['computeUnits']
                stats['total_compute_units'] += compute_units
                stats['avg_compute_units'] = (
                    stats['total_compute_units'] / stats['call_count']
                )
                
            # Track unique callers
            if 'accounts' in instruction:
                for idx in instruction['accounts']:
                    if idx < len(account_keys):
                        stats['unique_callers'].add(account_keys[idx])
                
        except Exception as e:
            self.logger.error(f"Error processing instruction: {str(e)}")

    def _get_instruction_type(self, instruction: Any) -> str:
        """
        Attempt to determine the type of instruction.
        
        Args:
            instruction: Instruction data
            
        Returns:
            String describing the instruction type
        """
        try:
            # Check for parsed instruction data
            if 'parsed' in instruction:
                parsed = instruction['parsed']
                if isinstance(parsed, dict):
                    return parsed.get('type', 'unknown')
                    
            # Check for raw data
            if 'data' in instruction:
                # Here we could add logic to decode known instruction layouts
                return 'raw'
                
        except Exception as e:
            self.logger.debug(f"Error getting instruction type: {str(e)}")
            
        return 'unknown'

    def _track_program_interactions(
        self, 
        instruction: Any, 
        account_keys: List[str],
        program_id: str
    ) -> None:
        """
        Track which programs interact with each other.
        
        Args:
            instruction: Instruction data
            account_keys: List of account keys
            program_id: Current program ID being processed
        """
        try:
            # Get accounts referenced by this instruction
            account_indices = instruction.get('accounts', [])
            
            # Look for other programs in the account list
            for idx in account_indices:
                try:
                    # Convert index to integer if it's a string
                    idx = int(idx) if isinstance(idx, str) else idx
                    if not isinstance(idx, int):
                        self.logger.debug(f"Invalid account index type: {type(idx)}")
                        continue
                        
                    if idx >= len(account_keys):
                        continue
                        
                    account = str(account_keys[idx])
                    # If account is a program (either known or unknown)
                    if (account in self.SYSTEM_PROGRAM_IDS or 
                        account in self.TOKEN_PROGRAM_IDS or 
                        account in self.KNOWN_DEFI_PROGRAMS or 
                        account in self.KNOWN_NFT_PROGRAMS or 
                        account in self.KNOWN_ORACLE_PROGRAMS or 
                        account in self.KNOWN_MEMO_PROGRAMS or 
                        account in self.unknown_programs):
                        self.program_stats[program_id]['interacts_with'].add(account)
                except (ValueError, TypeError, IndexError) as e:
                    self.logger.debug(f"Error processing account index {idx}: {str(e)}")
                    continue
        except Exception as e:
            self.logger.debug(f"Error tracking program interactions: {str(e)}")

    def _handle_transaction_error(self, tx_data: Dict[str, Any]) -> None:
        """
        Handle and categorize transaction errors.
        
        Args:
            tx_data: Transaction data containing error information
        """
        try:
            error = tx_data['meta']['err']
            
            # Extract program ID from error if possible
            program_id = self._get_program_from_error(error)
            if program_id:
                self.program_stats[program_id]['error_count'] += 1
                
            # Update overall error rate
            total_tx = self.stats['total_transactions']
            error_count = sum(
                stats['error_count'] 
                for stats in self.program_stats.values()
            )
            self.stats['error_rate'] = error_count / total_tx if total_tx > 0 else 0
                
        except Exception as e:
            self.logger.debug(f"Error handling transaction error: {str(e)}")

    def _get_program_from_error(self, error: Any) -> Optional[str]:
        """
        Extract program ID from transaction error if possible.
        
        Args:
            error: Error data from transaction
            
        Returns:
            Program ID if found in error, None otherwise
        """
        try:
            if isinstance(error, dict):
                # Check for program error
                if 'InstructionError' in error:
                    return error.get('program_id')
        except Exception:
            pass
        return None

    def _create_response(self) -> Dict[str, Any]:
        """
        Create the response dictionary with program statistics.
        
        Returns:
            Dict containing program ID statistics
        """
        return {
            'stats': self.stats,
            'programs': {
                program_id: {
                    'call_count': stats['call_count'],
                    'unique_callers': len(stats['unique_callers']),
                    'instruction_types': dict(stats['instruction_types']),
                    'first_seen': stats['first_seen'],
                    'last_seen': stats['last_seen'],
                    'error_rate': (
                        stats['error_count'] / 
                        (stats['error_count'] + stats['success_count'])
                        if (stats['error_count'] + stats['success_count']) > 0
                        else 0
                    ),
                    'avg_compute_units': stats['avg_compute_units'],
                    'interacts_with': list(stats['interacts_with'])
                }
                for program_id, stats in self.program_stats.items()
            },
            'unknown_programs': list(self.unknown_programs)
        }

    def get_program_stats(self, program_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific program.
        
        Args:
            program_id: Program ID to get statistics for
            
        Returns:
            Dict containing program statistics if found, None otherwise
        """
        if program_id not in self.program_stats:
            return None
            
        stats = self.program_stats[program_id]
        return {
            'call_count': stats['call_count'],
            'unique_callers': len(stats['unique_callers']),
            'instruction_types': dict(stats['instruction_types']),
            'first_seen': stats['first_seen'],
            'last_seen': stats['last_seen'],
            'error_rate': (
                stats['error_count'] / 
                (stats['error_count'] + stats['success_count'])
                if (stats['error_count'] + stats['success_count']) > 0
                else 0
            ),
            'avg_compute_units': stats['avg_compute_units'],
            'interacts_with': list(stats['interacts_with'])
        }

    def _categorize_program(self, program_id: str, stats: Dict[str, Any]) -> str:
        """
        Categorize a program based on its ID and instruction types.
        
        Args:
            program_id: Program ID to categorize
            stats: Program statistics including instruction types
            
        Returns:
            String indicating the program category
        """
        # Check system programs
        if program_id in self.SYSTEM_PROGRAM_IDS:
            return 'system'
            
        # Check token programs
        if program_id in self.TOKEN_PROGRAM_IDS:
            return 'token'
            
        # Check known DeFi programs
        if program_id in self.KNOWN_DEFI_PROGRAMS:
            return 'defi'
            
        # Check known NFT programs
        if program_id in self.KNOWN_NFT_PROGRAMS:
            return 'nft'
            
        # Check known oracle programs
        if program_id in self.KNOWN_ORACLE_PROGRAMS:
            return 'oracle'
            
        # Check known memo programs
        if program_id in self.KNOWN_MEMO_PROGRAMS:
            return 'memo'
            
        # Check instruction types for hints
        instruction_types = str(stats['instruction_types']).lower()
        
        # DeFi hints
        if any(k in instruction_types for k in [
            'swap', 'pool', 'amm', 'stake', 'liquidity', 'vault',
            'deposit', 'withdraw', 'borrow', 'repay', 'margin',
            'trade', 'order', 'position', 'farm'
        ]):
            return 'defi'
            
        # NFT hints
        if any(k in instruction_types for k in [
            'mint', 'nft', 'metadata', 'collection', 'auction',
            'bid', 'offer', 'listing', 'verify', 'creator'
        ]):
            return 'nft'
            
        # Check program interactions
        if stats['interacts_with']:
            # Programs that heavily interact with token programs are likely DeFi
            token_interactions = sum(1 for addr in stats['interacts_with'] 
                                  if addr in self.TOKEN_PROGRAM_IDS)
            if token_interactions >= 2:
                return 'defi'
                
            # Programs that interact with NFT programs are likely NFT-related
            nft_interactions = sum(1 for addr in stats['interacts_with']
                                if addr in self.KNOWN_NFT_PROGRAMS)
            if nft_interactions > 0:
                return 'nft'
            
        return 'other'

    def get_active_programs(self, min_calls: int = 5) -> List[Dict[str, Any]]:
        """
        Get a list of active programs based on call count threshold.
        
        Args:
            min_calls: Minimum number of calls to be considered active
            
        Returns:
            List of active program statistics
        """
        active_programs = []
        program_categories = {
            'system': 0,
            'token': 0,
            'defi': 0,
            'nft': 0,
            'oracle': 0,
            'memo': 0,
            'other': 0
        }
        
        for program_id, stats in self.program_stats.items():
            try:
                if stats['call_count'] >= min_calls:
                    # Categorize program
                    category = self._categorize_program(program_id, stats)
                    # Ensure category exists in our tracking dict
                    if category not in program_categories:
                        category = 'other'
                    program_categories[category] += 1
                    
                    program_stats = {
                        'program_id': program_id,
                        'category': category,
                        'call_count': stats['call_count'],
                        'unique_callers': len(stats['unique_callers']),
                        'instruction_types': dict(stats['instruction_types']),
                        'first_seen': stats['first_seen'],
                        'last_seen': stats['last_seen'],
                        'error_rate': (
                            stats['error_count'] / 
                            (stats['error_count'] + stats['success_count'])
                            if (stats['error_count'] + stats['success_count']) > 0
                            else 0
                        ),
                        'avg_compute_units': stats['avg_compute_units'],
                        'interacts_with': list(stats['interacts_with'])
                    }
                    active_programs.append(program_stats)
            except Exception as e:
                self.logger.error(f"Error processing program {program_id}: {str(e)}")
                continue
                
        # Sort by call count (most active first)
        active_programs.sort(key=lambda x: x['call_count'], reverse=True)
        
        # Log program statistics
        self.logger.info(f"Found {len(active_programs)} active programs (min calls: {min_calls})")
        self.logger.info("Program categories:")
        for category, count in program_categories.items():
            self.logger.info(f"  - {category}: {count} programs")
            
        if active_programs:
            top_program = active_programs[0]
            self.logger.info(
                f"Most active program: {top_program['program_id']} ({top_program['category']}) "
                f"with {top_program['call_count']} calls"
            )
            
            # Log top programs by category
            self.logger.info("Most active program by category:")
            for category in program_categories:
                cat_programs = [p for p in active_programs if p['category'] == category]
                if cat_programs:
                    top = cat_programs[0]
                    self.logger.info(
                        f"  - {category}: {top['program_id']} "
                        f"with {top['call_count']} calls"
                    )
            
        return active_programs

    async def analyze_program(
        self,
        program_id: str,
        num_blocks: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze a specific program's recent activity.
        
        Args:
            program_id: Program ID to analyze
            num_blocks: Number of recent blocks to analyze
            
        Returns:
            Dict containing program analysis results
        """
        try:
            # Reset stats for this analysis
            self.program_stats.clear()
            self.unknown_programs.clear()
            self.stats = {
                'total_transactions': 0,
                'total_instructions': 0,
                'unique_programs': 0,
                'error_rate': 0.0
            }
            
            # Get transactions for the program
            query_handler = SolanaQueryHandler()
            transactions = await query_handler.get_program_transactions(
                program_id,
                limit=num_blocks
            )
            
            # Process each transaction
            for tx in transactions:
                self.handle_transaction(tx)
                
            # Update unique programs count
            self.stats['unique_programs'] = len(self.program_stats)
            
            return self._create_response()
            
        except Exception as e:
            self.logger.error(f"Error analyzing program {program_id}: {str(e)}")
            return {}

    def analyze_imports(self, module_name: str) -> Dict[str, List[str]]:
        """
        Analyze the imports of a given module.
        
        Args:
            module_name: Name of the module to analyze
            
        Returns:
            Dict containing the module's imports
        """
        import ast
        import importlib
        from collections import defaultdict
        
        dependency_map = defaultdict(list)
        
        try:
            module = importlib.import_module(module_name)
            with open(module.__file__, 'r') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependency_map[module_name].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module_path = node.module
                    if node.level > 0:  # Handle relative imports
                        base_module = module_name.rsplit('.', node.level)[0]
                        module_path = f"{base_module}.{module_path}" if module_path else base_module
                    dependency_map[module_name].append(module_path)
        except Exception as e:
            logger.error(f"Import analysis failed for {module_name}: {str(e)}")
        
        return dict(dependency_map)
