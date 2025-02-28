#!/usr/bin/env python3
"""
Script to test the connection pool.
"""

import asyncio
import sys
import os
import time
import logging

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.utils.solana_rpc import get_connection_pool, SolanaClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_pool():
    """Test the connection pool by making multiple requests."""
    # Get the connection pool
    pool = await get_connection_pool()
    
    # Print the current endpoints
    logger.info(f"Connection pool has {len(pool.endpoints)} endpoints")
    logger.info(f"First 5 endpoints:")
    for i, endpoint in enumerate(pool.endpoints[:5]):
        logger.info(f"  {i+1}. {endpoint}")
    
    # Make multiple requests to test the pool
    logger.info("Making 10 requests to test the pool...")
    
    for i in range(10):
        start_time = time.time()
        
        # Get a client from the pool
        async with await pool.get_client() as client:
            # Make a request
            try:
                result = await client._make_rpc_call("getHealth", [])
                endpoint = client.endpoint
                elapsed = time.time() - start_time
                logger.info(f"Request {i+1}: {endpoint} - {result.get('result', 'unknown')} ({elapsed:.3f}s)")
            except Exception as e:
                endpoint = client.endpoint if hasattr(client, 'endpoint') else "unknown"
                elapsed = time.time() - start_time
                logger.error(f"Request {i+1}: {endpoint} - Error: {str(e)} ({elapsed:.3f}s)")
        
        # Small delay between requests
        await asyncio.sleep(0.5)
    
    logger.info("Test completed")

def main():
    """Main function."""
    asyncio.run(test_pool())

if __name__ == "__main__":
    main()
