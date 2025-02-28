"""
Specialized handler for extracting new mint addresses from Solana transactions.
"""

import logging
import base58
from typing import Any, Dict, List, Optional, Set
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)

class MintExtractor(BaseHandler):
    """Handler for extracting new mint addresses from transactions."""
    
    # Token program IDs
    TOKEN_PROGRAMS = {
        'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA': 'Token Program',
        'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBxvf9Ss623VQ5DA': 'Token-2022'
    }
    
    # Known programs that create mints
    MINT_CREATION_PROGRAMS = {
        "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s",  # Metaplex Token Metadata
        "M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K",  # Magic Eden v2
        "MEisE1HzehtrDpAAT8PnLHjpSSkRYakotTuJRPjTpo8",  # Magic Eden v3
        "hausS13jsjafwWwGqZTUQRmWyvyxn9EQpqMwV1PBBmk",  # Opensea
    }
    
    # Known token mints to exclude
    KNOWN_TOKEN_MINTS = {
        "So11111111111111111111111111111111111111112",  # Wrapped SOL
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
        "7i5KKsX2weiTkry7jA4ZwSJ4zRWqW2PPkiupCAMMQCLQ",  # PYTH
    }
    
    # Metadata program constants
    METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
    SYSTEM_PROGRAM_IDS = {
        '11111111111111111111111111111111',  # System Program
        'Vote111111111111111111111111111111111111111',  # Vote Program
        'Config1111111111111111111111111111111111111',  # Config Program
    }
    
    # Token program instruction discriminators
    TOKEN_IX_DISCRIMINATORS = {
        "initializeMint": "0",
        "initializeMint2": "8",
        "createMetadata": "b",
        "createMasterEdition": "c"
    }
    
    def __init__(self):
        super().__init__()
        self.mint_addresses: Set[str] = set()  # All mint addresses (both new and existing)
        self.new_mint_addresses: Set[str] = set()  # Only newly created mint addresses
        self.pump_tokens: Set[str] = set()  # All pump tokens
        self.stats = type('Stats', (), {})()
        self.stats.mint_operations = 0
        self.stats.token_operations = 0
        self.stats.metadata_operations = 0
        self.stats.pump_tokens = 0

    @staticmethod
    def is_valid_base58(address: str) -> bool:
        """Validate if an address is proper base58 encoded and correct length."""
        try:
            decoded = base58.b58decode(address)
            return len(decoded) == 32  # Solana public keys are 32 bytes
        except Exception:
            return False

    def _is_initialize_mint(self, instruction: Dict[str, Any]) -> bool:
        """Check if instruction is InitializeMint."""
        try:
            data = instruction.get('data', '')
            if not data:
                return False
                
            # Check discriminator
            discriminator = data[0] if data else None
            return discriminator in [
                self.TOKEN_IX_DISCRIMINATORS["initializeMint"],
                self.TOKEN_IX_DISCRIMINATORS["initializeMint2"]
            ]
        except Exception as e:
            logger.debug(f"Error checking initialize mint: {str(e)}")
            return False

    def _is_metadata_instruction(self, instruction: Dict[str, Any]) -> bool:
        """Check if instruction is from metadata program."""
        try:
            return instruction.get('programId') == self.METADATA_PROGRAM_ID
        except Exception as e:
            logger.debug(f"Metadata instruction check error: {str(e)}")
            return False

    def _get_full_account_keys(self, message: Dict[str, Any], meta: Dict[str, Any]) -> List[str]:
        """Get full list of account keys including loaded addresses."""
        try:
            account_keys = [str(key) for key in message.get('accountKeys', [])]
            
            # Add loaded addresses if present
            loaded_addresses = meta.get('loadedAddresses', {})
            if loaded_addresses:
                writable = loaded_addresses.get('writable', [])
                readonly = loaded_addresses.get('readonly', [])
                account_keys.extend(writable)
                account_keys.extend(readonly)
                
            return account_keys
            
        except Exception as e:
            logger.error(f"Error getting full account keys: {str(e)}")
            return []

    def _extract_mint_address(self, instruction: Dict[str, Any], account_keys: List[str]) -> Optional[str]:
        """Extract mint address from instruction with validation."""
        try:
            program_id = account_keys[instruction.get('programIdIndex', -1)]
            if not program_id:
                return None
                
            # Only process token program instructions
            if program_id not in self.TOKEN_PROGRAMS:
                return None
                
            # Must be an initialize mint instruction
            if not self._is_initialize_mint(instruction):
                return None
                
            accounts = instruction.get('accounts', [])
            if not accounts or len(accounts) < 2:
                return None
                
            # The mint account is the first account in initialize mint instructions
            potential_mint = account_keys[accounts[0]] if accounts and accounts[0] < len(account_keys) else None
            if potential_mint and self.is_valid_base58(potential_mint):
                if potential_mint not in self.KNOWN_TOKEN_MINTS:
                    logger.info(f"Found potential new mint: {potential_mint}")
                    return potential_mint
                    
            return None
                
        except Exception as e:
            logger.error(f"Error extracting mint address: {str(e)}")
            return None

    def _extract_metadata_mint(self, log_messages: List[str]) -> Optional[str]:
        """Extract mint address from metadata program logs."""
        for log in log_messages:
            if "initializeMint" in log:
                parts = log.split()
                if len(parts) > 2 and self.is_valid_mint_address(parts[2]):
                    return parts[2]
            elif "createMetadata" in log:
                parts = log.split()
                if len(parts) > 3 and self.is_valid_mint_address(parts[3]):
                    return parts[3]
        return None

    def _enhanced_mint_validation(self, address: str) -> bool:
        """Perform enhanced mint address validation."""
        return (
            self.is_valid_base58(address) 
            and address not in self.KNOWN_TOKEN_MINTS
            and address not in self.SYSTEM_PROGRAM_IDS
        )

    def _analyze_token_balances(self, pre_balances: List[Dict], post_balances: List[Dict]) -> Set[str]:
        """Analyze token balance changes for mint activity."""
        new_mints = set()
        for pre, post in zip(pre_balances, post_balances):
            if pre['mint'] != post['mint'] and self._enhanced_mint_validation(post['mint']):
                new_mints.add(post['mint'])
        return new_mints

    def _process_log_messages(self, log_messages: List[str]) -> Set[str]:
        """Extract potential mints from transaction logs."""
        mints = set()
        for log in log_messages:
            if "initializeMint" in log or "createMetadata" in log:
                parts = log.split()
                if len(parts) > 2 and self._enhanced_mint_validation(parts[2]):
                    mints.add(parts[2])
        return mints

    def _register_mint(self, address: str) -> None:
        """Register a validated mint address."""
        if self._enhanced_mint_validation(address):
            # Always add to mint_addresses (all mints)
            self.mint_addresses.add(address)
            
            # Only add to new_mint_addresses if it's a new mint
            if self._is_new_mint(address):
                self.new_mint_addresses.add(address)
                self.stats.mint_operations += 1
                logger.info(f"Validated new mint: {address}")
            
            # Check if this is a pump token (address ends with 'pump')
            logger.debug(f"Checking if {address} is a pump token. Ends with 'pump': {address.lower().endswith('pump')}")
            if address.lower().endswith('pump'):
                self.pump_tokens.add(address)
                self.stats.pump_tokens += 1
                logger.info(f"Identified pump token: {address}")
                
    def _is_new_mint(self, address: str) -> bool:
        """
        Determine if a mint address is new.
        Currently, we consider a mint address new if it's not already in our new_mint_addresses set
        and it passes our enhanced validation.
        This could be enhanced with more sophisticated checks in the future.
        """
        # Check if this is the first time we're seeing this mint address
        is_new = address not in self.new_mint_addresses
        
        # Additional checks could be added here in the future
        # For example, checking if the mint was created in the current block
        
        return is_new

    def process_block(self, block: Dict[str, Any]) -> None:
        """Process a block to extract new mint addresses."""
        try:
            if not block or not isinstance(block, dict):
                logger.warning("Invalid block data format")
                return
                
            transactions = block.get('transactions', [])
            if not isinstance(transactions, list):
                logger.warning("Invalid transactions format")
                return
                
            block_time = block.get('blockTime', 0)
            block_slot = block.get('parentSlot', 'unknown')
            logger.info(f"Processing block {block_slot} with {len(transactions)} transactions")
            
            for tx_wrapper in transactions:
                if not isinstance(tx_wrapper, dict):
                    logger.warning("Invalid transaction wrapper format")
                    continue
                    
                tx = tx_wrapper.get('transaction')
                meta = tx_wrapper.get('meta')
                
                if not isinstance(tx, dict) or not isinstance(meta, dict):
                    logger.debug("Invalid transaction or meta format")
                    continue
                    
                self.process_transaction(tx, meta)
                
            if self.new_mint_addresses:
                logger.info(f"Found {len(self.new_mint_addresses)} new mints in block {block_slot}")
                
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}", exc_info=True)
            
    def process_transaction(self, transaction: Dict[str, Any], meta: Dict[str, Any]) -> None:
        """Process a transaction to extract new mint addresses."""
        try:
            if not isinstance(transaction, dict) or not isinstance(meta, dict):
                logger.debug("Invalid transaction or meta format")
                return
                
            message = transaction.get('message')
            if not isinstance(message, dict):
                logger.debug("Invalid message format")
                return

            # Get full account keys including loaded addresses
            account_keys = self._get_full_account_keys(message, meta)
            if not account_keys:
                logger.debug("No valid account keys found")
                return
                
            log_messages = meta.get('logMessages', [])
            if not isinstance(log_messages, list):
                log_messages = []

            # 1. Process instructions
            instructions = message.get('instructions', [])
            if not isinstance(instructions, list):
                instructions = []
                
            inner_instructions = meta.get('innerInstructions', [])
            if not isinstance(inner_instructions, list):
                inner_instructions = []
                
            all_instructions = instructions + [i for g in inner_instructions for i in g.get('instructions', [])]
            
            for ix in all_instructions:
                if not isinstance(ix, dict):
                    continue
                    
                if mint_address := self._extract_mint_address(ix, account_keys):
                    self._register_mint(mint_address)

            # 2. Analyze token balances
            pre_balances = meta.get('preTokenBalances', [])
            post_balances = meta.get('postTokenBalances', [])
            
            # Add all mint addresses from token balances to our tracking
            if isinstance(pre_balances, list):
                for balance in pre_balances:
                    if isinstance(balance, dict) and 'mint' in balance:
                        mint = balance['mint']
                        if self._enhanced_mint_validation(mint):
                            self.mint_addresses.add(mint)
                            
            if isinstance(post_balances, list):
                for balance in post_balances:
                    if isinstance(balance, dict) and 'mint' in balance:
                        mint = balance['mint']
                        if self._enhanced_mint_validation(mint):
                            self.mint_addresses.add(mint)
            
            # Check for new mints by comparing pre and post balances
            if isinstance(pre_balances, list) and isinstance(post_balances, list):
                for mint in self._analyze_token_balances(pre_balances, post_balances):
                    self._register_mint(mint)

            # 3. Process log messages
            for mint in self._process_log_messages(log_messages):
                self._register_mint(mint)

            # 4. Metadata program analysis
            if any(self._is_metadata_instruction(ix) for ix in instructions if isinstance(ix, dict)):
                if mint := self._extract_metadata_mint(log_messages):
                    self._register_mint(mint)

        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}", exc_info=True)

    def get_results(self) -> Dict[str, Any]:
        """Get the results of mint extraction."""
        results = {
            "all_mints": list(self.mint_addresses),  # All mint addresses (both new and existing)
            "new_mints": list(self.new_mint_addresses),  # Only newly created mint addresses
            "pump_tokens": list(self.pump_tokens),  # All pump tokens
            "stats": {
                "total_all_mints": len(self.mint_addresses),
                "total_new_mints": len(self.new_mint_addresses),
                "total_pump_tokens": len(self.pump_tokens),
                "mint_operations": self.stats.mint_operations,
                "token_operations": self.stats.token_operations
            }
        }
        logger.debug(f"MintExtractor.get_results() returning: {results}")
        return results

    def get_detection_stats(self) -> Dict[str, Any]:
        """Get statistics about mint detection performance."""
        return {
            "total_mints_detected": len(self.mint_addresses),
            "new_mints_current_session": len(self.new_mint_addresses),
            "mint_operations_processed": self.stats.mint_operations,
            "token_program_detections": self.stats.token_operations,
            "metadata_program_detections": self.stats.metadata_operations
        }
