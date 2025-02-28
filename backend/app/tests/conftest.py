"""
Pytest configuration file for the Solana RPC tests.
"""

import pytest

# Register the asyncio marker
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio coroutine"
    )
