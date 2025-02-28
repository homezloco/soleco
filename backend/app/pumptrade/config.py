import os
import sys
from dotenv import load_dotenv
from solana.rpc.api import Client
from solders.keypair import Keypair

# Explicitly remove any proxy-related environment variables
proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
for var in proxy_vars:
    os.environ.pop(var, None)

# Import WalletManager
from .wallet_management import WalletManager

# Load environment variables
load_dotenv()

# RPC Configuration
DEFAULT_RPC_URL = "https://api.mainnet-beta.solana.com"
RPC = os.getenv("SOLANA_RPC_URL", DEFAULT_RPC_URL)

# Solana Network Diagnostic Information
NETWORK_DIAGNOSTICS = {
    'cluster_nodes': 5939,  # Number of cluster nodes from diagnostic test
    'version': '2.1.11',   # Solana version from diagnostic test
    'epoch_info': {
        'current_epoch': 743,
        'slot_index': 394818,
        'slots_in_epoch': 432000,
        'absolute_slot': 321370818,
        'block_height': 299641640,
        'transaction_count': 374000062153
    }
}

# Wallet Configuration
try:
    # Attempt to load keypair using WalletManager
    payer_keypair = WalletManager.from_env()
    
    # Robust client initialization
    def create_solana_client(rpc_url):
        """
        Create a Solana client with robust error handling
        
        Args:
            rpc_url (str): Solana RPC URL
        
        Returns:
            Client: Configured Solana RPC client
        """
        try:
            # Initialize synchronous client with minimal parameters
            client = Client(rpc_url)
            return client
        except Exception as e:
            print(f"Client initialization error: {e}")
            print(f"RPC URL: {rpc_url}")
            raise
    
    # Initialize client
    client = create_solana_client(RPC) if payer_keypair else None
    
    if not payer_keypair:
        print("WARNING: No private key found. Trading functions will be disabled.")
except Exception as e:
    print(f"Error initializing wallet: {e}")
    client = None
    payer_keypair = None

# Compute Budget Configuration
UNIT_BUDGET = int(os.getenv("PUMP_FUN_UNIT_BUDGET", 100_000))
UNIT_PRICE = int(os.getenv("PUMP_FUN_UNIT_PRICE", 1_000_000))

def validate_configuration():
    """
    Validate the current Pump.fun trading configuration
    
    Returns:
        Dict: Configuration validation results
    """
    return {
        "rpc_url": RPC,
        "rpc_connected": client is not None,
        "wallet_configured": payer_keypair is not None,
        "wallet_address": str(payer_keypair.pubkey()) if payer_keypair else None,
        "unit_budget": UNIT_BUDGET,
        "unit_price": UNIT_PRICE,
        "network_diagnostics": NETWORK_DIAGNOSTICS
    }

# Expose configuration validation
__all__ = [
    'client', 
    'payer_keypair', 
    'RPC', 
    'UNIT_BUDGET', 
    'UNIT_PRICE', 
    'NETWORK_DIAGNOSTICS',
    'validate_configuration', 
    'WalletManager'
]