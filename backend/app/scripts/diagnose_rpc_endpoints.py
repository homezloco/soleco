#!/usr/bin/env python3
"""
Script to diagnose and troubleshoot Solana RPC endpoint issues.

This script tests RPC endpoints for various issues including:
- SSL certificate problems
- Rate limiting
- API key restrictions
- Performance metrics

Usage:
    python diagnose_rpc_endpoints.py [--endpoints ENDPOINT1 ENDPOINT2 ...] [--ssl-bypass] [--verbose]
"""

import asyncio
import argparse
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("rpc-diagnostics")

# Import app modules
sys.path.append(".")  # Add current directory to path
from app.utils.solana_rpc import SolanaClient
from app.utils.solana_rpc_constants import DEFAULT_RPC_ENDPOINTS
from app.utils.solana_ssl_config import should_bypass_ssl_verification, add_ssl_bypass_endpoint

async def diagnose_endpoint(endpoint: str, ssl_bypass: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """
    Run comprehensive diagnostics on a single RPC endpoint.
    
    Args:
        endpoint: The RPC endpoint URL to diagnose
        ssl_bypass: Whether to bypass SSL verification
        verbose: Whether to print verbose output
        
    Returns:
        Dictionary with diagnostic results
    """
    result = {
        "endpoint": endpoint,
        "timestamp": datetime.now().isoformat(),
        "ssl_verified": not ssl_bypass,
        "tests": {},
        "overall_status": "failed",
        "issues": []
    }
    
    # Check if endpoint should bypass SSL verification
    if should_bypass_ssl_verification(endpoint):
        ssl_bypass = True
        result["ssl_verified"] = False
        logger.info(f"Endpoint {endpoint} is in SSL bypass list")
    
    # Create client with appropriate SSL settings
    client = None
    try:
        client = SolanaClient(
            endpoint=endpoint,
            timeout=10.0,
            max_retries=1,  # Use only 1 retry for diagnostics
            ssl_verify=not ssl_bypass
        )
        
        # Test connection
        start_time = time.time()
        await client.connect()
        connection_time = time.time() - start_time
        result["tests"]["connection"] = {
            "status": "success",
            "latency": connection_time,
            "error": None
        }
        if verbose:
            logger.info(f"Connection test successful: {connection_time:.3f}s")
        
        # Test getHealth
        try:
            start_time = time.time()
            health = await client.get_health()
            health_time = time.time() - start_time
            result["tests"]["health"] = {
                "status": "success",
                "latency": health_time,
                "result": health,
                "error": None
            }
            if verbose:
                logger.info(f"Health test successful: {health_time:.3f}s, result: {health}")
        except Exception as e:
            result["tests"]["health"] = {
                "status": "failed",
                "error": str(e)
            }
            result["issues"].append(f"Health check failed: {str(e)}")
            if verbose:
                logger.error(f"Health test failed: {str(e)}")
        
        # Test getVersion
        try:
            start_time = time.time()
            version = await client.get_version()
            version_time = time.time() - start_time
            result["tests"]["version"] = {
                "status": "success",
                "latency": version_time,
                "result": version,
                "error": None
            }
            if verbose:
                logger.info(f"Version test successful: {version_time:.3f}s, result: {version}")
        except Exception as e:
            result["tests"]["version"] = {
                "status": "failed",
                "error": str(e)
            }
            result["issues"].append(f"Version check failed: {str(e)}")
            if verbose:
                logger.error(f"Version test failed: {str(e)}")
        
        # Test getSlot
        try:
            start_time = time.time()
            slot = await client.get_slot()
            slot_time = time.time() - start_time
            result["tests"]["slot"] = {
                "status": "success",
                "latency": slot_time,
                "result": slot,
                "error": None
            }
            if verbose:
                logger.info(f"Slot test successful: {slot_time:.3f}s, result: {slot}")
        except Exception as e:
            result["tests"]["slot"] = {
                "status": "failed",
                "error": str(e)
            }
            result["issues"].append(f"Slot check failed: {str(e)}")
            if verbose:
                logger.error(f"Slot test failed: {str(e)}")
        
        # Test getBlock
        try:
            start_time = time.time()
            # Get a recent block (10 blocks behind current slot to ensure it's available)
            slot_value = result["tests"].get("slot", {}).get("result", 0)
            if slot_value > 10:
                options = {
                    "encoding": "json",
                    "transactionDetails": "full",
                    "maxSupportedTransactionVersion": 0
                }
                block = await client.get_block(slot_value - 10, options)
                block_time = time.time() - start_time
                result["tests"]["block"] = {
                    "status": "success",
                    "latency": block_time,
                    "error": None
                }
                if verbose:
                    logger.info(f"Block test successful: {block_time:.3f}s")
            else:
                result["tests"]["block"] = {
                    "status": "skipped",
                    "error": "No valid slot available"
                }
                if verbose:
                    logger.warning("Block test skipped: No valid slot available")
        except Exception as e:
            result["tests"]["block"] = {
                "status": "failed",
                "error": str(e)
            }
            result["issues"].append(f"Block retrieval failed: {str(e)}")
            if verbose:
                logger.error(f"Block test failed: {str(e)}")
        
        # Check for rate limiting
        rate_limit_detected = False
        for test_name, test_result in result["tests"].items():
            if test_result.get("error") and any(x in str(test_result["error"]).lower() for x in ["rate limit", "too many request", "429"]):
                rate_limit_detected = True
                result["issues"].append(f"Rate limiting detected in {test_name} test")
        
        if rate_limit_detected:
            result["rate_limited"] = True
            if verbose:
                logger.warning(f"Rate limiting detected for endpoint {endpoint}")
        
        # Check for API key issues
        api_key_issue = False
        for test_name, test_result in result["tests"].items():
            if test_result.get("error") and any(x in str(test_result["error"]).lower() for x in ["api key", "unauthorized", "forbidden", "auth"]):
                api_key_issue = True
                result["issues"].append(f"API key issue detected in {test_name} test")
        
        if api_key_issue:
            result["api_key_issue"] = True
            if verbose:
                logger.warning(f"API key issue detected for endpoint {endpoint}")
        
        # Check for SSL issues
        ssl_issue = False
        for test_name, test_result in result["tests"].items():
            if test_result.get("error") and any(x in str(test_result["error"]).lower() for x in ["ssl", "certificate", "verify"]):
                ssl_issue = True
                result["issues"].append(f"SSL issue detected in {test_name} test")
        
        if ssl_issue:
            result["ssl_issue"] = True
            if verbose:
                logger.warning(f"SSL issue detected for endpoint {endpoint}")
            
            # Add to SSL bypass list if SSL issue detected
            if not ssl_bypass:
                add_ssl_bypass_endpoint(endpoint)
                logger.info(f"Added {endpoint} to SSL bypass list due to SSL issues")
                
                # Retry with SSL bypass
                if verbose:
                    logger.info(f"Retrying endpoint {endpoint} with SSL verification disabled")
                return await diagnose_endpoint(endpoint, ssl_bypass=True, verbose=verbose)
        
        # Determine overall status
        successful_tests = sum(1 for test in result["tests"].values() if test.get("status") == "success")
        total_tests = len(result["tests"])
        
        if successful_tests == total_tests:
            result["overall_status"] = "success"
        elif successful_tests > 0:
            result["overall_status"] = "partial"
        else:
            result["overall_status"] = "failed"
        
        # Calculate average latency for successful tests
        latencies = [test.get("latency", 0) for test in result["tests"].values() 
                    if test.get("status") == "success" and "latency" in test]
        if latencies:
            result["average_latency"] = sum(latencies) / len(latencies)
        
        return result
    except Exception as e:
        result["connection_error"] = str(e)
        result["issues"].append(f"Connection failed: {str(e)}")
        
        # Check for SSL issues in connection error
        if "SSL" in str(e) or "certificate" in str(e).lower():
            result["ssl_issue"] = True
            if verbose:
                logger.warning(f"SSL issue detected for endpoint {endpoint}")
            
            # Add to SSL bypass list if SSL issue detected
            if not ssl_bypass:
                add_ssl_bypass_endpoint(endpoint)
                logger.info(f"Added {endpoint} to SSL bypass list due to SSL issues")
                
                # Retry with SSL bypass
                if verbose:
                    logger.info(f"Retrying endpoint {endpoint} with SSL verification disabled")
                return await diagnose_endpoint(endpoint, ssl_bypass=True, verbose=verbose)
        
        if verbose:
            logger.error(f"Connection to {endpoint} failed: {str(e)}")
        return result
    finally:
        # Ensure client is closed
        if client:
            try:
                await client.close()
            except Exception as e:
                if verbose:
                    logger.debug(f"Error closing client: {str(e)}")

async def diagnose_endpoints(endpoints: List[str], ssl_bypass: bool = False, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Run diagnostics on multiple endpoints.
    
    Args:
        endpoints: List of RPC endpoint URLs to diagnose
        ssl_bypass: Whether to bypass SSL verification
        verbose: Whether to print verbose output
        
    Returns:
        List of diagnostic results
    """
    results = []
    
    for endpoint in endpoints:
        logger.info(f"Diagnosing endpoint: {endpoint}")
        result = await diagnose_endpoint(endpoint, ssl_bypass, verbose)
        results.append(result)
        
        # Print summary
        status_emoji = "✅" if result["overall_status"] == "success" else "⚠️" if result["overall_status"] == "partial" else "❌"
        issues = len(result["issues"])
        latency = result.get("average_latency", float('inf'))
        latency_str = f"{latency:.3f}s" if latency != float('inf') else "N/A"
        
        print(f"{status_emoji} {endpoint} - Status: {result['overall_status'].upper()}, Issues: {issues}, Latency: {latency_str}")
        
        # Print issues if any
        if result["issues"] and (verbose or result["overall_status"] != "success"):
            for issue in result["issues"]:
                print(f"  - {issue}")
            print()
    
    return results

def print_diagnostics_summary(results: List[Dict[str, Any]]):
    """Print a summary of the diagnostics results."""
    total = len(results)
    successful = sum(1 for r in results if r["overall_status"] == "success")
    partial = sum(1 for r in results if r["overall_status"] == "partial")
    failed = sum(1 for r in results if r["overall_status"] == "failed")
    
    print("\n=== DIAGNOSTICS SUMMARY ===")
    print(f"Total endpoints tested: {total}")
    print(f"Successful: {successful} ({successful/total*100:.1f}%)")
    print(f"Partial success: {partial} ({partial/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    
    # Count specific issues
    ssl_issues = sum(1 for r in results if r.get("ssl_issue", False))
    rate_limited = sum(1 for r in results if r.get("rate_limited", False))
    api_key_issues = sum(1 for r in results if r.get("api_key_issue", False))
    
    if ssl_issues:
        print(f"SSL issues: {ssl_issues} ({ssl_issues/total*100:.1f}%)")
    if rate_limited:
        print(f"Rate limited: {rate_limited} ({rate_limited/total*100:.1f}%)")
    if api_key_issues:
        print(f"API key issues: {api_key_issues} ({api_key_issues/total*100:.1f}%)")
    
    # Find fastest endpoint
    valid_results = [r for r in results if "average_latency" in r]
    if valid_results:
        fastest = min(valid_results, key=lambda x: x["average_latency"])
        print(f"\nFastest endpoint: {fastest['endpoint']} ({fastest['average_latency']:.3f}s)")
    
    print("========================")

async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Diagnose Solana RPC endpoint issues")
    parser.add_argument("--endpoints", nargs="+", help="Specific endpoints to test")
    parser.add_argument("--ssl-bypass", action="store_true", help="Bypass SSL verification for all endpoints")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    # Use provided endpoints or default endpoints
    endpoints = args.endpoints or DEFAULT_RPC_ENDPOINTS
    
    # Run diagnostics
    results = await diagnose_endpoints(endpoints, args.ssl_bypass, args.verbose)
    
    # Print summary
    print_diagnostics_summary(results)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
