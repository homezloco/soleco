#!/usr/bin/env python3
"""
Script to reset the connection pool and initialize it from scratch.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.utils.solana_rpc import get_connection_pool, SolanaConnectionPool, DEFAULT_RPC_ENDPOINTS

async def reset_pool():
    """Reset the connection pool and initialize it from scratch."""
    # Get the current connection pool
    global_pool = await get_connection_pool()
    
    # Print the current endpoints
    print(f"Current connection pool endpoints:")
    for i, endpoint in enumerate(global_pool.endpoints):
        print(f"  {i+1}. {endpoint}")
    print(f"Current connection pool size: {global_pool.pool_size}")
    
    # Print the DEFAULT_RPC_ENDPOINTS
    print(f"\nDEFAULT_RPC_ENDPOINTS:")
    for i, endpoint in enumerate(DEFAULT_RPC_ENDPOINTS):
        print(f"  {i+1}. {endpoint}")
    
    # Create a new connection pool with the DEFAULT_RPC_ENDPOINTS
    print(f"\nCreating a new connection pool with DEFAULT_RPC_ENDPOINTS...")
    new_pool = SolanaConnectionPool(
        endpoints=DEFAULT_RPC_ENDPOINTS,
        pool_size=5,
        max_retries=3,
        retry_delay=1.0,
        timeout=10.0
    )
    await new_pool.initialize()
    
    # Print the new endpoints
    print(f"\nNew connection pool endpoints:")
    for i, endpoint in enumerate(new_pool.endpoints):
        print(f"  {i+1}. {endpoint}")
    print(f"New connection pool size: {new_pool.pool_size}")

def main():
    """Main function."""
    asyncio.run(reset_pool())

if __name__ == "__main__":
    main()
