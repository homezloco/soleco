"""
Models for representing Solana transactions and their statistics.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

@dataclass
class TransactionStats:
    """Statistics for a transaction."""
    instruction_count: int = 0
    program_ids: Set[str] = field(default_factory=set)
    error_count: int = 0
    mint_count: int = 0
    transfer_count: int = 0
    total_transactions: int = 0
    total_mint_addresses: int = 0
    total_mint_operations: int = 0
    initialize_mint_ops: int = 0
    mint_to_ops: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "instruction_count": self.instruction_count,
            "program_ids": list(self.program_ids),
            "error_count": self.error_count,
            "mint_count": self.mint_count,
            "transfer_count": self.transfer_count,
            "total_transactions": self.total_transactions,
            "total_mint_addresses": self.total_mint_addresses,
            "total_mint_operations": self.total_mint_operations,
            "initialize_mint_ops": self.initialize_mint_ops,
            "mint_to_ops": self.mint_to_ops
        }

@dataclass
class Transaction:
    """Represents a processed Solana transaction."""
    signature: str
    slot: int
    block_time: Optional[int] = None
    
    # Transaction data
    mint_addresses: Set[str] = field(default_factory=set)
    pump_tokens: Set[str] = field(default_factory=set)
    errors: List[str] = field(default_factory=list)
    
    # Transaction details
    sender: Optional[str] = None
    receiver: Optional[str] = None
    amount: float = 0
    token_balances: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Statistics
    stats: TransactionStats = field(default_factory=TransactionStats)
    
    def add_mint_address(self, address: str) -> None:
        """Add a mint address."""
        self.mint_addresses.add(address)
        self.stats.mint_count += 1
        
    def add_pump_token(self, address: str) -> None:
        """Add a pump token."""
        self.pump_tokens.add(address)
        
    def add_error(self, error: str) -> None:
        """Add an error."""
        self.errors.append(error)
        self.stats.error_count += 1
        
    def add_program_id(self, program_id: str) -> None:
        """Add a program ID."""
        self.stats.program_ids.add(program_id)
        
    def update_stats(self, instruction_count: int = 0,
                    transfer_count: int = 0) -> None:
        """Update transaction statistics."""
        self.stats.instruction_count += instruction_count
        self.stats.transfer_count += transfer_count
        
    def set_token_balance(self, mint: str, balance_type: str,
                         balance_data: Dict[str, Any]) -> None:
        """Set token balance data."""
        if mint not in self.token_balances:
            self.token_balances[mint] = {}
        self.token_balances[mint][balance_type] = balance_data
        
    def get_token_balance(self, mint: str, balance_type: str) -> Optional[Dict[str, Any]]:
        """Get token balance data."""
        return self.token_balances.get(mint, {}).get(balance_type)
        
    def set_sender(self, address: str) -> None:
        """Set transaction sender."""
        self.sender = address
        
    def set_receiver(self, address: str) -> None:
        """Set transaction receiver."""
        self.receiver = address
        
    def set_amount(self, amount: float) -> None:
        """Set transaction amount."""
        self.amount = amount
        
    def get_sender(self) -> Optional[str]:
        """Get transaction sender."""
        return self.sender
        
    def get_receiver(self) -> Optional[str]:
        """Get transaction receiver."""
        return self.receiver
        
    def get_amount(self) -> float:
        """Get transaction amount."""
        return self.amount
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            'signature': self.signature,
            'slot': self.slot,
            'block_time': self.block_time,
            'mint_addresses': list(self.mint_addresses),
            'pump_tokens': list(self.pump_tokens),
            'errors': self.errors,
            'sender': self.sender,
            'receiver': self.receiver,
            'amount': self.amount,
            'token_balances': self.token_balances,
            'stats': self.stats.to_dict()
        }
