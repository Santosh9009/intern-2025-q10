"""
LRU Cache implementation with TTL support for caching LLM responses.
"""

import time
import hashlib
from typing import Optional, Any, Dict
from collections import OrderedDict
from dataclasses import dataclass

@dataclass
class CacheEntry:
    """Cache entry with value and timestamp for TTL support."""
    value: Any
    timestamp: float
    access_count: int = 0

class LRUCacheWithTTL:
    """
    LRU (Least Recently Used) Cache with TTL (Time To Live) support.
    
    Features:
    - Maximum capacity (default: 50 entries)
    - TTL expiration (default: 5 minutes = 300 seconds)
    - LRU eviction when capacity is exceeded
    - Automatic cleanup of expired entries
    """
    
    def __init__(self, max_size: int = 50, ttl_seconds: int = 300):
        """
        Initialize LRU cache with TTL.
        
        Args:
            max_size: Maximum number of entries to store
            ttl_seconds: Time to live for cache entries in seconds (default: 5 minutes)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, prompt: str, model: str = "", context: str = "") -> str:
        """
        Generate a cache key from prompt and other parameters.
        
        Args:
            prompt: The user prompt
            model: Model name (optional)
            context: Additional context (optional)
            
        Returns:
            Hash string to use as cache key
        """
        # Combine all inputs for cache key
        cache_input = f"{prompt}|{model}|{context}"
        
        # Use SHA256 for consistent, collision-resistant hashing
        return hashlib.sha256(cache_input.encode('utf-8')).hexdigest()
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """
        Check if a cache entry has expired based on TTL.
        
        Args:
            entry: Cache entry to check
            
        Returns:
            True if entry has expired, False otherwise
        """
        return time.time() - entry.timestamp > self.ttl_seconds
    
    def _cleanup_expired(self) -> None:
        """Remove all expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry.timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]
    
    def get(self, prompt: str, model: str = "", context: str = "") -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired.
        
        Args:
            prompt: The user prompt
            model: Model name (optional)
            context: Additional context (optional)
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        # Clean up expired entries first
        self._cleanup_expired()
        
        key = self._generate_key(prompt, model, context)
        
        if key in self.cache:
            entry = self.cache[key]
            
            # Check if entry has expired
            if self._is_expired(entry):
                del self.cache[key]
                self.misses += 1
                return None
            
            # Move to end (mark as recently used)
            self.cache.move_to_end(key)
            entry.access_count += 1
            self.hits += 1
            return entry.value
        
        self.misses += 1
        return None
    
    def put(self, prompt: str, value: Any, model: str = "", context: str = "") -> None:
        """
        Store value in cache with current timestamp.
        
        Args:
            prompt: The user prompt
            value: Value to cache
            model: Model name (optional)
            context: Additional context (optional)
        """
        key = self._generate_key(prompt, model, context)
        current_time = time.time()
        
        if key in self.cache:
            # Update existing entry
            self.cache[key] = CacheEntry(value, current_time, self.cache[key].access_count + 1)
            self.cache.move_to_end(key)
        else:
            # Add new entry
            self.cache[key] = CacheEntry(value, current_time)
            self.cache.move_to_end(key)
            
            # Remove least recently used if over capacity
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)  # Remove first (least recently used)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        # Clean up expired entries before reporting stats
        self._cleanup_expired()
        
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "ttl_seconds": self.ttl_seconds
        }
    
    def get_size(self) -> int:
        """Get current cache size after cleanup."""
        self._cleanup_expired()
        return len(self.cache)

# Global cache instance (in-memory)
# This will be shared across all requests in the same process
_global_cache: Optional[LRUCacheWithTTL] = None

def get_cache(max_size: int = 50, ttl_seconds: int = 300) -> LRUCacheWithTTL:
    """
    Get or create global cache instance.
    
    Args:
        max_size: Maximum cache size (only used when creating new instance)
        ttl_seconds: TTL in seconds (only used when creating new instance)
        
    Returns:
        Global LRUCacheWithTTL instance
    """
    global _global_cache
    
    if _global_cache is None:
        _global_cache = LRUCacheWithTTL(max_size, ttl_seconds)
    
    return _global_cache

def reset_cache():
    """Reset the global cache (useful for testing)."""
    global _global_cache
    _global_cache = None
