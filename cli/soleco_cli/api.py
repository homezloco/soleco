"""
API client for interacting with the Soleco backend
"""

import requests
import logging
import time
from typing import Dict, Any, Optional, List, Union
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger("soleco")

class APIError(Exception):
    """Exception raised for API errors"""
    pass

class SolecoAPI:
    """Client for interacting with the Soleco API"""
    
    def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3):
        """Initialize the API client"""
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        
        logger.debug(f"Initialized API client for {base_url}")
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                     data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make an HTTP request to the API with retry logic"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        default_headers = {"Accept": "application/json"}
        
        if headers:
            default_headers.update(headers)
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=default_headers,
                    timeout=self.timeout
                )
                elapsed = time.time() - start_time
                
                logger.debug(f"{method} {url} completed in {elapsed:.2f}s (status: {response.status_code})")
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    return response.json()
                except ValueError:
                    logger.warning(f"Response is not valid JSON: {response.text[:100]}...")
                    return {"status": "success", "data": response.text}
                
            except Timeout:
                logger.warning(f"Request timed out (attempt {attempt+1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise APIError(f"Request timed out after {self.max_retries} attempts")
                time.sleep(1)
                
            except ConnectionError as e:
                logger.warning(f"Connection error: {str(e)} (attempt {attempt+1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise APIError(f"Connection failed after {self.max_retries} attempts: {str(e)}")
                time.sleep(1)
                
            except RequestException as e:
                status_code = e.response.status_code if hasattr(e, 'response') else "unknown"
                logger.error(f"Request failed with status {status_code}: {str(e)}")
                
                # Don't retry 4xx errors (except 429)
                if hasattr(e, 'response') and 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    try:
                        error_data = e.response.json()
                        error_message = error_data.get('detail', str(e))
                    except ValueError:
                        error_message = e.response.text or str(e)
                    
                    raise APIError(f"API error ({status_code}): {error_message}")
                
                if attempt == self.max_retries - 1:
                    raise APIError(f"Request failed after {self.max_retries} attempts: {str(e)}")
                
                # Exponential backoff
                sleep_time = 2 ** attempt
                logger.debug(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request to the API"""
        return self._make_request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a POST request to the API"""
        return self._make_request("POST", endpoint, params=params, data=data)
    
    # Network endpoints
    def get_network_status(self, summary_only: bool = False) -> Dict[str, Any]:
        """Get Solana network status"""
        return self.get("solana/network/status", params={"summary_only": summary_only})
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get Solana network performance metrics"""
        return self.get("solana/network/performance")
    
    # RPC node endpoints
    def get_rpc_nodes(self, include_details: bool = False, health_check: bool = False) -> Dict[str, Any]:
        """Get Solana RPC nodes"""
        params = {
            "include_details": include_details,
            "health_check": health_check
        }
        return self.get("solana/network/rpc-nodes", params=params)
    
    def get_rpc_stats(self) -> Dict[str, Any]:
        """Get RPC endpoint performance statistics"""
        return self.get("solana/network/rpc/stats")
    
    def get_filtered_rpc_stats(self) -> Dict[str, Any]:
        """Get filtered RPC endpoint performance statistics (excluding private endpoints)"""
        return self.get("solana/network/rpc/filtered-stats")
    
    # Mint analytics endpoints
    def get_recent_mints(self, blocks: int = 5) -> Dict[str, Any]:
        """Get recently created mint addresses"""
        return self.get("analytics/mints/recent", params={"blocks": blocks})
    
    def analyze_mint(self, mint_address: str, include_history: bool = False) -> Dict[str, Any]:
        """Analyze a specific mint address"""
        params = {"include_history": include_history}
        return self.get(f"analytics/mints/analyze/{mint_address}", params=params)
    
    def get_mint_statistics(self, timeframe: str = "24h") -> Dict[str, Any]:
        """Get mint creation statistics for a specific timeframe"""
        return self.get("analytics/mints/statistics", params={"timeframe": timeframe})
    
    def extract_mints_from_block(self, limit: int = 1) -> Dict[str, Any]:
        """Extract mint addresses from recent blocks"""
        return self.get("mints/extract", params={"limit": limit})
    
    # Diagnostics endpoints
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get system diagnostic information"""
        return self.get("diagnostics")
    
    def close(self) -> None:
        """Close the API client session"""
        self.session.close()
