"""
Custom error types for Solana RPC operations.
"""

class SolanaError(Exception):
    """Base class for Solana errors."""
    pass

class RPCError(SolanaError):
    """Base class for RPC errors."""
    pass

class RetryableError(RPCError):
    """Base class for errors that can be retried."""
    pass

class RateLimitError(RetryableError):
    """Raised when rate limit is exceeded."""
    pass

class NodeBehindError(RetryableError):
    """Raised when node is behind."""
    pass

class NodeUnhealthyError(RetryableError):
    """Raised when node is unhealthy."""
    pass

class MissingBlocksError(RetryableError):
    """Raised when blocks are missing."""
    pass

class TransactionError(SolanaError):
    """Base class for transaction errors."""
    pass

class MissingTransactionDataError(TransactionError):
    """Raised when transaction data is missing."""
    pass

class InvalidInstructionError(TransactionError):
    """Raised when instruction data is invalid."""
    pass

class InvalidProgramIdError(TransactionError):
    """Raised when program ID is invalid or not found."""
    pass

class InvalidMintAddressError(TransactionError):
    """Raised when mint address is invalid or not found."""
    pass

class TokenBalanceError(TransactionError):
    """Raised when token balance data is invalid or missing."""
    pass

class SlotSkippedError(RetryableError):
    """Raised when a slot is skipped."""
    pass

class ConnectionError(RetryableError):
    """Raised when connection fails."""
    pass

class TimeoutError(RetryableError):
    """Raised when request times out."""
    pass

class ValidationError(SolanaError):
    """Raised when data validation fails."""
    pass

# Public exports
__all__ = [
    'SolanaError',
    'RPCError',
    'RetryableError',
    'RateLimitError',
    'NodeBehindError',
    'NodeUnhealthyError',
    'MissingBlocksError',
    'TransactionError',
    'MissingTransactionDataError',
    'InvalidInstructionError',
    'InvalidProgramIdError',
    'InvalidMintAddressError',
    'TokenBalanceError',
    'SlotSkippedError',
    'ConnectionError',
    'TimeoutError',
    'ValidationError'
]
