"""
Simple in-memory rate limiter for FastAPI endpoints.
"""

import time
import asyncio
from fastapi import HTTPException, Request, status, Depends
from typing import Dict, Tuple, Optional, Callable

# In-memory storage for rate limiting
# Structure: {ip_address: (request_count, start_time)}
request_counts: Dict[str, Tuple[int, float]] = {}
rate_limit_lock = asyncio.Lock()

async def in_memory_rate_limiter(
    request: Request,
    times: int = 10,
    seconds: int = 60,
    error_message: str = "Rate limit exceeded"
) -> None:
    """
    A simple in-memory rate limiter that can be used as a FastAPI dependency.
    
    Args:
        request: The FastAPI request object
        times: Maximum number of requests allowed in the time window
        seconds: Time window in seconds
        error_message: Error message to return when rate limit is exceeded
    
    Raises:
        HTTPException: When rate limit is exceeded
    """
    client_ip = request.client.host if request.client else "unknown"
    
    async with rate_limit_lock:
        current_time = time.time()
        
        # Get current count and start time for this IP
        count, start_time = request_counts.get(client_ip, (0, current_time))
        
        # Reset if time window has passed
        if current_time - start_time > seconds:
            count = 0
            start_time = current_time
        
        # Check if rate limit exceeded
        if count >= times:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_message
            )
        
        # Update count
        request_counts[client_ip] = (count + 1, start_time)

def create_rate_limiter(times: int = 10, seconds: int = 60) -> Callable:
    """
    Create a rate limiter dependency with the specified parameters.
    
    Args:
        times: Maximum number of requests allowed in the time window
        seconds: Time window in seconds
        
    Returns:
        A dependency function for FastAPI
    """
    async def rate_limit_dependency(request: Request) -> None:
        await in_memory_rate_limiter(request, times, seconds)
    
    return rate_limit_dependency
