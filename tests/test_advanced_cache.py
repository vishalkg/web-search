"""Tests for the LRUCache (advanced_cache)."""

import time

import pytest

from websearch.utils.advanced_cache import LRUCache


def test_set_and_get_compressed():
    cache = LRUCache(max_size=10, ttl_seconds=60, compress=True)
    cache.set("k", {"hello": "world"})
    assert cache.get("k") == {"hello": "world"}


def test_set_and_get_uncompressed():
    cache = LRUCache(max_size=10, ttl_seconds=60, compress=False)
    cache.set("k", {"hello": "world"})
    assert cache.get("k") == {"hello": "world"}


def test_lru_eviction():
    cache = LRUCache(max_size=2, ttl_seconds=60, compress=True)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)  # Evicts 'a'
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_lru_recency_bumps_to_end():
    cache = LRUCache(max_size=2, ttl_seconds=60, compress=True)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")  # 'a' becomes most recent
    cache.set("c", 3)  # Evicts 'b'
    assert cache.get("a") == 1
    assert cache.get("b") is None


def test_expiration():
    cache = LRUCache(max_size=10, ttl_seconds=1, compress=True)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    time.sleep(1.05)
    assert cache.get("k") is None


def test_clear_expired():
    cache = LRUCache(max_size=10, ttl_seconds=1, compress=True)
    cache.set("a", 1)
    cache.set("b", 2)
    time.sleep(1.05)
    cache.set("c", 3)
    removed = cache.clear_expired()
    assert removed == 2
    assert cache.get("c") == 3


def test_stats_track_hits_and_misses():
    cache = LRUCache(max_size=10, ttl_seconds=60, compress=True)
    cache.set("a", 1)
    cache.get("a")  # hit
    cache.get("a")  # hit
    cache.get("missing")  # miss
    stats = cache.get_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["hit_rate"] == pytest.approx(2 / 3, rel=1e-3)


def test_compression_independent_round_trip():
    """Same data round-trips identically across both modes."""
    payload = {"a": list(range(100)), "nested": {"k": "v"}}
    a = LRUCache(max_size=5, ttl_seconds=60, compress=True)
    b = LRUCache(max_size=5, ttl_seconds=60, compress=False)
    a.set("k", payload)
    b.set("k", payload)
    assert a.get("k") == b.get("k") == payload
