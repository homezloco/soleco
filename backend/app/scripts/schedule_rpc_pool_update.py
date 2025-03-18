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
import random
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.scripts.update_rpc_pool import discover_rpc_nodes, test_rpc_endpoints, update_connection_pool
from app.utils.solana_rpc import get_connection_pool

# Configure logging
logger = logging.getLogger(__name__)

# Add a file handler for scheduler-specific logs
file_handler = logging.FileHandler('logs/rpc_scheduler.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Configure console logging
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

logger.setLevel(logging.INFO)

async def check_pool_health():
    """Check the health of the current RPC pool and return True if it needs updating."""
    try:
        # Get the current connection pool
        pool = await get_connection_pool()
        
        # Get stats about the pool
        stats = await pool.get_stats()
        
        # Check if we have enough healthy endpoints
        healthy_count = 0
        rate_limited_count = 0
        
        for endpoint, endpoint_stats in stats.get('endpoint_stats', {}).items():
            success_rate = endpoint_stats.get('success_rate', 0)
            if success_rate > 70:  # Consider endpoints with >70% success rate as healthy
                healthy_count += 1
            
            # Check if endpoint is rate limited
            if hasattr(pool, '_rate_limited_until') and endpoint in pool._rate_limited_until:
                if time.time() < pool._rate_limited_until[endpoint]:
                    rate_limited_count += 1
        
        total_endpoints = len(stats.get('endpoint_stats', {}))
        
        logger.info(f"Pool health check: {healthy_count}/{total_endpoints} healthy endpoints, {rate_limited_count} rate limited")
        
        # If more than 30% of endpoints are rate limited or less than 50% are healthy, we need to update
        if rate_limited_count > total_endpoints * 0.3 or healthy_count < total_endpoints * 0.5:
            logger.warning(f"Pool health is poor: {healthy_count}/{total_endpoints} healthy, {rate_limited_count} rate limited")
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error checking pool health: {str(e)}")
        return True  # If we can't check health, assume we need to update

async def update_rpc_pool(max_test: int, max_endpoints: int, quick_mode: bool = False) -> bool:
    """
    Update the RPC pool with the best performing endpoints.
    
    Args:
        max_test: Maximum number of endpoints to test
        max_endpoints: Maximum number of endpoints to keep in the pool
        quick_mode: If True, use a quicker discovery method
        
    Returns:
        True if the pool was updated successfully, False otherwise
    """
    logger.info(f"Updating RPC pool (quick_mode={quick_mode})")
    
    try:
        # Discover RPC nodes
        endpoints = await discover_rpc_nodes(quick_mode=quick_mode)
        
        if not endpoints:
            logger.warning("No endpoints discovered")
            return False
            
        # Update the connection pool
        return await update_connection_pool(endpoints, max_test, max_endpoints)
        
    except Exception as e:
        logger.error(f"Error updating RPC pool: {str(e)}")
        logger.exception(e)
        return False

async def scheduled_update(interval_hours: float, max_test: int, max_endpoints: int, health_check_interval: float):
    """
    Run the RPC pool update on a schedule.
    
    Args:
        interval_hours: Hours between full updates
        max_test: Maximum number of endpoints to test
        max_endpoints: Maximum number of endpoints to keep in the pool
        health_check_interval: Hours between health checks
    """
    logger.info(f"Starting scheduled RPC pool update with interval={interval_hours}h, health_check={health_check_interval}h")
    
    # Convert hours to seconds
    interval_seconds = interval_hours * 3600
    health_check_seconds = health_check_interval * 3600
    
    # Add jitter to prevent thundering herd
    jitter_factor = 0.1  # 10% jitter
    
    try:
        # Run an initial update immediately
        logger.info("Running initial RPC pool update")
        try:
            await update_rpc_pool(max_test, max_endpoints)
            logger.info("Initial RPC pool update completed successfully")
        except Exception as e:
            logger.error(f"Error during initial RPC pool update: {str(e)}")
            logger.exception(e)
        
        # Main update loop
        while True:
            try:
                # Wait for the health check interval with jitter
                jitter = random.uniform(-jitter_factor, jitter_factor) * health_check_seconds
                next_check = health_check_seconds + jitter
                logger.debug(f"Next health check in {next_check/3600:.2f} hours")
                await asyncio.sleep(next_check)
                
                # Check pool health
                logger.debug("Checking RPC pool health")
                health_status = await check_pool_health()
                logger.info(f"RPC pool health status: {health_status}")
                
                # If pool health is poor, run a quick update
                if health_status:
                    logger.warning("Pool health is poor, running quick update")
                    await update_rpc_pool(max_test, max_endpoints, quick_mode=True)
                    logger.info("Quick RPC pool update completed")
                
                # Check if it's time for a full update
                elapsed = time.time() - (await get_connection_pool()).last_update
                if elapsed >= interval_seconds:
                    logger.info(f"Running scheduled full RPC pool update (elapsed: {elapsed/3600:.2f}h)")
                    await update_rpc_pool(max_test, max_endpoints)
                    logger.info("Scheduled full RPC pool update completed")
                else:
                    logger.debug(f"Not time for full update yet. Next update in {(interval_seconds - elapsed)/3600:.2f} hours")
                
            except asyncio.CancelledError:
                logger.info("RPC pool update task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in RPC pool update scheduler: {str(e)}")
                logger.exception(e)
                # Wait a bit before retrying after an error
                await asyncio.sleep(60)
    
    except asyncio.CancelledError:
        logger.info("RPC pool update scheduler cancelled")
    except Exception as e:
        logger.error(f"Fatal error in RPC pool update scheduler: {str(e)}")
        logger.exception(e)
        raise

async def start_scheduler(interval_hours: float = 12.0, 
                          health_check_interval: float = 1.0,
                          max_test: int = 50, 
                          max_endpoints: int = 10) -> asyncio.Task:
    """
    Start the RPC pool update scheduler as a background task.
    
    Args:
        interval_hours: Hours between full updates
        health_check_interval: Hours between health checks
        max_test: Maximum number of endpoints to test
        max_endpoints: Maximum number of endpoints to keep in the pool
        
    Returns:
        The scheduler task
    """
    logger.info(f"Creating RPC pool scheduler task with interval={interval_hours}h, health_check={health_check_interval}h")
    
    # Create the task
    try:
        task = asyncio.create_task(
            scheduled_update(
                interval_hours=interval_hours,
                max_test=max_test,
                max_endpoints=max_endpoints,
                health_check_interval=health_check_interval
            ),
            name="rpc_pool_scheduler"
        )
        
        # Add done callback to log when the task completes
        def on_task_done(t):
            try:
                # Get the exception if there was one
                exc = t.exception()
                if exc:
                    logger.error(f"RPC pool scheduler task failed with exception: {exc}")
                    logger.exception(exc)
                else:
                    logger.info("RPC pool scheduler task completed successfully")
            except asyncio.CancelledError:
                logger.info("RPC pool scheduler task was cancelled")
            except Exception as e:
                logger.error(f"Error in RPC pool scheduler done callback: {e}")
        
        task.add_done_callback(on_task_done)
        logger.info(f"RPC pool scheduler task created: {task}")
        
        return task
    except Exception as e:
        logger.error(f"Error creating RPC pool scheduler task: {e}")
        logger.exception(e)
        raise

async def main(args):
    """Main function to run the scheduler."""
    logger.info(f"Starting RPC pool update scheduler with interval={args.interval}h, health_check={args.health_check_interval}h")
    
    # Run the scheduled update
    await start_scheduler(
        interval_hours=args.interval,
        max_test=args.max_test,
        max_endpoints=args.max_endpoints,
        health_check_interval=args.health_check_interval
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Schedule periodic updates of the RPC connection pool")
    parser.add_argument("--interval", type=float, default=12.0, help="Full update interval in hours (default: 12)")
    parser.add_argument("--health-check-interval", type=float, default=1.0, help="Health check interval in hours (default: 1)")
    parser.add_argument("--max-test", type=int, default=50, help="Maximum number of endpoints to test (default: 50)")
    parser.add_argument("--max-endpoints", type=int, default=10, help="Maximum number of endpoints to keep in the pool (default: 10)")
    
    args = parser.parse_args()
    
    # Run the main function
    asyncio.run(main(args))
