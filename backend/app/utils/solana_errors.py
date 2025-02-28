"""
Custom error classes for Solana RPC interactions
"""

class RetryableError(Exception):
    """Base class for errors that can be retried"""
    pass

class RPCError(Exception):
    """Base class for RPC errors"""
    pass

class NodeBehindError(RetryableError):
    """Exception for node behind errors"""
    pass

class SlotSkippedError(RetryableError):
    """Exception for slot skipped errors"""
    pass

class MissingBlocksError(RetryableError):
    """Exception for missing blocks errors"""
    pass

class NodeUnhealthyError(RetryableError):
    """Exception for node unhealthy errors"""
    pass

class RateLimitError(RetryableError):
    """Exception for rate limit errors"""
    pass
