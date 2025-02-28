"""
Tests for the Soleco API client
"""

import pytest
import json
import requests
from unittest.mock import patch, MagicMock
from requests.exceptions import ConnectionError, Timeout

from soleco_cli.api import SolecoAPI, APIError

@pytest.fixture
def api_client():
    """Create an API client for testing"""
    return SolecoAPI(base_url="http://test.com")

@pytest.fixture
def mock_response():
    """Create a mock response"""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"status": "success", "data": {"key": "value"}}
    return mock

def test_api_init():
    """Test API client initialization"""
    api = SolecoAPI(base_url="http://test.com", timeout=60, max_retries=5)
    assert api.base_url == "http://test.com"
    assert api.timeout == 60
    assert api.max_retries == 5
    
    # Test URL normalization
    api = SolecoAPI(base_url="http://test.com/")
    assert api.base_url == "http://test.com"

def test_get_request(api_client, mock_response):
    """Test GET request"""
    with patch.object(api_client.session, 'request', return_value=mock_response) as mock_request:
        response = api_client.get("test/endpoint", params={"param": "value"})
        
        mock_request.assert_called_once_with(
            method="GET",
            url="http://test.com/test/endpoint",
            params={"param": "value"},
            json=None,
            headers={"Accept": "application/json"},
            timeout=30
        )
        
        assert response == mock_response.json.return_value

def test_post_request(api_client, mock_response):
    """Test POST request"""
    with patch.object(api_client.session, 'request', return_value=mock_response) as mock_request:
        data = {"key": "value"}
        response = api_client.post("test/endpoint", data=data, params={"param": "value"})
        
        mock_request.assert_called_once_with(
            method="POST",
            url="http://test.com/test/endpoint",
            params={"param": "value"},
            json=data,
            headers={"Accept": "application/json"},
            timeout=30
        )
        
        assert response == mock_response.json.return_value

def test_request_error():
    """Test request error handling"""
    api = SolecoAPI(base_url="http://test.com")
    
    # Test connection error
    with patch.object(api.session, 'request', side_effect=ConnectionError("Connection refused")):
        with pytest.raises(APIError) as excinfo:
            api._make_request("GET", "/test")
        assert "Connection failed" in str(excinfo.value)
    
    # Test timeout error
    with patch.object(api.session, 'request', side_effect=Timeout("Request timed out")):
        with pytest.raises(APIError) as excinfo:
            api._make_request("GET", "/test")
        assert "timed out" in str(excinfo.value)

def test_get_network_status(api_client, mock_response):
    """Test get_network_status method"""
    with patch.object(api_client, '_make_request', return_value=mock_response.json()) as mock_request:
        response = api_client.get_network_status()
        mock_request.assert_called_once_with("GET", "solana/network/status", params={"summary_only": False})
        assert response == mock_response.json()

def test_get_rpc_nodes(api_client, mock_response):
    """Test get_rpc_nodes method"""
    with patch.object(api_client, '_make_request', return_value=mock_response.json()) as mock_request:
        response = api_client.get_rpc_nodes()
        mock_request.assert_called_once_with("GET", "solana/network/rpc-nodes", params={"include_details": False, "health_check": False})
        assert response == mock_response.json()

def test_get_rpc_nodes_with_params(api_client, mock_response):
    """Test get_rpc_nodes method with parameters"""
    with patch.object(api_client, '_make_request', return_value=mock_response.json()) as mock_request:
        response = api_client.get_rpc_nodes(include_details=True, health_check=True)
        mock_request.assert_called_once_with("GET", "solana/network/rpc-nodes", params={"include_details": True, "health_check": True})
        assert response == mock_response.json()

def test_get_recent_mints(api_client, mock_response):
    """Test get_recent_mints method"""
    with patch.object(api_client, '_make_request', return_value=mock_response.json()) as mock_request:
        response = api_client.get_recent_mints()
        mock_request.assert_called_once_with("GET", "analytics/mints/recent", params={"blocks": 5})
        assert response == mock_response.json()

def test_get_recent_mints_with_params(api_client, mock_response):
    """Test get_recent_mints method with parameters"""
    with patch.object(api_client, '_make_request', return_value=mock_response.json()) as mock_request:
        response = api_client.get_recent_mints(blocks=10)
        mock_request.assert_called_once_with("GET", "analytics/mints/recent", params={"blocks": 10})
        assert response == mock_response.json()

def test_analyze_mint(api_client, mock_response):
    """Test analyze_mint method"""
    with patch.object(api_client, '_make_request', return_value=mock_response.json()) as mock_request:
        response = api_client.analyze_mint("mint123")
        mock_request.assert_called_once_with("GET", "analytics/mints/analyze/mint123", params={"include_history": False})
        assert response == mock_response.json()

def test_extract_mints_from_block(api_client, mock_response):
    """Test extract_mints_from_block method"""
    with patch.object(api_client, '_make_request', return_value=mock_response.json()) as mock_request:
        response = api_client.extract_mints_from_block()
        mock_request.assert_called_once_with("GET", "mints/extract", params={"limit": 1})
        assert response == mock_response.json()

def test_get_diagnostics(api_client, mock_response):
    """Test get_diagnostics method"""
    with patch.object(api_client, '_make_request', return_value=mock_response.json()) as mock_request:
        response = api_client.get_diagnostics()
        mock_request.assert_called_once_with("GET", "diagnostics", params=None)
        assert response == mock_response.json()
