"""
Test script for Solana endpoints.
"""
import asyncio
import httpx
import json
import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import the FastAPI app
from app.main import app

async def test_solana_endpoints():
    """Test all Solana endpoints"""
    print("Testing Solana endpoints...")
    
    # Create a test client
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Health monitoring endpoints
        print("\nTesting health monitoring endpoints:")
        health_response = await client.get("/solana/health/endpoints")
        print(f"GET /solana/health/endpoints: {health_response.status_code}")
        if health_response.status_code == 200:
            endpoints = health_response.json()
            if endpoints and len(endpoints) > 0:
                endpoint = endpoints[0]["endpoint"]
                detail_response = await client.get(f"/solana/health/endpoints/{endpoint}")
                print(f"GET /solana/health/endpoints/{endpoint}: {detail_response.status_code}")
        
        # RPC pool management endpoints
        print("\nTesting RPC pool management endpoints:")
        status_response = await client.get("/solana/rpc-pool/status")
        print(f"GET /solana/rpc-pool/status: {status_response.status_code}")
        
        rotate_response = await client.post("/solana/rpc-pool/rotate")
        print(f"POST /solana/rpc-pool/rotate: {rotate_response.status_code}")
        
        endpoints_response = await client.get("/solana/rpc-pool/endpoints")
        print(f"GET /solana/rpc-pool/endpoints: {endpoints_response.status_code}")
        
        # Network performance metrics endpoints
        print("\nTesting network performance metrics endpoints:")
        tps_response = await client.get("/solana/metrics/tps")
        print(f"GET /solana/metrics/tps: {tps_response.status_code}")
        
        blocktime_response = await client.get("/solana/metrics/blocktime")
        print(f"GET /solana/metrics/blocktime: {blocktime_response.status_code}")
        
        # Advanced analytics endpoints
        print("\nTesting advanced analytics endpoints:")
        token_mints_response = await client.get("/solana/analytics/token-mints")
        print(f"GET /solana/analytics/token-mints: {token_mints_response.status_code}")
        
        pump_tokens_response = await client.get("/solana/analytics/pump-tokens")
        print(f"GET /solana/analytics/pump-tokens: {pump_tokens_response.status_code}")
        
        dex_activity_response = await client.get("/solana/analytics/dex-activity")
        print(f"GET /solana/analytics/dex-activity: {dex_activity_response.status_code}")
        
        print("\nAll tests completed.")

if __name__ == "__main__":
    asyncio.run(test_solana_endpoints())
