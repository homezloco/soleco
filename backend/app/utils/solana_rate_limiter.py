"""
Rate limiter for Solana RPC requests with adaptive rate adjustment.
"""

import asyncio
import logging
import time
import random
from dataclasses import dataclass
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Default rate limiting configuration
RATE_CONFIG = {
    'initial_rate': 5.0,      # Start with 5 requests per second
    'min_rate': 1.0,          # Never go below 1 request per second
    'max_rate': 15.0,         # Never exceed 15 requests per second
    'decrease_factor': 0.4,   # Cut rate by 60% on failure
    'increase_factor': 1.02,  # Increase rate by 2% on success
    'circuit_breaker_threshold': 2,  # Trip after 2 consecutive errors
    'max_backoff_time': 120,  # Maximum backoff time in seconds
    'jitter_factor': 0.2      # Add randomness to backoff times
}

@dataclass
class AdaptiveRateConfig:
    """Configuration for adaptive rate limiting."""
    initial_rate: float = 5.0  # Initial requests per second
    min_rate: float = 1.0      # Minimum requests per second
    max_rate: float = 15.0     # Maximum requests per second
    decrease_factor: float = 0.4  # Rate decrease factor
    increase_factor: float = 1.02  # Rate increase factor
    circuit_breaker_threshold: int = 2  # Threshold for circuit breaker
    window_size: int = 10     # Number of requests to consider for success rate
    cooldown_multiplier: float = 3.0  # Multiplier for cooldown duration
    max_consecutive_failures: int = 2  # Maximum consecutive failures before circuit break
    max_backoff_time: float = 120.0  # Maximum backoff time in seconds
    jitter_factor: float = 0.2  # Add randomness to backoff times

class SolanaRateLimiter:
    """Adaptive rate limiter for Solana RPC requests."""
    
    def __init__(self, config: Dict[str, Any]):
        self.initial_rate = config.get('initial_rate', 5)
        self.min_rate = config.get('min_rate', 1)
        self.max_rate = config.get('max_rate', 15)
        self.decrease_factor = config.get('decrease_factor', 0.4)
        self.increase_factor = config.get('increase_factor', 1.02)
        self.circuit_breaker_threshold = config.get('circuit_breaker_threshold', 2)
        self.max_backoff_time = config.get('max_backoff_time', 120)
        self.jitter_factor = config.get('jitter_factor', 0.2)
        
        self.current_rate = self.initial_rate
        self.error_count = 0
        self.rate_limit_errors = 0  # Specific counter for rate limit errors
        self.last_success_time = time.time()
        self.cooldown_until = 0
        self._lock = asyncio.Lock()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limited_requests = 0
        self.last_rate_limited_time = 0
        
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
                
            # Calculate minimum time between requests based on current rate
            min_interval = 1.0 / self.current_rate
            
            # Add jitter to avoid thundering herd problem
            jitter = random.uniform(0, min_interval * self.jitter_factor)
            min_interval += jitter
            
            # Enforce minimum interval between requests
            time_since_last_request = current_time - self.last_success_time
            if time_since_last_request < min_interval:
                # Need to wait more
                return False

            self.total_requests += 1
            return True

    def update_rate(self, success: bool, rate_limited: bool = False) -> None:
        """Update rate limiter state based on request success/failure."""
        current_time = time.time()

        if success:
            self.error_count = max(0, self.error_count - 1)  # Gradually decrease error count on success
            self.rate_limit_errors = 0  # Reset rate limit errors on success
            self.last_success_time = current_time
            self.successful_requests += 1
            
            # Gradually increase rate after consistent success
            if self.successful_requests % 10 == 0:  # Only increase after every 10 successful requests
                self.current_rate = min(
                    self.current_rate * self.increase_factor,
                    self.max_rate
                )
                logger.debug(f"Gradually increasing rate to {self.current_rate:.1f}/s after consistent success")
        else:
            self.error_count += 1
            self.failed_requests += 1
            
            if rate_limited:
                self.rate_limited_requests += 1
                self.rate_limit_errors += 1
                self.last_rate_limited_time = current_time
                
                # More aggressive rate reduction for rate limit errors
                self.current_rate = max(
                    self.current_rate * 0.3,  # 70% reduction for rate limit errors
                    self.min_rate
                )
                logger.warning(f"Rate limited: reducing rate to {self.current_rate:.1f}/s")
            else:
                # Standard decrease rate on general failure
                self.current_rate = max(
                    self.current_rate * self.decrease_factor,
                    self.min_rate
                )
                logger.debug(f"Decreasing rate to {self.current_rate:.1f}/s due to error")
            
            # Circuit breaker logic
            if self.error_count >= self.circuit_breaker_threshold:
                # Exponential backoff with cap
                base_cooldown = min(30.0 * (2 ** (self.error_count - self.circuit_breaker_threshold)), 
                                   self.max_backoff_time)
                
                # Add jitter to avoid thundering herd problem when multiple clients recover
                jitter = random.uniform(0, base_cooldown * self.jitter_factor)
                cooldown_time = base_cooldown + jitter
                
                # More aggressive backoff for rate limit errors
                if self.rate_limit_errors >= 2:
                    cooldown_time *= 1.5
                
                self.cooldown_until = current_time + cooldown_time
                logger.warning(f"Circuit breaker triggered: cooling down for {cooldown_time:.1f}s")
                
                # Don't reset error count completely to maintain memory of problems
                self.error_count = max(1, self.error_count // 2)

    def get_backoff_time(self) -> float:
        """
        Get the time to back off in seconds.
        
        Returns:
            float: The time to back off in seconds, or 0 if no backoff is needed
        """
        current_time = time.time()
        if current_time < self.cooldown_until:
            return self.cooldown_until - current_time
        return 0.0

    def handle_rate_limit_error(self) -> float:
        """Handle a rate limit error and return the backoff time in seconds."""
        self.update_rate(False, rate_limited=True)
        
        # Calculate backoff time
        current_time = time.time()
        if current_time < self.cooldown_until:
            return self.cooldown_until - current_time
        
        # If not in cooldown, calculate a backoff time based on rate limit errors
        backoff_time = min(5.0 * (2 ** self.rate_limit_errors), self.max_backoff_time)
        
        # Add jitter
        jitter = random.uniform(0, backoff_time * self.jitter_factor)
        backoff_time += jitter
        
        return backoff_time

    def get_statistics(self) -> Dict:
        """Get current rate limiting statistics."""
        return {
            "current_rate": self.current_rate,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rate_limited_requests": self.rate_limited_requests,
            "success_rate": (self.successful_requests / max(1, self.total_requests) * 100),
            "error_count": self.error_count,
            "rate_limit_errors": self.rate_limit_errors,
            "circuit_breaker_active": time.time() < self.cooldown_until,
            "cooldown_remaining": max(0, self.cooldown_until - time.time())
        }
