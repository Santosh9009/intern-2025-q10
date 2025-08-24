import time
from typing import Optional
from dataclasses import dataclass

@dataclass
class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""
    message: str = "Rate limit exceeded. Please try again later."
    status_code: int = 429

class TokenBucket:
    """
    Token bucket implementation for rate limiting.
    Allows bursts up to capacity but maintains average rate over time.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens (requests) the bucket can hold
            refill_rate: Number of tokens added per second
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time and refill rate
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens available
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def time_until_available(self, tokens: int = 1) -> float:
        """
        Calculate time until enough tokens will be available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Time in seconds until tokens will be available
        """
        self._refill()
        
        if self.tokens >= tokens:
            return 0.0
        
        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate

class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    Default: 10 requests per minute.
    """
    
    def __init__(self, requests_per_minute: int = 10):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum number of requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        
        # Convert to requests per second for token bucket
        refill_rate = requests_per_minute / 60.0
        
        # Allow burst of all requests, but maintain average rate
        self.bucket = TokenBucket(capacity=requests_per_minute, refill_rate=refill_rate)
    
    def check_rate_limit(self) -> None:
        """
        Check if request is allowed under rate limit.
        
        Raises:
            RateLimitError: If rate limit is exceeded
        """
        if not self.bucket.consume(1):
            wait_time = self.bucket.time_until_available(1)
            raise RateLimitError(
                f"Rate limit exceeded. {self.requests_per_minute} requests per minute allowed. "
                f"Try again in {wait_time:.1f} seconds.",
                429
            )
    
    def get_status(self) -> dict:
        """
        Get current rate limit status.
        
        Returns:
            Dictionary with current status information
        """
        self.bucket._refill()  # Update tokens first
        
        return {
            "requests_per_minute": self.requests_per_minute,
            "available_tokens": int(self.bucket.tokens),
            "capacity": self.bucket.capacity,
            "refill_rate_per_second": self.bucket.refill_rate,
            "time_until_next_token": self.bucket.time_until_available(1)
        }

# Global rate limiter instance (in-memory)
# This will be shared across all requests in the same process
_global_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter(requests_per_minute: int = 10) -> RateLimiter:
    """
    Get or create global rate limiter instance.
    
    Args:
        requests_per_minute: Rate limit (only used when creating new instance)
        
    Returns:
        Global RateLimiter instance
    """
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(requests_per_minute)
    
    return _global_rate_limiter

def reset_rate_limiter():
    """Reset the global rate limiter (useful for testing)."""
    global _global_rate_limiter
    _global_rate_limiter = None
