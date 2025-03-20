"""
Pytest configuration file for the Solana RPC tests.
"""

import os
import sys
from typing import List

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from backend.app.utils.solana_rpc import SolanaConnectionPool

# Register the asyncio marker
def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as running with asyncio")

@pytest.fixture
def endpoint() -> str:
    """
    Provide a default RPC endpoint for testing.
    """
    return "https://api.mainnet-beta.solana.com"

@pytest.fixture
def endpoints() -> List[str]:
    """
    Provide a list of default RPC endpoints for testing.
    """
    return [
        "https://api.mainnet-beta.solana.com",
        "https://rpc.ankr.com/solana",
        "https://solana-api.projectserum.com"
    ]

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def well_known_endpoints():
    return [
        'https://api.mainnet-beta.solana.com',
        'https://rpc.ankr.com/solana',
        'https://solana-api.projectserum.com'
    ]

@pytest.fixture
def server_url():
    """Return the URL of the server to test against."""
    return os.environ.get("TEST_SERVER_URL", "http://localhost:8001")
