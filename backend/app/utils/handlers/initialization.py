from ..solana_rpc import SolanaConnectionPool
from ..solana_query import SolanaQueryHandler
from .network_status_handler import NetworkStatusHandler

async def initialize_handlers():
    connection_pool = SolanaConnectionPool()
    query_handler = SolanaQueryHandler(connection_pool)
    network_handler = NetworkStatusHandler(query_handler)
    return connection_pool, query_handler, network_handler
