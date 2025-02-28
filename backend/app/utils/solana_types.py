"""
Common types and base classes for Solana modules
"""
from dataclasses import dataclass

@dataclass
class EndpointConfig:
    """Configuration for RPC endpoint."""
    url: str
    requests_per_second: float = 40.0
    burst_limit: int = 80
    max_retries: int = 3
    retry_delay: float = 1.0

class RPCError(Exception):
    """Base exception for RPC errors"""
    pass

class RetryableError(RPCError):
    """Exception for errors that can be retried"""
    pass

class RateLimitError(RPCError):
    """Exception for rate limit errors"""
    pass

class NodeBehindError(RPCError):
    """Exception for node behind errors"""
    pass

class SlotSkippedError(RPCError):
    """Exception for slot skipped errors"""
    pass

class MissingBlocksError(RPCError):
    """Exception for missing blocks errors"""
    pass

class NodeUnhealthyError(RPCError):
    """Exception for node unhealthy errors"""
    pass

class SimulationError(RPCError):
    """Exception for transaction simulation errors"""
    pass
