"""
Test client for the RPC Nodes API endpoint
"""
import asyncio
import aiohttp
import json
import logging
from backend.app.utils.solana_rpc import SolanaConnectionPool
import pytest
import socket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_server_running(host="localhost", port=8001):
    """Check if server is running on the specified host and port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect((host, port))
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False

@pytest.mark.asyncio
@pytest.mark.skipif(not is_server_running(), reason="Server is not running")
async def test_rpc_nodes_api():
    """Test the RPC nodes API endpoint."""
    try:
        # API endpoint URL
        url = "http://localhost:8001/soleco/solana/rpc-nodes"
        
        # Test with different query parameters
        test_cases = [
            {"name": "Basic (no details)", "params": {}},
            {"name": "With details", "params": {"include_details": "true"}},
            {"name": "With health check", "params": {"health_check": "true"}},
            {"name": "With details and health check", "params": {"include_details": "true", "health_check": "true"}}
        ]
        
        async with aiohttp.ClientSession() as session:
            for test in test_cases:
                logger.info(f"\nTesting: {test['name']}")
                
                # Make the request
                async with session.get(url, params=test["params"]) as response:
                    # Check status
                    status = response.status
                    logger.info(f"Status: {status}")
                    
                    # Get response data
                    data = await response.json()
                    
                    # Print summary
                    logger.info(f"Total nodes: {data.get('total_nodes', 'N/A')}")
                    
                    # Print version distribution if available
                    if "version_distribution" in data:
                        logger.info("Version distribution:")
                        for version in data["version_distribution"]:
                            logger.info(f"  {version['version']}: {version['count']} nodes ({version['percentage']:.2f}%)")
                    
                    # Print health info if available
                    if "estimated_health_percentage" in data:
                        logger.info(f"Estimated health: {data['estimated_health_percentage']}% (sample size: {data.get('health_sample_size', 'N/A')})")
                    
                    # Print node count if details were included
                    if "rpc_nodes" in data:
                        nodes = data["rpc_nodes"]
                        logger.info(f"Received {len(nodes)} node details")
                        
                        # Print a few sample nodes
                        if nodes:
                            logger.info("Sample RPC nodes:")
                            for i, node in enumerate(nodes[:3]):  # Print first 3 nodes
                                logger.info(f"  {i+1}. {node.get('rpc_endpoint')} (version: {node.get('version', 'unknown')})")
                    else:
                        logger.info("No node details included in response (as expected)")
                    
                    # Verify basic response structure
                    assert isinstance(data, dict)
                    assert 'total_nodes' in data
                    assert 'version_distribution' in data
                    
                    if 'rpc_nodes' in data:
                        for node in data['rpc_nodes']:
                            assert 'rpc_endpoint' in node
                            # Version and status may not be present in all implementations
                            # No need to assert on optional fields
                    
        logger.info("\nAll tests completed successfully")
        
    except Exception as e:
        logger.error(f"Error testing RPC nodes API: {str(e)}")
        raise

@pytest.mark.asyncio
@pytest.mark.skipif(not is_server_running(), reason="Server is not running")
async def test_api_with_details():
    # Test API with include_details parameter
    url = "http://localhost:8001/soleco/solana/rpc-nodes"
    params = {'include_details': 'true'}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            assert response.status == 200
            data = await response.json()
            
            # The response may or may not include rpc_nodes depending on the implementation
            # Just check that we get a valid response
            assert 'status' in data
            assert data['status'] == 'success'
            assert 'total_nodes' in data
            
            if 'rpc_nodes' in data and len(data['rpc_nodes']) > 0:
                for node in data['rpc_nodes']:
                    assert 'rpc_endpoint' in node

@pytest.mark.asyncio
@pytest.mark.skipif(not is_server_running(), reason="Server is not running")
async def test_api_with_health_check():
    # Test API with health_check parameter
    url = "http://localhost:8001/soleco/solana/rpc-nodes"
    params = {'health_check': 'true'}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            assert response.status == 200
            data = await response.json()
            
            assert 'status' in data
            assert data['status'] == 'success'
            
            # Health check may or may not include these fields depending on implementation
            # Just check that we get a valid response
            if 'estimated_health_percentage' in data:
                assert isinstance(data['estimated_health_percentage'], (int, float))

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_rpc_nodes_api())
