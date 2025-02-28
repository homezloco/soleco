#!/usr/bin/env python3
"""
Script to test the improved connection pool with prioritized endpoints.
"""

import asyncio
import sys
import os
import time
import logging
import random
from typing import List, Dict, Any

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.utils.solana_rpc import get_connection_pool, SolanaClient, SolanaConnectionPool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def simulate_endpoint_performance(pool: SolanaConnectionPool, num_requests: int = 50) -> None:
    """
    Simulate endpoint performance by making multiple requests and tracking metrics.
    
    Args:
        pool: The connection pool to test
        num_requests: Number of requests to make
    """
    # Track metrics for each endpoint
    endpoint_metrics: Dict[str, Dict[str, Any]] = {}
    
    logger.info(f"Making {num_requests} requests to test endpoint performance...")
    
    for i in range(num_requests):
        # Get a client from the pool
        async with await pool.get_client() as client:
            endpoint = client.endpoint
            
            # Initialize metrics for this endpoint if not already done
            if endpoint not in endpoint_metrics:
                endpoint_metrics[endpoint] = {
                    "requests": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_latency": 0,
                    "avg_latency": 0
                }
            
            # Make a request
            start_time = time.time()
            try:
                # Simulate random success/failure and latency
                # In a real scenario, we'd make an actual RPC call
                await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate network latency
                
                # Simulate occasional failures (10% chance)
                if random.random() < 0.1:
                    raise Exception("Simulated failure")
                
                # Record success
                latency = time.time() - start_time
                endpoint_metrics[endpoint]["requests"] += 1
                endpoint_metrics[endpoint]["successes"] += 1
                endpoint_metrics[endpoint]["total_latency"] += latency
                endpoint_metrics[endpoint]["avg_latency"] = (
                    endpoint_metrics[endpoint]["total_latency"] / 
                    endpoint_metrics[endpoint]["successes"]
                )
                
                logger.info(f"Request {i+1}: {endpoint} - Success ({latency:.3f}s)")
                
            except Exception as e:
                # Record failure
                latency = time.time() - start_time
                endpoint_metrics[endpoint]["requests"] += 1
                endpoint_metrics[endpoint]["failures"] += 1
                
                logger.error(f"Request {i+1}: {endpoint} - Error: {str(e)} ({latency:.3f}s)")
            
        # Small delay between requests
        await asyncio.sleep(0.1)
    
    # Print metrics
    logger.info("\nEndpoint Performance Metrics:")
    for endpoint, metrics in endpoint_metrics.items():
        success_rate = metrics["successes"] / metrics["requests"] * 100 if metrics["requests"] > 0 else 0
        logger.info(f"Endpoint: {endpoint}")
        logger.info(f"  Requests: {metrics['requests']}")
        logger.info(f"  Success Rate: {success_rate:.2f}%")
        logger.info(f"  Avg Latency: {metrics['avg_latency']:.3f}s")
        logger.info("")
    
    # Get the pool's internal stats
    pool_stats = pool._endpoint_stats
    logger.info("\nConnection Pool Internal Stats:")
    for endpoint, stats in pool_stats.items():
        logger.info(f"Endpoint: {endpoint}")
        total = stats["success_count"] + stats["failure_count"]
        success_rate = stats["success_count"] / total * 100 if total > 0 else 0
        logger.info(f"  Success Rate: {success_rate:.2f}%")
        logger.info(f"  Avg Latency: {stats['avg_latency']:.3f}s")
        logger.info(f"  Current Failures: {stats.get('current_failures', 0)}")
        logger.info("")

async def test_endpoint_prioritization(pool: SolanaConnectionPool) -> None:
    """
    Test that endpoints are properly prioritized based on performance.
    
    Args:
        pool: The connection pool to test
    """
    # First, simulate some endpoint performance to build up metrics
    await simulate_endpoint_performance(pool, num_requests=30)
    
    # Get the current endpoint order
    original_endpoints = pool.endpoints.copy()
    logger.info("\nOriginal endpoint order:")
    for i, endpoint in enumerate(original_endpoints[:5]):
        logger.info(f"  {i+1}. {endpoint}")
    
    # Sort endpoints by performance
    sorted_endpoints = await pool.sort_endpoints_by_performance()
    logger.info("\nSorted endpoint order:")
    for i, endpoint in enumerate(sorted_endpoints[:5]):
        logger.info(f"  {i+1}. {endpoint}")
    
    # Update the pool with the sorted endpoints
    await pool.update_endpoints(sorted_endpoints)
    
    # Get the new endpoint order
    new_endpoints = pool.endpoints.copy()
    logger.info("\nNew endpoint order after update:")
    for i, endpoint in enumerate(new_endpoints[:5]):
        logger.info(f"  {i+1}. {endpoint}")
    
    # Verify that the Helius endpoint is still first
    helius_endpoint = next((ep for ep in new_endpoints if "helius-rpc.com" in ep), None)
    if helius_endpoint and new_endpoints[0] == helius_endpoint:
        logger.info("\nHelius endpoint is correctly prioritized as the first endpoint.")
    else:
        logger.warning("\nHelius endpoint is not the first endpoint in the list!")

async def test_pool():
    """Test the improved connection pool."""
    # Get the connection pool
    pool = await get_connection_pool()
    
    # Print the current endpoints
    logger.info(f"Connection pool has {len(pool.endpoints)} endpoints")
    logger.info(f"First 5 endpoints:")
    for i, endpoint in enumerate(pool.endpoints[:5]):
        logger.info(f"  {i+1}. {endpoint}")
    
    # Test endpoint performance
    await simulate_endpoint_performance(pool, num_requests=20)
    
    # Test endpoint prioritization
    await test_endpoint_prioritization(pool)
    
    logger.info("Test completed")

def main():
    """Main function."""
    asyncio.run(test_pool())

if __name__ == "__main__":
    main()
