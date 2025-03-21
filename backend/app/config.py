"""
Configuration module for the Soleco backend application.
Contains environment variables and other configuration settings.
"""
import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()

# API Keys
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
EXTRNODE_RPC_URL = os.getenv('EXTRNODE_RPC_URL')
ALCHEMY_RPC_URL = os.getenv('ALCHEMY_RPC_URL')
ANKR_API_KEY = os.getenv('ANKR_API_KEY')

# Updated Helius URL format - they might have changed their URL structure
HELIUS_RPC_URL = os.getenv('HELIUS_RPC_URL', f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}")

# RPC Configuration
DEFAULT_TIMEOUT = 30.0  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds

# Rate Limiting Configuration
RATE_CONFIG: Dict[str, Any] = {
    'initial_rate': 0.5,     # Initial requests per second
    'min_rate': 0.2,        # Minimum rate (1 request per 5 seconds)
    'max_rate': 2.0,        # Maximum rate (2 requests per second)
    'increase_factor': 1.1,  # Rate increase factor on success
    'decrease_factor': 0.5,  # Rate decrease factor on failure
    'cooldown_duration': 300,  # Cooldown duration in seconds
    'circuit_breaker_threshold': 10,  # Number of consecutive failures before circuit breaker
    'backoff_base': 2.0,    # Base for exponential backoff
    'max_backoff': 300,     # Maximum backoff time in seconds
}

# Connection Pool Configuration
POOL_SIZE = 5
POOL_TIMEOUT = 20.0

class Constants:
    """
    Constants used throughout the application.
    """
    # Solana Program IDs
    TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
    ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
    SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
    
    # Transaction Settings
    MAX_TRANSACTION_SIZE = 1232
    DEFAULT_COMPUTE_BUDGET = 200_000
    
    # Rate Limiting
    DEFAULT_RATE_LIMIT = 5  # requests per second
    
    # Timeouts
    DEFAULT_TIMEOUT = 30.0  # seconds
    
    # Batch Processing
    DEFAULT_BATCH_SIZE = 100
    MAX_BATCH_SIZE = 1000

# Config class for compatibility
class Config:
    """Configuration class for application settings."""
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    API_VERSION = "1.0.0"
    API_TITLE = "Soleco API"
    API_DESCRIPTION = "A comprehensive blockchain analytics and data extraction API"
    DEFAULT_RPC_URL = HELIUS_RPC_URL
    BACKUP_RPC_URLS = [ALCHEMY_RPC_URL, EXTRNODE_RPC_URL]
    RATE_CONFIG = RATE_CONFIG
    PUMPFUN_API_URL = os.getenv('PUMPFUN_API_URL', 'https://api.pump.fun/api')  # Updated to include /api path
