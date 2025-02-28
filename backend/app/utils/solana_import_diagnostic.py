import sys
sys.path.append('/mnt/c/Users/Shane Holmes/CascadeProjects/windsurf-project/soleco/backend')

import logging
from typing import Dict, List, Any
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.rpc.responses import GetLatestBlockhashResp
from solana.rpc.async_api import AsyncClient
from spl.token.constants import TOKEN_PROGRAM_ID

logger = logging.getLogger('solana.imports')

async def validate_imports() -> Dict[str, Any]:
    """
    Validates that all required Solana components can be imported and are functional.
    
    Returns:
        Dict containing import status and any errors encountered
    """
    import_results = {
        "solana_components": [],
        "local_modules": [],
        "success": True,
        "errors": []
    }
    
    # Test Solana component imports
    try:
        # Core components
        import_results["solana_components"].append({
            "name": "AsyncClient, Transaction, Pubkey",
            "status": "success"
        })
        
        # RPC components
        from solders.rpc.responses import GetLatestBlockhashResp
        import_results["solana_components"].append({
            "name": "GetLatestBlockhashResp",
            "status": "success"
        })
        
        # Token components
        from spl.token.constants import TOKEN_PROGRAM_ID
        import_results["solana_components"].append({
            "name": "TOKEN_PROGRAM_ID",
            "status": "success"
        })
        
    except ImportError as e:
        import_results["success"] = False
        import_results["errors"].append(f"Failed to import Solana components: {str(e)}")
        logger.error(f"Solana import validation failed: {str(e)}")
    
    # Test local module imports
    try:
        from ..utils.token import get_associated_token_address
        from ..config import Constants
        from ..utils.common import Utils
        from ..models.coin_data import CoinData
        from ..utils.wallet import WalletManager
        from ..config import Config
        
        local_modules = [
            "get_associated_token_address",
            "Constants",
            "Utils",
            "CoinData",
            "WalletManager",
            "Config"
        ]
        
        for module in local_modules:
            import_results["local_modules"].append({
                "name": module,
                "status": "success"
            })
            
        # Test token address derivation
        test_pubkey = Pubkey.from_string("11111111111111111111111111111111")
        token_address = get_associated_token_address(test_pubkey, TOKEN_PROGRAM_ID)
        import_results["token_validation"] = {
            "status": "success",
            "address": str(token_address)
        }
        
    except ImportError as e:
        import_results["success"] = False
        import_results["errors"].append(f"Failed to import local modules: {str(e)}")
        logger.error(f"Local module import validation failed: {str(e)}")
    except Exception as e:
        import_results["success"] = False
        import_results["errors"].append(f"Error during validation: {str(e)}")
        logger.error(f"Validation error: {str(e)}")
    
    return import_results

print("Attempting to import Solana components:")

try:
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction
    from solana.rpc.async_api import AsyncClient
    print("✓ AsyncClient, Transaction, Pubkey imported successfully")
except ImportError as e:
    print(f"✗ Failed to import core components: {e}")

try:
    from solders.rpc.responses import GetLatestBlockhashResp
    print("✓ GetLatestBlockhashResp imported successfully")
except ImportError as e:
    print(f"✗ Failed to import GetLatestBlockhashResp: {e}")

print("\nAttempting to import from local modules:")

try:
    from app.pumptrade.token_utils import get_associated_token_address, create_test_pubkey
    print("✓ get_associated_token_address imported successfully")
except ImportError as e:
    print(f"✗ Failed to import get_associated_token_address: {e}")

try:
    from app.pumptrade.constants import PUMP_FUN_PROGRAM
    print("✓ Constants imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Constants: {e}")

try:
    from app.pumptrade.utils import confirm_txn, get_token_balance
    print("✓ Utils imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Utils: {e}")

try:
    from app.pumptrade.coin_data import CoinData, get_coin_data
    print("✓ CoinData imported successfully")
except ImportError as e:
    print(f"✗ Failed to import CoinData: {e}")

try:
    from app.pumptrade.wallet_management import WalletManager
    print("✓ WalletManager imported successfully")
except ImportError as e:
    print(f"✗ Failed to import WalletManager: {e}")

try:
    from app.pumptrade.config import client, payer_keypair
    print("✓ Config imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Config: {e}")

print("\nTesting token address derivation:")
try:
    from solders.pubkey import Pubkey
    
    # Test token address derivation
    from app.pumptrade.token_utils import get_associated_token_address, create_test_pubkey
    
    owner = create_test_pubkey()
    mint = create_test_pubkey()
    
    associated_address = get_associated_token_address(owner, mint)
    print(f"✓ Associated token address derived: {associated_address}")
except Exception as e:
    print(f"✗ Failed to derive token address: {e}")
