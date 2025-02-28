"""
RPC Node Health Test Runner

This script runs the RPC node health test and displays the results.
"""

import asyncio
import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.tests.test_rpc_nodes_health import main

if __name__ == "__main__":
    print("Running RPC Node Health Test...")
    asyncio.run(main())
