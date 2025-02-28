class PumpFunTradeError(Exception):
    """Base exception for Pump.fun trading errors"""
    pass

class TokenNotFoundError(PumpFunTradeError):
    """Raised when a token cannot be found or retrieved"""
    pass

class TransactionFailedError(PumpFunTradeError):
    """Raised when a trading transaction fails"""
    pass

class ConfigurationError(PumpFunTradeError):
    """Raised when there's an issue with trading configuration"""
    pass
