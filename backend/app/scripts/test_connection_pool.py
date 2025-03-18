#!/usr/bin/env python3
"""
Script to test the connection pool with a focus on the Helius endpoint and getBlock method.
"""

import asyncio
import sys
import os
import time
import logging
from typing import Dict, Any, List, Optional

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.utils.solana_rpc import get_connection_pool, SolanaClient
from app.config import HELIUS_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_helius_endpoint():
    """Test if the Helius endpoint is properly configured and working."""
    logger.info("Testing Helius endpoint configuration...")
    
    if not HELIUS_API_KEY:
        logger.warning("HELIUS_API_KEY is not set in the environment variables")
        return False
    
    logger.info(f"HELIUS_API_KEY is set (first 4 chars: {HELIUS_API_KEY[:4]}...)")
    
    # Create a direct client to the Helius endpoint
    helius_endpoint = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    client = SolanaClient(endpoint=helius_endpoint, timeout=10.0)
    
    try:
        # Test basic functionality
        logger.info(f"Testing direct connection to Helius endpoint...")
        version = await client.get_version()
        logger.info(f"Helius endpoint version: {version}")
        
        # Test getSlot method
        try:
            logger.info(f"Testing getSlot method on Helius endpoint...")
            slot = await client.get_slot()
            logger.info(f"Current slot: {slot}")
        except Exception as e:
            logger.warning(f"Error getting slot from Helius endpoint: {str(e)}")
            # Use a reasonable default slot for testing
            slot = 200000000
        
        # Test supported methods
        supported_methods = []
        unsupported_methods = []
        
        # Test getBlock method
        try:
            # Try to get a block a few slots back to ensure it's available
            test_slot = max(0, slot - 5)
            logger.info(f"Testing getBlock method on Helius endpoint for slot {test_slot}...")
            block = await client.get_block(test_slot, max_supported_transaction_version=0)
            
            if block and isinstance(block, dict) and "result" in block:
                num_txns = len(block["result"].get("transactions", []))
                logger.info(f"Successfully retrieved block {test_slot} with {num_txns} transactions")
                supported_methods.append("getBlock")
            else:
                logger.error(f"Failed to retrieve block data from Helius endpoint")
                unsupported_methods.append("getBlock")
        except Exception as e:
            logger.error(f"Error testing getBlock on Helius endpoint: {str(e)}")
            if "API key is not allowed to access blockchain" in str(e):
                logger.warning("Helius API key does not have permission to access blockchain data. This may require a paid plan.")
            elif "Method not found" in str(e):
                logger.warning("The getBlock method is not supported by the Helius endpoint")
                unsupported_methods.append("getBlock")
            else:
                unsupported_methods.append("getBlock")
        
        # Log supported and unsupported methods
        if supported_methods:
            logger.info(f"Helius endpoint supports these methods: {', '.join(supported_methods)}")
        if unsupported_methods:
            logger.warning(f"Helius endpoint does NOT support these methods: {', '.join(unsupported_methods)}")
            
        # Return success if we could at least connect and get version info
        return True
            
    except Exception as e:
        logger.error(f"Error testing Helius endpoint: {str(e)}")
        return False
    finally:
        await client.close()

async def test_pool():
    """Test the connection pool by making multiple requests."""
    # First test the Helius endpoint directly
    helius_working = await test_helius_endpoint()
    
    # Get the connection pool
    pool = await get_connection_pool()
    
    # Print the current endpoints
    logger.info(f"Connection pool has {len(pool.endpoints)} endpoints")
    logger.info(f"First 5 endpoints:")
    for i, endpoint in enumerate(pool.endpoints[:5]):
        logger.info(f"  {i+1}. {endpoint}")
    
    # Check if Helius is the first endpoint
    if pool.endpoints and "helius-rpc.com" in pool.endpoints[0]:
        logger.info(" Helius endpoint is correctly set as the first endpoint in the pool")
    else:
        logger.warning(" Helius endpoint is NOT the first endpoint in the pool")
    
    # Make multiple requests to test the pool
    logger.info("Making requests to test getBlock method...")
    
    # Get the current slot
    client = await pool.get_client()
    try:
        try:
            slot = await client.get_slot()
            logger.info(f"Current slot: {slot}")
        except Exception as e:
            logger.error(f"Error getting current slot: {str(e)}")
            slot = 200000000  # Use a reasonable default slot
    finally:
        await pool.release(client)
    
    # Test getBlock with different slots
    test_slots = [slot - i * 10 for i in range(1, 6)]  # Test 5 different slots
    
    # Track endpoints that support and don't support getBlock
    endpoints_supporting_getblock = set()
    endpoints_not_supporting_getblock = set()
    
    for i, test_slot in enumerate(test_slots):
        start_time = time.time()
        
        # Get a client from the pool
        client = await pool.get_client()
        try:
            # Make a request
            result = await client.get_block(test_slot, max_supported_transaction_version=0)
            endpoint = client.endpoint
            elapsed = time.time() - start_time
            
            # Add to supporting endpoints
            endpoints_supporting_getblock.add(endpoint)
            
            if result and isinstance(result, dict) and "result" in result:
                num_txns = len(result["result"].get("transactions", []))
                logger.info(f"Request {i+1}: {endpoint} - Got block {test_slot} with {num_txns} transactions ({elapsed:.3f}s)")
            else:
                logger.warning(f"Request {i+1}: {endpoint} - Invalid response format for block {test_slot} ({elapsed:.3f}s)")
                
        except Exception as e:
            endpoint = client.endpoint if hasattr(client, 'endpoint') else "unknown"
            elapsed = time.time() - start_time
            
            error_msg = str(e)
            if "Method not found" in error_msg or "does not support getBlock method" in error_msg:
                endpoints_not_supporting_getblock.add(endpoint)
                logger.warning(f"Request {i+1}: {endpoint} - Endpoint does not support getBlock method ({elapsed:.3f}s)")
            elif "API key is not allowed to access blockchain" in error_msg:
                logger.warning(f"Request {i+1}: {endpoint} - API key does not have permission to access blockchain data ({elapsed:.3f}s)")
            else:
                logger.error(f"Request {i+1}: {endpoint} - Error getting block {test_slot}: {error_msg} ({elapsed:.3f}s)")
        finally:
            await pool.release(client)
        
        # Small delay between requests
        await asyncio.sleep(1.0)
    
    # Log summary of endpoint support
    if endpoints_supporting_getblock:
        logger.info(f"Endpoints supporting getBlock: {len(endpoints_supporting_getblock)}")
        for i, endpoint in enumerate(endpoints_supporting_getblock):
            logger.info(f"  {i+1}. {endpoint}")
    
    if endpoints_not_supporting_getblock:
        logger.warning(f"Endpoints NOT supporting getBlock: {len(endpoints_not_supporting_getblock)}")
        for i, endpoint in enumerate(endpoints_not_supporting_getblock):
            logger.warning(f"  {i+1}. {endpoint}")
    
    logger.info("Test completed")

def main():
    """Main function."""
    asyncio.run(test_pool())

if __name__ == "__main__":
    main()
