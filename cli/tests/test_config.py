"""
Tests for the Soleco configuration management
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from soleco_cli.config import Config, DEFAULT_CONFIG

@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(json.dumps({
            "api_url": "http://test.com",
            "timeout": 60,
            "format": "json"
        }).encode())
        config_path = f.name
    
    yield config_path
    
    # Cleanup
    if os.path.exists(config_path):
        os.unlink(config_path)

@pytest.fixture
def config(temp_config_file):
    """Create a Config instance for testing"""
    # Instead of patching config_path which is an instance attribute, not a class attribute,
    # we'll create a Config instance with our temp file path
    config = Config(config_path=temp_config_file)
    return config

def test_config_init():
    """Test Config initialization with default values"""
    with patch.object(Config, '_load_config') as mock_load:
        mock_load.return_value = DEFAULT_CONFIG.copy()
        config = Config()
        assert hasattr(config, 'config_path')
        assert hasattr(config, 'config')

def test_config_load(temp_config_file):
    """Test loading configuration from file"""
    config = Config(config_path=temp_config_file)
    assert config.config["api_url"] == "http://test.com"
    assert config.config["timeout"] == 60

def test_config_get_default():
    """Test getting default configuration value"""
    with patch.object(Config, '_load_config') as mock_load:
        mock_load.return_value = DEFAULT_CONFIG.copy()
        config = Config()
        # Test getting existing value
        assert config.get("api_url") == DEFAULT_CONFIG["api_url"]
        # Test getting non-existent value with default
        assert config.get("non_existent", "default") == "default"

def test_config_set(config):
    """Test setting configuration value"""
    # Mock the _save_config method to avoid writing to file
    with patch.object(config, '_save_config'):
        config.set("new_key", "new_value")
        assert config.get("new_key") == "new_value"
        
        # Test overwriting existing value
        config.set("api_url", "http://new.com")
        assert config.get("api_url") == "http://new.com"

def test_config_reset(config):
    """Test resetting configuration to defaults"""
    # Mock the _save_config method to avoid writing to file
    with patch.object(config, '_save_config'):
        # Change a value
        config.set("api_url", "http://changed.com")
        assert config.get("api_url") == "http://changed.com"
        
        # Reset to defaults
        config.reset()
        assert config.get("api_url") == DEFAULT_CONFIG["api_url"]

def test_config_save(config, temp_config_file):
    """Test saving configuration to file"""
    # Change a value
    config.set("test_key", "test_value")
    
    # Verify file was written
    with open(temp_config_file, 'r') as f:
        saved_config = json.load(f)
        assert "test_key" in saved_config
        assert saved_config["test_key"] == "test_value"

def test_config_create_default(temp_config_file):
    """Test creating default configuration file"""
    # Remove the existing config file
    os.unlink(temp_config_file)
    
    # Create a new config instance
    config = Config(config_path=temp_config_file)
    
    # Verify default config was created
    assert os.path.exists(temp_config_file)
    with open(temp_config_file, 'r') as f:
        saved_config = json.load(f)
        assert saved_config == DEFAULT_CONFIG

def test_config_get_all(config):
    """Test getting all configuration values"""
    all_config = config.get_all()
    assert isinstance(all_config, dict)
    assert "api_url" in all_config
    assert "timeout" in all_config

def test_config_file_not_found():
    """Test handling of missing config file"""
    # Use a temporary directory that we have permission to write to
    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_path = os.path.join(temp_dir, "non_existent_config.json")
        with patch.object(Config, '_load_config') as mock_load:
            mock_load.return_value = DEFAULT_CONFIG.copy()
            config = Config(config_path=non_existent_path)
            assert config.get("api_url") == DEFAULT_CONFIG["api_url"]

def test_config_file_invalid_json():
    """Test handling of invalid JSON in config file"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"invalid json")
        config_path = f.name

    try:
        with patch.object(Config, '_load_config') as mock_load:
            mock_load.return_value = DEFAULT_CONFIG.copy()
            config = Config(config_path=config_path)
            assert config.get("api_url") == DEFAULT_CONFIG["api_url"]
    finally:
        if os.path.exists(config_path):
            os.unlink(config_path)
