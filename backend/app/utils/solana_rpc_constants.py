"""
Constants used for Solana RPC connections.
"""
from app.config import HELIUS_API_KEY, ANKR_API_KEY, HELIUS_RPC_URL

# Default RPC endpoints to use if none are provided
DEFAULT_RPC_ENDPOINTS = [
    HELIUS_RPC_URL,
    "https://api.mainnet-beta.solana.com",
    # Removing Ankr endpoint as it requires a valid API key
    # "https://rpc.ankr.com/solana",  # Free tier not working - API key is not allowed to access blockchain
    # Conditionally add Ankr endpoint with API key if available
    *([] if not ANKR_API_KEY else [f"https://rpc.ankr.com/solana/{ANKR_API_KEY}"]),
    # "https://mainnet.rpcpool.com"  # HTTP 403 errors
]

# Fallback RPC endpoints to use if the default ones fail
FALLBACK_RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    # Removing Ankr endpoint as it requires a valid API key
    # "https://rpc.ankr.com/solana",  # Free tier not working - API key is not allowed to access blockchain
    # Conditionally add Ankr endpoint with API key if available
    *([] if not ANKR_API_KEY else [f"https://rpc.ankr.com/solana/{ANKR_API_KEY}"]),
]

# Official Solana network endpoints
# Note: Only including mainnet endpoints for production use
# Testnet and devnet endpoints should not be used in production
SOLANA_OFFICIAL_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com"
]

# Well-known RPC providers mapping
KNOWN_RPC_PROVIDERS = {
    # Public RPC providers
    "mainnet.helius-rpc.com": [HELIUS_RPC_URL],
    # Ankr requires an API key
    "rpc.ankr.com/solana": [] if not ANKR_API_KEY else [f"https://rpc.ankr.com/solana/{ANKR_API_KEY}"],
    "api.mainnet-beta.solana.com": ["https://api.mainnet-beta.solana.com"],
    # "mainnet.rpcpool.com": ["https://mainnet.rpcpool.com"],
    # "ssc-dao.genesysgo.net": ["https://ssc-dao.genesysgo.net"],  # DNS resolution issues
    # "api.metaplex.solana.com": ["https://api.metaplex.solana.com"],  # No address associated with hostname
    # "solana-mainnet.g.alchemy.com": ["https://solana-mainnet.g.alchemy.com/v2/demo"],  # JSON decode issues
    # "mainnet.solana.rpc.extrnode.com": ["https://mainnet.solana.rpc.extrnode.com"],  # Name resolution issues
}
