"""
Cache TTL constants for the application.
These values determine how long data is cached in the database before being refreshed.
"""

# PumpFun API cache TTL constants (in seconds)
MARKET_OVERVIEW_CACHE_TTL = 600  # 10 minutes (was 5)
SOL_PRICE_CACHE_TTL = 600  # 10 minutes (was 5)
LATEST_TOKENS_CACHE_TTL = 900  # 15 minutes (was 5)
TOKEN_DETAILS_CACHE_TTL = 1800  # 30 minutes (was 10)
TOKEN_ANALYTICS_CACHE_TTL = 900  # 15 minutes (was 5)
TOKEN_HISTORY_CACHE_TTL = 1800  # 30 minutes (was 10)
LATEST_TRADES_CACHE_TTL = 600  # 10 minutes (was 3)
TOP_PERFORMERS_CACHE_TTL = 900  # 15 minutes (was 5)
KING_OF_THE_HILL_CACHE_TTL = 900  # 15 minutes (was 5)
SEARCH_TOKENS_CACHE_TTL = 900  # 15 minutes (was 5)
TOKEN_PRICE_CHART_CACHE_TTL = 900  # 15 minutes (was 5)
TOKEN_HOLDERS_CACHE_TTL = 3600  # 60 minutes (was 30)
TOKEN_SOCIAL_METRICS_CACHE_TTL = 1800  # 30 minutes (was 15)

# Solana API cache TTL constants (in seconds)
NETWORK_STATUS_CACHE_TTL = 300  # 5 minutes
PERFORMANCE_METRICS_CACHE_TTL = 180  # 3 minutes
RPC_NODES_CACHE_TTL = 600  # 10 minutes
CACHE_KEY_RPC_NODES = "rpc-nodes"
TOKEN_INFO_CACHE_TTL = 900  # 15 minutes
SYSTEM_RESOURCES_CACHE_TTL = 3600  # 1 hour
TRANSACTION_SIMULATE_CACHE_TTL = 300  # 5 minutes
RECENT_BLOCKS_CACHE_TTL = 180  # 3 minutes
VALIDATOR_INFO_CACHE_TTL = 1800  # 30 minutes
EPOCH_INFO_CACHE_TTL = 600  # 10 minutes
VOTE_ACCOUNTS_CACHE_TTL = 600  # 10 minutes

# General cache TTL constants (in seconds)
DEFAULT_CACHE_TTL = 300  # 5 minutes
SHORT_CACHE_TTL = 60  # 1 minute
MEDIUM_CACHE_TTL = 300  # 5 minutes
LONG_CACHE_TTL = 1800  # 30 minutes
VERY_LONG_CACHE_TTL = 3600  # 1 hour
