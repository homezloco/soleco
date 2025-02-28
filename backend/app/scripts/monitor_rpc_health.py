#!/usr/bin/env python3
"""
Script to monitor the health of Solana RPC endpoints in the connection pool.

This script periodically checks the health of all endpoints in the connection pool
and updates their performance metrics. It also logs the top performing endpoints.

Usage:
    python -m app.scripts.monitor_rpc_health [--interval SECONDS] [--daemon]

Options:
    --interval SECONDS    Interval between health checks in seconds (default: 300)
    --daemon              Run in daemon mode (continuous monitoring)
"""

import asyncio
import argparse
import logging
import sys
import time
import signal
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Import connection pool utilities
from app.utils.solana_rpc import get_connection_pool, SolanaConnectionPool

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """Handle termination signals for graceful shutdown."""
    global running
    logger.info("Received termination signal, shutting down...")
    running = False

async def monitor_endpoint_health(interval: int = 300, daemon: bool = False) -> None:
    """
    Continuously monitor the health of all endpoints in the connection pool.
    
    Args:
        interval: Interval between health checks in seconds (default: 300)
        daemon: Whether to run in daemon mode (continuous monitoring)
    """
    logger.info(f"Starting RPC endpoint health monitoring (interval: {interval}s, daemon: {daemon})")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    global running
    running = True
    
    try:
        while running:
            try:
                # Get the connection pool
                pool = await get_connection_pool()
                
                # Log current pool state before health check
                logger.info(f"Current connection pool has {len(pool.endpoints)} endpoints")
                logger.info(f"Top 5 current endpoints:")
                for i, endpoint in enumerate(pool.endpoints[:5]):
                    logger.info(f"  {i+1}. {endpoint}")
                
                # Check the health of all endpoints
                await pool.check_all_endpoints_health()
                
                # Log the current stats
                stats = await pool.get_stats()
                
                logger.info(f"Connection pool stats:")
                logger.info(f"  Total endpoints: {len(pool.endpoints)}")
                logger.info(f"  Active clients: {stats.get('active_clients', 0)}")
                logger.info(f"  Available clients: {stats.get('available_clients', 0)}")
                
                # Get top performers from the stats
                top_performers = stats.get('top_performers', [])
                if top_performers:
                    logger.info(f"Top 5 performing endpoints:")
                    for i, performer in enumerate(top_performers[:5]):
                        logger.info(f"  {i+1}. {performer.get('endpoint', 'Unknown')} - " +
                                   f"Success Rate: {performer.get('success_rate', 0):.2f}, " +
                                   f"Avg Latency: {performer.get('avg_latency', 0):.3f}s")
                
                # Wait for the next check
                if not daemon and not running:
                    break
                    
                logger.info(f"Next health check in {interval} seconds")
                for _ in range(interval):
                    if not running:
                        break
                    await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {str(e)}")
                # Print exception traceback for debugging
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(60)  # Wait a minute before retrying
                
            if not daemon:
                break
                
    finally:
        logger.info("Health monitoring stopped")

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Monitor Solana RPC endpoint health")
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Interval between health checks in seconds (default: 300)"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in daemon mode (continuous monitoring)"
    )
    return parser.parse_args()

async def main() -> None:
    """Main entry point."""
    args = parse_args()
    await monitor_endpoint_health(args.interval, args.daemon)

if __name__ == "__main__":
    asyncio.run(main())
