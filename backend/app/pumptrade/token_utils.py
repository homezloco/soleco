from solders.pubkey import Pubkey

def get_associated_token_address(owner: Pubkey, mint: Pubkey) -> Pubkey:
    """
    Derive the Associated Token Account address for a given owner and mint
    
    Args:
        owner (Pubkey): Owner's public key
        mint (Pubkey): Token mint address
    
    Returns:
        Pubkey: Associated Token Account address
    """
    # Solana Program Library Token Program ID
    TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    
    # Seeds for Associated Token Account derivation
    seeds = [
        bytes(owner),
        bytes(TOKEN_PROGRAM_ID),
        bytes(mint)
    ]
    
    # Derive the PDA (Program Derived Address)
    pda, _ = Pubkey.find_program_address(seeds, TOKEN_PROGRAM_ID)
    
    return pda

def create_test_pubkey() -> Pubkey:
    """
    Create a test Pubkey
    
    Returns:
        Pubkey: A randomly generated public key
    """
    import secrets
    
    # Generate 32 random bytes
    random_bytes = secrets.token_bytes(32)
    
    # Convert to Pubkey
    return Pubkey(random_bytes)
