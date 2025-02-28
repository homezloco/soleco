"""
Rate limiter for Solana RPC requests with adaptive rate adjustment.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Default rate limiting configuration
RATE_CONFIG = {
    'initial_rate': 5.0,      # Start with 5 requests per second
    'min_rate': 2.0,         # Never go below 2 requests per second
    'max_rate': 20.0,        # Never exceed 20 requests per second
    'decrease_factor': 0.5,   # Cut rate in half on failure
    'increase_factor': 1.05,  # Increase rate by 5% on success
    'circuit_breaker_threshold': 3  # Trip after 3 consecutive errors
}

@dataclass
class AdaptiveRateConfig:
    """Configuration for adaptive rate limiting."""
    initial_rate: float = 5.0  # Initial requests per second
    min_rate: float = 2.0     # Minimum requests per second
    max_rate: float = 20.0     # Maximum requests per second
    decrease_factor: float = 0.5  # Rate decrease factor
    increase_factor: float = 1.05  # Rate increase factor
    circuit_breaker_threshold: int = 3  # Threshold for circuit breaker
    window_size: int = 10     # Number of requests to consider for success rate
    cooldown_multiplier: float = 2.0  # Multiplier for cooldown duration
    max_consecutive_failures: int = 3  # Maximum consecutive failures before circuit break

class SolanaRateLimiter:
    """Adaptive rate limiter for Solana RPC requests."""
    
    def __init__(self, config: Dict[str, Any]):
        self.initial_rate = config.get('initial_rate', 5)
        self.min_rate = config.get('min_rate', 2)
        self.max_rate = config.get('max_rate', 20)
        self.decrease_factor = config.get('decrease_factor', 0.5)
        self.increase_factor = config.get('increase_factor', 1.05)
        self.circuit_breaker_threshold = config.get('circuit_breaker_threshold', 3)
        
        self.current_rate = self.initial_rate
        self.error_count = 0
        self.last_success_time = time.time()
        self.cooldown_until = 0
        self._lock = asyncio.Lock()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
    async def acquire(self) -> bool:
        """Try to acquire a rate limit token."""
        async with self._lock:
            current_time = time.time()
            
            # Check if we're in cooldown
            if current_time < self.cooldown_until:
                cooldown_remaining = self.cooldown_until - current_time
                logger.debug(f"In cooldown for {cooldown_remaining:.1f}s")
                return False

            # Calculate time since last success
            time_since_success = current_time - self.last_success_time
            
            # If we've been successful for a while, gradually increase rate
            if time_since_success > 10 and self.error_count == 0:
                self.current_rate = min(
                    self.current_rate * self.increase_factor,
                    self.max_rate
                )
                logger.debug(f"Increasing rate to {self.current_rate:.1f}/s")

            return True

    def update_rate(self, success: bool) -> None:
        """Update rate limiter state based on request success/failure."""
        current_time = time.time()

        if success:
            self.error_count = 0
            self.last_success_time = current_time
            self.successful_requests += 1
            
            # Gradually increase rate after consistent success
            if current_time - self.last_success_time > 5:
                self.current_rate = min(
                    self.current_rate * self.increase_factor,
                    self.max_rate
                )
        else:
            self.error_count += 1
            self.failed_requests += 1
            
            # Decrease rate on failure
            self.current_rate = max(
                self.current_rate * self.decrease_factor,
                self.min_rate
            )
            
            # Circuit breaker logic
            if self.error_count >= self.circuit_breaker_threshold:
                cooldown_time = min(30.0 * (2 ** (self.error_count - self.circuit_breaker_threshold)), 300.0)
                self.cooldown_until = current_time + cooldown_time
                logger.warning(f"Circuit breaker triggered: cooling down for {cooldown_time:.1f}s")
                self.error_count = 0  # Reset error count after triggering circuit breaker

    def get_statistics(self) -> Dict:
        """Get current rate limiting statistics."""
        return {
            "current_rate": self.current_rate,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.successful_requests / (self.successful_requests + self.failed_requests) * 100) if (self.successful_requests + self.failed_requests) > 0 else 0,
            "error_count": self.error_count,
            "circuit_breaker_active": time.time() < self.cooldown_until
        }
