"""
Test client for the RPC Nodes API endpoint
"""
import asyncio
import aiohttp
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_rpc_nodes_api():
    """Test the RPC nodes API endpoint."""
    try:
        # API endpoint URL
        url = "http://localhost:8000/solana/network/rpc-nodes"
        
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
                    logger.info(f"Total RPC nodes: {data.get('total_rpc_nodes', 'N/A')}")
                    
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
                    
        logger.info("\nAll tests completed successfully")
        
    except Exception as e:
        logger.error(f"Error testing RPC nodes API: {str(e)}")
        raise

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_rpc_nodes_api())
