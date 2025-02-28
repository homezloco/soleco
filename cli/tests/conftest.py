"""
Pytest configuration file for Soleco CLI tests
"""

import os
import sys
import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def runner():
    """Create a CLI runner for testing"""
    return CliRunner()

@pytest.fixture
def mock_api():
    """Create a mock API client"""
    with patch('soleco_cli.api.SolecoAPI') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_console():
    """Create a mock console"""
    with patch('rich.console.Console') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
    api_url: http://localhost:8000
    timeout: 30
    max_retries: 3
    output_format: json
    """)
    return config_file
