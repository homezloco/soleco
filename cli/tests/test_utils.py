"""
Tests for the Soleco CLI utility functions
"""

import pytest
import json
import logging
from io import StringIO
from unittest.mock import patch, MagicMock, mock_open
from soleco_cli.utils import (
    setup_logging, 
    format_output,
    _dict_to_csv,
    handle_api_error,
    flatten_dict,
    truncate_string,
    format_duration,
    format_bytes
)


def test_setup_logging():
    """Test logging setup"""
    with patch('logging.getLogger') as mock_get_logger:
        with patch('logging.StreamHandler') as mock_stream_handler:
            with patch('logging.FileHandler') as mock_file_handler:
                with patch('pathlib.Path.mkdir') as mock_mkdir:
                    setup_logging(debug=False)
                    mock_get_logger.assert_called()
                    mock_stream_handler.assert_called()
                    mock_file_handler.assert_called()
                    mock_mkdir.assert_called()
        
        # Test debug mode
        with patch('logging.StreamHandler') as mock_stream_handler:
            with patch('logging.FileHandler') as mock_file_handler:
                with patch('pathlib.Path.mkdir') as mock_mkdir:
                    setup_logging(debug=True)
                    mock_stream_handler.assert_called()
                    mock_file_handler.assert_called()
                    mock_mkdir.assert_called()

def test_format_output():
    """Test output formatting"""
    data = {"key": "value"}
    console = MagicMock()
    
    # Test JSON output
    format_output(data, 'json', None, console)
    console.print_json.assert_called_once()
    
    # Test CSV output
    console.reset_mock()
    with patch('soleco_cli.utils._dict_to_csv') as mock_dict_to_csv:
        mock_dict_to_csv.return_value = "key,value"
        format_output(data, 'csv', None, console)
        mock_dict_to_csv.assert_called_once_with(data)
        console.print.assert_called_once()
    
    # Test file output
    console.reset_mock()
    with patch('builtins.open', mock_open()) as mock_file:
        format_output(data, 'json', 'output.json', console)
        mock_file.assert_called_once_with('output.json', 'w')
        console.print.assert_called_once()

def test_dict_to_csv():
    """Test dictionary to CSV conversion"""
    data = {
        "key1": "value1",
        "key2": {"nested_key": "nested_value"},
        "key3": ["item1", "item2"]
    }
    
    csv_str = _dict_to_csv(data)
    assert isinstance(csv_str, str)
    # The CSV format has headers and values on separate lines
    lines = csv_str.strip().split('\r\n')
    assert len(lines) == 2
    assert "key1" in lines[0]
    assert "value1" in lines[1]

def test_format_duration():
    """Test duration formatting"""
    # Test seconds
    assert format_duration(1.0).endswith("s")
    
    # Test minutes
    duration = format_duration(90)
    assert "m" in duration
    
    # Test hours
    duration = format_duration(5400)
    assert "h" in duration
    
    # Test days
    duration = format_duration(90000)
    assert "d" in duration

def test_format_bytes():
    """Test byte formatting"""
    # Test bytes
    assert "100 B" in format_bytes(100)
    
    # Test kilobytes
    assert "1.00 KB" in format_bytes(1024)
    
    # Test megabytes
    assert "1.00 MB" in format_bytes(1024 * 1024)
    
    # Test gigabytes
    assert "1.00 GB" in format_bytes(1024 * 1024 * 1024)

def test_handle_api_error():
    """Test API error handling"""
    error = MagicMock()
    error.status_code = 404
    error.message = "Not found"
    
    console = MagicMock()
    
    handle_api_error(error, console)
    console.print.assert_called_once()

def test_flatten_dict():
    """Test dictionary flattening"""
    nested_dict = {
        "key1": "value1",
        "key2": {
            "nested1": "nested_value1",
            "nested2": {
                "deep": "deep_value"
            }
        }
    }
    
    flattened = flatten_dict(nested_dict)
    assert flattened["key1"] == "value1"
    assert flattened["key2_nested1"] == "nested_value1"
    assert flattened["key2_nested2_deep"] == "deep_value"

def test_truncate_string():
    """Test string truncation"""
    long_string = "a" * 100
    
    # Test no truncation needed
    assert truncate_string("short", 10) == "short"
    
    # Test truncation
    truncated = truncate_string(long_string, 20)
    assert len(truncated) <= 20
    assert "..." in truncated
