"""
Schedule RPC Pool Update Script

This script sets up a scheduled task to periodically update the RPC pool
with the best performing nodes. It uses the update_rpc_pool.py script
to discover, test, and update the connection pool.

Usage:
    python -m app.scripts.schedule_rpc_pool_update
"""

import asyncio
import time
import logging
import argparse
import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.scripts.update_rpc_pool import discover_rpc_nodes, test_rpc_endpoints, update_connection_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def scheduled_update(interval_hours: int, max_test: int, max_endpoints: int):
    """Run the RPC pool update on a schedule."""
    while True:
        try:
            logger.info(f"Starting scheduled RPC pool update at {datetime.now()}")
            
            # Discover RPC nodes
            endpoints = await discover_rpc_nodes()
            
            if not endpoints:
                logger.error("No RPC nodes discovered. Skipping update.")
            else:
                # Test the endpoints
                test_results = await test_rpc_endpoints(endpoints, max_test)
                
                # Update the connection pool
                await update_connection_pool(test_results, max_endpoints)
                
                logger.info(f"Scheduled update completed successfully at {datetime.now()}")
            
            # Calculate next run time
            next_run = datetime.now() + timedelta(hours=interval_hours)
            logger.info(f"Next update scheduled for {next_run}")
            
            # Sleep until next run
            await asyncio.sleep(interval_hours * 3600)
        
        except Exception as e:
            logger.error(f"Error during scheduled update: {str(e)}")
            # Sleep for 1 hour before retrying after an error
            logger.info("Retrying in 1 hour...")
            await asyncio.sleep(3600)

async def main(args):
    """Main function to run the scheduler."""
    logger.info(f"Starting RPC pool update scheduler")
    logger.info(f"Update interval: {args.interval} hours")
    logger.info(f"Max endpoints to test: {args.max_test}")
    logger.info(f"Max endpoints to add to pool: {args.max_endpoints}")
    
    # Run the scheduled update
    await scheduled_update(args.interval, args.max_test, args.max_endpoints)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Schedule periodic updates of the RPC connection pool")
    parser.add_argument("--interval", type=int, default=24, help="Update interval in hours (default: 24)")
    parser.add_argument("--max-test", type=int, default=50, help="Maximum number of endpoints to test")
    parser.add_argument("--max-endpoints", type=int, default=15, help="Maximum number of endpoints to add to the pool")
    
    args = parser.parse_args()
    
    # Run the main function
    asyncio.run(main(args))
