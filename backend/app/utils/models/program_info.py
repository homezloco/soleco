"""
Models for Solana program information and types.
"""

from dataclasses import dataclass
from typing import Dict, List, Set
from enum import Enum, auto

class ProgramType(Enum):
    """Enumeration of program types"""
    VOTE = auto()
    TOKEN = auto()
    TOKEN2022 = auto()
    METADATA = auto()
    METAPLEX = auto()
    CANDY_MACHINE = auto()
    JUPITER = auto()
    UNKNOWN = auto()

@dataclass
class ProgramInfo:
    """Information about Solana programs and system addresses"""
    
    # System program addresses
    SYSTEM_ADDRESSES: Dict[str, str] = None
    
    # Program IDs by type
    PROGRAM_ADDRESSES: Set[str] = None
    
    # Program type mapping
    PROGRAM_TYPES: Dict[str, str] = None
    
    # Program IDs by category
    PROGRAM_IDS: Dict[str, List[str]] = None
    
    # Common token program IDs
    TOKEN_PROGRAM_ID: str = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
    TOKEN_2022_PROGRAM_ID: str = 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'
    
    def __post_init__(self):
        """Initialize default values"""
        self.SYSTEM_ADDRESSES = {
            'system_program': 'Sys1111111111111111111111111111111111111111',
            'token_program': self.TOKEN_PROGRAM_ID,
            'token2022_program': self.TOKEN_2022_PROGRAM_ID,
            'associated_token': 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',
            'metadata_program': 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'
        }
        
        self.PROGRAM_ADDRESSES = {
            'Vote111111111111111111111111111111111111111',  # Vote Program
            self.TOKEN_PROGRAM_ID,  # Token Program
            self.TOKEN_2022_PROGRAM_ID,  # Token-2022
            'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s',  # Metadata Program
            'p1exdMJcjVao65QdewkaZRUnU6VPSXhus9n2GzWfh98',  # Metaplex Program
            'vau1zxA2LbssAUEF7Gpw91zMM1LvXrvpzJtmZ58rPsn',  # Metaplex Program v2
            'cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ',  # Candy Machine Program
            'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB',  # Jupiter v4
            'JUP6i4ozu5ydDCnLiMogSckDPpbtr7BJ4FtzYWkb5Rk'   # Jupiter v6
        }
        
        self.PROGRAM_TYPES = {
            'Vote111111111111111111111111111111111111111': 'vote',
            self.TOKEN_PROGRAM_ID: 'token',
            self.TOKEN_2022_PROGRAM_ID: 'token2022',
            'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s': 'metadata',
            'p1exdMJcjVao65QdewkaZRUnU6VPSXhus9n2GzWfh98': 'metaplex',
            'vau1zxA2LbssAUEF7Gpw91zMM1LvXrvpzJtmZ58rPsn': 'metaplex',
            'cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ': 'candy_machine',
            'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB': 'jupiter',
            'JUP6i4ozu5ydDCnLiMogSckDPpbtr7BJ4FtzYWkb5Rk': 'jupiter'
        }
        
        self.PROGRAM_IDS = {
            'token': [self.TOKEN_PROGRAM_ID],
            'token2022': [self.TOKEN_2022_PROGRAM_ID],
            'metadata': ['metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'],
            'jupiter': [
                'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB',
                'JUP6i4ozu5ydDCnLiMogSckDPpbtr7BJ4FtzYWkb5Rk'
            ]
        }
