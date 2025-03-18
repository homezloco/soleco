"""
Handler for processing mint-related responses from Solana RPC.
"""

from typing import Dict, Optional, Set, List
from collections import defaultdict
from app.utils.base_response_handler import ResponseHandler, SolanaResponseManager

class MintResponseHandler(ResponseHandler):
    """Handler for mint-related responses"""
    
    SYSTEM_ADDRESSES = {
        'token_program': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
        'associated_token': 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',
        'metadata_program': 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s',
        'system_program': '11111111111111111111111111111111'
    }

    def __init__(self, response_manager: Optional[SolanaResponseManager] = None):
        super().__init__(response_manager)
        self.mint_addresses = set()
        self.processed_addresses = set()
        self.metadata_addresses = set()
        self.mint_stats = {
            "total_mints": 0,
            "unique_minters": set(),
            "mint_programs": defaultdict(int),
            "token_types": {
                "fungible": 0,
                "non_fungible": 0
            }
        }
    
    def process_transaction(self, transaction: Dict) -> Dict:
        """Process a mint transaction"""
        tx_details = super().process_result(transaction)
        
        # Track mint statistics
        if self._is_mint_transaction(tx_details):
            self.mint_stats["total_mints"] += 1
            
            # Track minter
            if "signer" in tx_details:
                self.mint_stats["unique_minters"].add(tx_details["signer"])
            
            # Track program
            if "program" in tx_details:
                self.mint_stats["mint_programs"][tx_details["program"]] += 1
            
            # Determine token type
            if self._is_nft_mint(tx_details):
                self.mint_stats["token_types"]["non_fungible"] += 1
            else:
                self.mint_stats["token_types"]["fungible"] += 1
        
        return tx_details
    
    def _is_mint_transaction(self, tx_details: Dict) -> bool:
        """Check if transaction is a mint operation"""
        if not tx_details.get("instructions"):
            return False
            
        mint_programs = {
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token Program
            "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"   # Token-2022
        }
        
        for inst in tx_details["instructions"]:
            if inst.get("program") in mint_programs and \
               "MintTo" in str(inst.get("data", "")):
                return True
        return False
    
    def _is_nft_mint(self, tx_details: Dict) -> bool:
        """Check if mint is for an NFT"""
        for inst in tx_details.get("instructions", []):
            if "decimals" in inst and inst["decimals"] == 0:
                return True
        return False

    def _is_valid_mint_address(self, address: str) -> bool:
        BASE58_CHARS = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        try:
            # Validate length and base58 characters
            return len(address) == 44 and all(c in BASE58_CHARS for c in address)
        except:
            return False

    def _process_instruction(self, instruction: Dict, account_keys: List[str]) -> Dict:
        """Process a single instruction"""
        program_id = account_keys[instruction['programIdIndex']]
        
        # Process based on program ID
        if program_id == self.SYSTEM_ADDRESSES['token_program']:
            return self._process_token_instruction(instruction, account_keys)
        elif program_id == self.SYSTEM_ADDRESSES['associated_token']:
            return self._process_associated_token_instruction(instruction, account_keys)
        elif program_id == self.SYSTEM_ADDRESSES['metadata_program']:
            return self._process_metadata_instruction(instruction, account_keys)
        
        return {}

    def _process_token_instruction(self, instruction: Dict, account_keys: List[str]) -> Dict:
        """Process a token program instruction"""
        parsed = instruction.get('parsed', {})
        info = parsed.get('info', {})
        mint = info.get('mint')
        if mint:
            self.mint_addresses.add(mint)
            self.processed_addresses.add(mint)
        return {
            'mint': mint,
            'mint_authority': info.get('mintAuthority'),
            'program': self.SYSTEM_ADDRESSES['token_program']
        }

    def _process_associated_token_instruction(self, instruction: Dict, account_keys: List[str]) -> Dict:
        """Process an associated token program instruction"""
        parsed = instruction.get('parsed', {})
        info = parsed.get('info', {})
        mint = info.get('mint')
        if mint:
            self.mint_addresses.add(mint)
            self.processed_addresses.add(mint)
        return {
            'mint': mint,
            'program': self.SYSTEM_ADDRESSES['associated_token']
        }

    def _process_metadata_instruction(self, instruction: Dict, account_keys: List[str]) -> Dict:
        """Process a metadata program instruction"""
        parsed = instruction.get('parsed', {})
        info = parsed.get('info', {})
        mint = info.get('mint')
        metadata = info.get('metadata')
        if mint:
            self.mint_addresses.add(mint)
            self.processed_addresses.add(mint)
        if metadata:
            self.metadata_addresses.add(metadata)
            self.processed_addresses.add(metadata)
        return {
            'mint': mint,
            'metadata': metadata,
            'program': self.SYSTEM_ADDRESSES['metadata_program']
        }
