"""Advanced caching with LRU eviction, TTL, and optional gzip compression."""

import gzip
import json
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

from ..config import (CONTENT_CACHE_SIZE, CONTENT_CACHE_TTL,
                      SEARCH_CACHE_SIZE, SEARCH_CACHE_TTL)


class LRUCache:
    """Thread-safe LRU cache with TTL and optional compression.

    When ``compress=True`` values are gzip-encoded JSON bytes; when False
    they are stored as-is. The encode/decode paths are symmetric so a
    cache instance can be safely toggled between modes only at construction.
    """

    def __init__(
        self, max_size: int = 1000, ttl_seconds: int = 300, compress: bool = True
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.compress = compress
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def _is_expired(self, entry: dict) -> bool:
        return time.time() - entry["timestamp"] > self.ttl_seconds

    def _encode(self, data: Any) -> Any:
        if not self.compress:
            return data
        return gzip.compress(json.dumps(data).encode("utf-8"))

    def _decode(self, encoded: Any) -> Any:
        if not self.compress:
            return encoded
        return json.loads(gzip.decompress(encoded).decode("utf-8"))

    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not self._is_expired(entry):
                    self.cache.move_to_end(key)
                    self._hits += 1
                    return self._decode(entry["value"])
                del self.cache[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        with self.lock:
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            self.cache[key] = {
                "value": self._encode(value),
                "timestamp": time.time(),
            }

    def clear_expired(self) -> int:
        """Clear expired entries and return count removed."""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items() if self._is_expired(entry)
            ]
            for key in expired_keys:
                del self.cache[key]
            return len(expired_keys)

    def get_stats(self) -> dict:
        """Get cache statistics including hit rate."""
        with self.lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total) if total > 0 else 0.0
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 4),
                "compression_enabled": self.compress,
            }


enhanced_search_cache = LRUCache(
    max_size=SEARCH_CACHE_SIZE, ttl_seconds=SEARCH_CACHE_TTL, compress=True
)
enhanced_content_cache = LRUCache(
    max_size=CONTENT_CACHE_SIZE, ttl_seconds=CONTENT_CACHE_TTL, compress=True
)
