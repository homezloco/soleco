"""
Scheduled task to collect and store Pump.fun token data for historical analysis.
"""
import logging
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os
import json

from app.database.sqlite import DatabaseCache
from app.config import Config

# Configure logging
logger = logging.getLogger("app.tasks.pump_data_collector")

class PumpDataCollector:
    """
    Collects and stores Pump.fun token data for historical analysis.
    """
    def __init__(self):
        """Initialize the data collector."""
        self.db = DatabaseCache()
        self.client = httpx.AsyncClient(timeout=60.0)
        self.api_url = Config.PUMPFUN_API_URL
        
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        
    async def fetch_latest_tokens(self, limit: int = 100, include_nsfw: bool = True) -> List[Dict[str, Any]]:
        """
        Fetch the latest tokens from Pump.fun API.
        
        Args:
            limit: Maximum number of tokens to fetch
            include_nsfw: Whether to include NSFW tokens
            
        Returns:
            List of token data
        """
        try:
            # Build the URL with parameters
            url = f"{self.api_url}/coins/latest"
            params = {
                "qty": limit,
                "includeNsfw": str(include_nsfw).lower()
            }
            
            logger.info(f"Fetching latest tokens from Pump.fun API: {url}")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Fetched {len(data)} tokens from Pump.fun API")
            return data
        except Exception as e:
            logger.error(f"Error fetching latest tokens: {e}")
            return []
            
    async def store_token_data(self, tokens: List[Dict[str, Any]]) -> int:
        """
        Store token data in the database.
        
        Args:
            tokens: List of token data
            
        Returns:
            Number of tokens stored
        """
        stored_count = 0
        for token in tokens:
            if self.db.store_token_performance(token):
                stored_count += 1
                
        logger.info(f"Stored {stored_count} tokens in the database")
        return stored_count
        
    async def run(self):
        """Run the data collection task."""
        try:
            logger.info("Starting Pump.fun data collection task")
            
            # Fetch latest tokens
            tokens = await self.fetch_latest_tokens(limit=100)
            
            if tokens:
                # Store token data
                await self.store_token_data(tokens)
                
            logger.info("Pump.fun data collection task completed")
        except Exception as e:
            logger.error(f"Error in Pump.fun data collection task: {e}")
        finally:
            await self.close()


async def run_data_collection():
    """Run the data collection task."""
    try:
        collector = PumpDataCollector()
        await collector.run()
    except Exception as e:
        logger.error(f"Error in run_data_collection: {e}")
    

if __name__ == "__main__":
    # This allows running the task directly for testing
    asyncio.run(run_data_collection())
