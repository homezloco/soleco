import pytest
from app.utils.solana_response import MintResponseHandler
from base58 import b58encode
import os

def test_is_valid_mint_address():
    handler = MintResponseHandler()
    
    # Test valid mint address format
    valid_address = b58encode(os.urandom(32)).decode('utf-8')
    assert handler._is_valid_mint_address(valid_address)
    
    # Test invalid addresses
    assert not handler._is_valid_mint_address(None)
    assert not handler._is_valid_mint_address("")
    assert not handler._is_valid_mint_address("too_short")
    assert not handler._is_valid_mint_address("!" * 32)  # Invalid characters
    assert not handler._is_valid_mint_address("1" * 45)  # Too long
    
    # Test system addresses
    assert not handler._is_valid_mint_address(handler.SYSTEM_ADDRESSES['token_program'])
    assert not handler._is_valid_mint_address(handler.SYSTEM_ADDRESSES['system_program'])

def test_process_token_instruction():
    handler = MintResponseHandler()
    
    # Create a mock token program instruction
    instruction = {
        'programIdIndex': 0,
        'accounts': [1, 2, 3],
        'parsed': {
            'info': {
                'mint': b58encode(os.urandom(32)).decode('utf-8'),
                'mintAuthority': b58encode(os.urandom(32)).decode('utf-8')
            }
        }
    }
    
    account_keys = [
        handler.SYSTEM_ADDRESSES['token_program'],
        b58encode(os.urandom(32)).decode('utf-8'),
        b58encode(os.urandom(32)).decode('utf-8'),
        b58encode(os.urandom(32)).decode('utf-8')
    ]
    
    # Process the instruction
    handler._process_instruction(instruction, account_keys)
    
    # Verify mint addresses were found
    assert len(handler.mint_addresses) > 0
    assert len(handler.processed_addresses) > 0

def test_process_associated_token_instruction():
    handler = MintResponseHandler()
    
    # Create a mock associated token program instruction
    mint_address = b58encode(os.urandom(32)).decode('utf-8')
    instruction = {
        'programIdIndex': 0,
        'accounts': [1, 2],
        'parsed': {
            'info': {
                'mint': mint_address
            }
        }
    }
    
    account_keys = [
        handler.SYSTEM_ADDRESSES['associated_token'],
        mint_address,
        b58encode(os.urandom(32)).decode('utf-8')
    ]
    
    # Process the instruction
    handler._process_instruction(instruction, account_keys)
    
    # Verify mint address was found
    assert mint_address in handler.mint_addresses
    assert mint_address in handler.processed_addresses

def test_process_metadata_instruction():
    handler = MintResponseHandler()
    
    # Create a mock metadata program instruction
    mint_address = b58encode(os.urandom(32)).decode('utf-8')
    metadata_address = b58encode(os.urandom(32)).decode('utf-8')
    instruction = {
        'programIdIndex': 0,
        'accounts': [1, 2, 3],
        'parsed': {
            'info': {
                'mint': mint_address,
                'metadata': metadata_address
            }
        }
    }
    
    account_keys = [
        handler.SYSTEM_ADDRESSES['metadata_program'],
        mint_address,
        metadata_address,
        b58encode(os.urandom(32)).decode('utf-8')
    ]
    
    # Process the instruction
    handler._process_instruction(instruction, account_keys)
    
    # Verify mint and metadata addresses were found
    assert mint_address in handler.mint_addresses
    assert metadata_address in handler.mint_addresses
    assert mint_address in handler.processed_addresses
    assert metadata_address in handler.processed_addresses
