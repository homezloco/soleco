#!/usr/bin/env python3
"""
Script to check the current connection pool.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.utils.solana_rpc import get_connection_pool

async def check_pool():
    """Check the current connection pool."""
    pool = await get_connection_pool()
    print(f"Current connection pool endpoints:")
    for i, endpoint in enumerate(pool.endpoints):
        print(f"  {i+1}. {endpoint}")
    print(f"Current connection pool size: {pool.pool_size}")
    # The _clients attribute doesn't exist, so we'll skip it

def main():
    """Main function."""
    asyncio.run(check_pool())

if __name__ == "__main__":
    main()
