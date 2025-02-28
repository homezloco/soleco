"""
Solana RPC error definitions.
"""

class RetryableError(BaseException):
    """Error that can be retried"""
    pass

class RPCError(BaseException):
    """Non-retryable RPC error"""
    pass

class NodeUnhealthyError(RetryableError):
    """Error indicating a node is unhealthy and should be retried"""
    pass
