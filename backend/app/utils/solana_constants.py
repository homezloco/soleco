"""
Constants used across Solana-related utilities.
"""

# System and program addresses
SYSTEM_ADDRESSES = {
    'system_program': 'Sys1111111111111111111111111111111111111',
    'token_program': 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
    'token2022_program': 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',
    'associated_token': 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',
    'metadata_program': 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'
}

# Program IDs by type
PROGRAM_IDS = {
    'token': ['TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'],
    'token2022': ['TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'],
    'metadata': ['metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'],
    'jupiter': [
        'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB',  # Jupiter v4
        'JUP6i4ozu5ydDCnLiMogSckDPpbtr7BJ4FtzYWkb5Rk'   # Jupiter v6
    ]
}

# Known program types
PROGRAM_TYPES = {
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

# Program addresses to exclude from processing
EXCLUDED_PROGRAMS = {
    'Vote111111111111111111111111111111111111111',  # Vote Program
    'Stake11111111111111111111111111111111111111',  # Stake Program
    'BPFLoaderUpgradeab1e11111111111111111111111',  # BPF Loader
    'Config1111111111111111111111111111111111111',  # Config Program
    'Ed25519SigVerify111111111111111111111111111'   # Ed25519 Program
}

# Transaction types
TRANSACTION_TYPES = {
    'mint': ['MintTo', 'InitializeMint'],
    'transfer': ['Transfer', 'TransferChecked'],
    'burn': ['Burn', 'BurnChecked'],
    'swap': ['Swap', 'ExactOutSwap', 'ExactInSwap'],
    'liquidity': ['AddLiquidity', 'RemoveLiquidity']
}