"""
Common types and base classes for Solana modules
"""
from dataclasses import dataclass
from .solana_error import (
    RPCError,
    RetryableError,
    RateLimitError,
    NodeBehindError,
    SlotSkippedError,
    MissingBlocksError,
    NodeUnhealthyError,
    MethodNotSupportedError,
    SimulationError
)

@dataclass
class EndpointConfig:
    """Configuration for RPC endpoint."""
    url: str
    requests_per_second: float = 40.0
    burst_limit: int = 80
    max_retries: int = 3
    retry_delay: float = 1.0
