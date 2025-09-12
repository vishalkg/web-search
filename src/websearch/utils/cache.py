"""Caching utilities."""

import hashlib
import threading
import time
from typing import Any, Dict, Optional


class SimpleCache:
    """Thread-safe in-memory cache with TTL support"""

    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self.lock = threading.RLock()

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        return time.time() - entry["timestamp"] > self.ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not self._is_expired(entry):
                    return entry["value"]
                else:
                    del self.cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        with self.lock:
            self.cache[key] = {"value": value, "timestamp": time.time()}

    def clear_expired(self) -> None:
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items() if self._is_expired(entry)
            ]
            for key in expired_keys:
                del self.cache[key]


# Global cache instances
search_cache = SimpleCache(ttl_seconds=300)
content_cache = SimpleCache(ttl_seconds=1800)


def get_cache_key(text: str) -> str:
    """Generate cache key from text"""
    return hashlib.md5(text.encode()).hexdigest()
