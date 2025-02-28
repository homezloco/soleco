"""
Rate limiter implementation for Solana RPC requests.
Uses token bucket algorithm with configurable rates and burst limits.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 40.0  # Default RPS
    burst_limit: int = 80  # Maximum burst size
    min_interval: float = 0.025  # Minimum time between requests (25ms)

class RateLimiter:
    """
    Token bucket rate limiter for RPC requests.
    Supports burst allowance and configurable rates.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config
        self.tokens = config.burst_limit
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "throttled_requests": 0,
            "burst_requests": 0,
            "average_interval": 0.0,
            "last_interval": 0.0
        }

    async def acquire(self) -> None:
        """
        Acquire permission to make a request.
        Raises RateLimitError if limit exceeded.
        """
        async with self.lock:
            now = time.monotonic()
            time_passed = now - self.last_update
            self.last_update = now

            # Replenish tokens based on time passed
            self.tokens = min(
                self.config.burst_limit,
                self.tokens + time_passed * self.config.requests_per_second
            )

            # Check if we can make a request
            if self.tokens < 1.0:
                self.stats["throttled_requests"] += 1
                raise RateLimitError("Rate limit exceeded")

            # Update statistics
            self.stats["total_requests"] += 1
            if self.tokens > self.config.requests_per_second:
                self.stats["burst_requests"] += 1
            
            self.stats["last_interval"] = time_passed
            self.stats["average_interval"] = (
                (self.stats["average_interval"] * (self.stats["total_requests"] - 1) + time_passed) / 
                self.stats["total_requests"]
            )

            # Consume a token
            self.tokens -= 1.0

            # Enforce minimum interval
            if time_passed < self.config.min_interval:
                await asyncio.sleep(self.config.min_interval - time_passed)

    def get_stats(self) -> Dict[str, float]:
        """Get current rate limiting statistics."""
        return {
            **self.stats,
            "current_tokens": self.tokens,
            "utilization": 1.0 - (self.tokens / self.config.burst_limit)
        }

    def reset_stats(self) -> None:
        """Reset rate limiting statistics."""
        self.stats = {
            "total_requests": 0,
            "throttled_requests": 0,
            "burst_requests": 0,
            "average_interval": 0.0,
            "last_interval": 0.0
        }