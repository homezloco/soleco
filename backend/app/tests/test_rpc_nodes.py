"""
Test for the RPC Node Extractor functionality
"""
import asyncio
import logging
from ..utils.handlers.rpc_node_extractor import RPCNodeExtractor
from ..utils.solana_query import SolanaQueryHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_rpc_node_extractor():
    """Test the RPC node extractor functionality."""
    try:
        # Create a query handler
        query_handler = SolanaQueryHandler()
        
        # Create an RPC node extractor
        extractor = RPCNodeExtractor(query_handler)
        
        # Get RPC nodes
        result = await extractor.get_all_rpc_nodes()
        
        # Print the result
        logger.info(f"Found {result.get('total_rpc_nodes', 0)} RPC nodes")
        logger.info(f"Version distribution: {result.get('version_distribution', [])}")
        
        # Print a few sample nodes
        nodes = result.get('rpc_nodes', [])
        if nodes:
            logger.info("Sample RPC nodes:")
            for i, node in enumerate(nodes[:5]):  # Print first 5 nodes
                logger.info(f"  {i+1}. {node.get('rpc_endpoint')} (version: {node.get('version', 'unknown')})")
        
        return result
    except Exception as e:
        logger.error(f"Error testing RPC node extractor: {str(e)}")
        raise

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_rpc_node_extractor())
    print(f"Test completed with status: {result.get('status', 'unknown')}")
