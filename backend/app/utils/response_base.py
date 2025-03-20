"""
Base response handler classes for Solana RPC responses.
"""

import logging
import time
from typing import Any, Dict, Optional, TypeVar

from .solana_types import EndpointConfig, RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar('T')

class SolanaResponseManager:
    """Manager for Solana responses with rate limiting and error handling"""
    
    def __init__(self, config: EndpointConfig):
        """Initialize with endpoint configuration"""
        self.config = config
        self.last_request_time = 0
        self.request_count = 0
        
    def track_request(self):
        """Track a request for rate limiting purposes"""
        current_time = time.time()
        time_diff = current_time - self.last_request_time
        
        # Reset counter if more than 1 second has passed
        if time_diff > 1.0:
            self.request_count = 0
            
        self.request_count += 1
        self.last_request_time = current_time
        
        # Check if we're exceeding rate limits
        if self.request_count > self.config.burst_limit:
            raise RateLimitError(f"Exceeded burst limit of {self.config.burst_limit} requests")
            
        # Sleep if we're approaching the rate limit
        if self.request_count > self.config.requests_per_second:
            sleep_time = 1.0 - time_diff
            if sleep_time > 0:
                time.sleep(sleep_time)

    async def handle_response(self, response: Any) -> Any:
        """Handle a Solana response with rate limiting and error handling"""
        try:
            # Track request
            self.track_request()
            
            # Process response
            return response
            
        except Exception as e:
            logger.error(f"Error handling response: {str(e)}")
            raise

class ResponseHandler:
    """Base handler for Solana responses with error handling"""
    
    def __init__(self, response_manager: Optional[SolanaResponseManager] = None):
        """Initialize with optional response manager"""
        self.response_manager = response_manager
        
    async def process_block(self, block_data: Any) -> Dict[str, Any]:
        """Process a block with comprehensive error handling and statistics tracking"""
        try:
            # Process block through response manager
            try:
                if self.response_manager:
                    result = await self.response_manager.handle_response(block_data)
                else:
                    result = block_data
                    
                if not result:
                    raise ValueError("Failed to process block data")
                    
                return {
                    "success": True,
                    "result": result
                }
                
            except Exception as e:
                logger.error(f"Error processing block data: {str(e)}")
                return {
                    "success": False,
                    "error": f"Failed to process block: {str(e)}",
                    "result": None
                }
                
        except Exception as e:
            logger.error(f"Error processing block: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
