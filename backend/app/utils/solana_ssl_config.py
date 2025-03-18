"""
SSL configuration for Solana RPC endpoints.

This module provides configuration for handling SSL verification for specific endpoints,
allowing for more granular control over SSL verification settings.
"""
import re
import logging
from typing import Dict, List, Optional, Pattern, Set, Union

logger = logging.getLogger(__name__)

# Endpoints that should bypass SSL verification
SSL_BYPASS_ENDPOINTS: Set[str] = set([
    # Add specific problematic endpoints here if needed
    "https://solana.public-rpc.com"
])

# Patterns for endpoints that should bypass SSL verification
SSL_BYPASS_PATTERNS: List[Pattern] = [
    # Example: re.compile(r'https://.*\.example\.com'),
    re.compile(r'https://.*\.public-rpc\.com')
]

def should_bypass_ssl_verification(endpoint: str) -> bool:
    """
    Determine if SSL verification should be bypassed for a specific endpoint.
    
    Args:
        endpoint: The endpoint URL to check
        
    Returns:
        True if SSL verification should be bypassed, False otherwise
    """
    # Check if the endpoint is in the bypass list
    if endpoint in SSL_BYPASS_ENDPOINTS:
        logger.warning(f"Bypassing SSL verification for known endpoint: {endpoint}")
        return True
        
    # Check if the endpoint matches any bypass patterns
    for pattern in SSL_BYPASS_PATTERNS:
        if pattern.match(endpoint):
            logger.warning(f"Bypassing SSL verification for endpoint matching pattern: {endpoint}")
            return True
            
    # Default to using SSL verification
    return False

def add_ssl_bypass_endpoint(endpoint: str) -> None:
    """
    Add an endpoint to the SSL bypass list.
    
    Args:
        endpoint: The endpoint URL to add
    """
    SSL_BYPASS_ENDPOINTS.add(endpoint)
    logger.info(f"Added endpoint to SSL bypass list: {endpoint}")

def add_ssl_bypass_pattern(pattern: str) -> None:
    """
    Add a pattern to the SSL bypass pattern list.
    
    Args:
        pattern: The regex pattern to add
    """
    try:
        compiled_pattern = re.compile(pattern)
        SSL_BYPASS_PATTERNS.append(compiled_pattern)
        logger.info(f"Added pattern to SSL bypass list: {pattern}")
    except re.error as e:
        logger.error(f"Invalid regex pattern '{pattern}': {str(e)}")
