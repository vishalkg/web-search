"""Advanced caching with LRU eviction and compression."""

import gzip
import json
import threading
import time
from collections import OrderedDict
from typing import Any, Optional


class LRUCache:
    """Thread-safe LRU cache with TTL and compression support"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300, compress: bool = True):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.compress = compress
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.RLock()

    def _is_expired(self, entry: dict) -> bool:
        return time.time() - entry["timestamp"] > self.ttl_seconds

    def _compress_data(self, data: Any) -> bytes:
        """Compress data using gzip"""
        if not self.compress:
            return data
        json_str = json.dumps(data)
        return gzip.compress(json_str.encode("utf-8"))

    def _decompress_data(self, compressed_data: bytes) -> Any:
        """Decompress gzip data"""
        if not self.compress:
            return compressed_data
        json_str = gzip.decompress(compressed_data).decode("utf-8")
        return json.loads(json_str)

    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not self._is_expired(entry):
                    # Move to end (most recently used)
                    self.cache.move_to_end(key)
                    return self._decompress_data(entry["value"])
                else:
                    del self.cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        with self.lock:
            # Remove oldest entries if at capacity
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)

            compressed_value = self._compress_data(value)
            self.cache[key] = {"value": compressed_value, "timestamp": time.time()}

    def clear_expired(self) -> int:
        """Clear expired entries and return count removed"""
        with self.lock:
            expired_keys = [key for key, entry in self.cache.items() if self._is_expired(entry)]
            for key in expired_keys:
                del self.cache[key]
            return len(expired_keys)

    def get_stats(self) -> dict:
        """Get cache statistics"""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_rate": getattr(self, "_hits", 0) / max(getattr(self, "_requests", 1), 1),
                "compression_enabled": self.compress,
            }


# Enhanced cache instances
enhanced_search_cache = LRUCache(max_size=500, ttl_seconds=300, compress=True)
enhanced_content_cache = LRUCache(max_size=200, ttl_seconds=1800, compress=True)
