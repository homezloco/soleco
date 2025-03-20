from ..solana_rpc import SolanaConnectionPool
# Use string-based type annotation to avoid circular import
from typing import TYPE_CHECKING, Tuple, Any

if TYPE_CHECKING:
    from ..solana_query import SolanaQueryHandler
    from .network_status_handler import NetworkStatusHandler

async def initialize_handlers():
    """Initialize all handlers with proper error handling.
    
    Returns:
        Tuple containing connection pool, query handler, and network handler
    """
    # Import here to avoid circular imports
    from ..solana_query import SolanaQueryHandler
    from .network_status_handler import NetworkStatusHandler
    
    connection_pool = SolanaConnectionPool()
    query_handler = SolanaQueryHandler(connection_pool)
    network_handler = NetworkStatusHandler(query_handler)
    return connection_pool, query_handler, network_handler
