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
            
            # Make the request
            response = await self.client.get(url, params=params)
            
            # Check for successful response
            if response.status_code == 404:
                # Try alternative endpoint without /api prefix
                alternative_url = url.replace("/api/coins/latest", "/coins/latest")
                logger.warning(f"API endpoint not found, trying alternative URL: {alternative_url}")
                response = await self.client.get(alternative_url, params=params)
                
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Check if the response contains the expected data
            if not isinstance(data, list):
                logger.warning(f"Unexpected response format from Pump.fun API: {data}")
                return []
                
            logger.info(f"Successfully fetched {len(data)} tokens from Pump.fun API")
            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"Error fetching latest tokens: {e.response.status_code} {e.response.reason_phrase}")
            logger.error(f"Response content: {e.response.text}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Error fetching latest tokens: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching latest tokens: {str(e)}")
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
