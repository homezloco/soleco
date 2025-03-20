from ..solana_rpc import SolanaConnectionPool
from ..solana_error import RPCError, RateLimitError, NodeUnhealthyError

async def safe_rpc_call_async(method, *args, **kwargs):
    try:
        connection_pool = SolanaConnectionPool()
        client = await connection_pool.get_client()
        result = await client.call(method, *args, **kwargs)
        return result
    except (RPCError, RateLimitError, NodeUnhealthyError) as e:
        raise e
