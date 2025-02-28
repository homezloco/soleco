import sys
sys.path.append('/mnt/c/Users/Shane Holmes/CascadeProjects/windsurf-project/soleco/backend')

print("Attempting to import Solana components:")

try:
    from solana.rpc.async_api import AsyncClient, Transaction, Pubkey
    print("✓ AsyncClient, Transaction, Pubkey imported successfully")
except ImportError as e:
    print(f"✗ Failed to import from solana.rpc.async_api: {e}")

try:
    from solana.rpc.commitment import Confirmed
    print("✓ Confirmed imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Confirmed: {e}")

try:
    from solana.rpc.types import TokenAccountOpts, TxOpts
    print("✓ TokenAccountOpts, TxOpts imported successfully")
except ImportError as e:
    print(f"✗ Failed to import from solana.rpc.types: {e}")

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
