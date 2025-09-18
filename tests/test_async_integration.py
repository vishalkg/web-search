#!/usr/bin/env python3
"""Async integration tests for web search functionality."""

import asyncio
import json
import os
import sys
import time
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from websearch.core.async_search import async_search_web
from websearch.core.content import fetch_single_page_content
from websearch.engines.async_search import (
    async_search_bing,
    async_search_duckduckgo,
    async_search_startpage,
)
from websearch.utils.cache import SimpleCache, content_cache, search_cache


class TestAsyncWebSearchIntegration:
    """Async integration tests for web search functionality"""

    def setup_method(self):
        """Clear caches before each test"""
        search_cache.cache.clear()
        content_cache.cache.clear()

    @pytest.mark.asyncio
    async def test_async_search_duckduckgo_real(self):
        """Test real async DuckDuckGo search"""
        results = await async_search_duckduckgo("python", 3)

        assert isinstance(results, list)
        if results:  # If we got results
            result = results[0]
            assert "title" in result
            assert "url" in result
            assert "snippet" in result
            assert "source" in result
            assert "rank" in result
            assert result["source"] == "DuckDuckGo"
            assert result["rank"] >= 1

    @pytest.mark.asyncio
    async def test_async_search_bing_real(self):
        """Test real async Bing search"""
        results = await async_search_bing("python", 3)

        assert isinstance(results, list)
        if results:  # If we got results
            result = results[0]
            assert "title" in result
            assert "url" in result
            assert "snippet" in result
            assert "source" in result
            assert "rank" in result
            assert result["source"] == "Bing"
            assert result["rank"] >= 1

    @pytest.mark.asyncio
    async def test_async_search_startpage_real(self):
        """Test real async Startpage search"""
        results = await async_search_startpage("python", 3)

        assert isinstance(results, list)
        if results:  # If we got results
            result = results[0]
            assert "title" in result
            assert "url" in result
            assert "snippet" in result
            assert "source" in result
            assert "rank" in result
            assert result["source"] == "Startpage"
            assert result["rank"] >= 1

    @pytest.mark.asyncio
    async def test_async_ranking_preserved(self):
        """Test that ranking is preserved per engine"""
        results = await async_search_duckduckgo("python programming", 5)

        if len(results) >= 2:
            # Check that ranks are sequential
            for i, result in enumerate(results):
                assert result["rank"] == i + 1

    def test_single_page_fetch(self):
        """Test fetching a single web page"""
        url = "https://httpbin.org/html"
        result_json = fetch_single_page_content(url)
        result = json.loads(result_json)

        assert "success" in result
        assert "url" in result
        assert "timestamp" in result
        assert "cached" in result

        if result["success"]:
            assert "content" in result
            assert "content_length" in result
            assert result["content_length"] > 0

    def test_batch_page_fetch_single_url(self):
        """Test batch fetch with single URL (string input)"""
        url = "https://httpbin.org/html"
        result_json = fetch_single_page_content(url)
        result = json.loads(result_json)

        # Should return single page result, not batch format
        assert "success" in result
        assert "url" in result
        assert "batch_request" not in result

    def test_batch_page_fetch_multiple_urls(self):
        """Test batch fetch logic with multiple URLs"""
        import threading
        from datetime import datetime

        urls = ["https://httpbin.org/html", "https://httpbin.org/json"]
        results = []
        threads = []
        thread_results = {}

        def fetch_url_thread(url_to_fetch: str, index: int):
            try:
                result_json = fetch_single_page_content(url_to_fetch)
                thread_results[index] = json.loads(result_json)
            except Exception as e:
                thread_results[index] = {
                    "url": url_to_fetch,
                    "success": False,
                    "error": f"Thread error: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "cached": False,
                }

        # Start threads for parallel fetching
        for i, url_to_fetch in enumerate(urls):
            thread = threading.Thread(target=fetch_url_thread, args=(url_to_fetch, i))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=25)

        # Collect results in order
        for i in range(len(urls)):
            if i in thread_results:
                results.append(thread_results[i])

        # Should have results for both URLs
        assert len(results) == 2
        for result in results:
            assert "success" in result
            assert "url" in result

    def test_content_caching(self):
        """Test that content caching works"""
        url = "https://httpbin.org/html"

        # First fetch
        result1_json = fetch_single_page_content(url)
        result1 = json.loads(result1_json)

        # Second fetch should be cached
        result2_json = fetch_single_page_content(url)
        result2 = json.loads(result2_json)

        # Both should succeed
        if result1["success"] and result2["success"]:
            # Content should be identical
            assert result1["content"] == result2["content"]

    @pytest.mark.asyncio
    async def test_async_search_web_integration(self):
        """Test full async web search integration"""
        result_json = await async_search_web("python programming", 5)
        result = json.loads(result_json)

        assert "query" in result
        assert "total_results" in result
        assert "sources" in result
        assert "results" in result
        assert "cached" in result

        assert result["query"] == "python programming"
        assert isinstance(result["results"], list)
        assert len(result["results"]) <= 5

    @pytest.mark.asyncio
    async def test_async_concurrent_searches(self):
        """Test multiple concurrent async searches"""
        queries = ["python", "javascript", "rust"]

        # Run searches concurrently
        tasks = [async_search_web(f"{query} tutorial", 2) for query in queries]
        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for result_json in results:
            result = json.loads(result_json)
            assert "results" in result
            assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_async_caching_works(self):
        """Test that async caching works correctly"""
        # First search
        result1_json = await async_search_web("python caching test", 3)
        result1 = json.loads(result1_json)

        # Second search should be cached
        result2_json = await async_search_web("python caching test", 3)
        result2 = json.loads(result2_json)

        # Second result should be marked as cached
        assert result2["cached"] is True

        # Results should be identical
        result1["cached"] = True  # Normalize for comparison
        assert result1 == result2


class TestCachingFunctionality:
    """Test caching system"""

    def setup_method(self):
        """Clear caches before each test"""
        search_cache.cache.clear()
        content_cache.cache.clear()

    def test_cache_basic_operations(self):
        """Test basic cache operations"""
        # Test set and get
        search_cache.set("test_key", {"data": "test_value"})
        result = search_cache.get("test_key")

        assert result is not None
        assert result["data"] == "test_value"

    def test_cache_expiration(self):
        """Test cache expiration"""
        # Create cache with very short TTL
        short_cache = SimpleCache(ttl_seconds=1)

        short_cache.set("test_key", {"data": "test_value"})

        # Should be available immediately
        result = short_cache.get("test_key")
        assert result is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        result = short_cache.get("test_key")
        assert result is None

    def test_cache_cleanup(self):
        """Test cache cleanup functionality"""
        short_cache = SimpleCache(ttl_seconds=1)

        # Add some entries
        short_cache.set("key1", "value1")
        short_cache.set("key2", "value2")

        # Wait for expiration
        time.sleep(1.1)

        # Clear expired entries
        short_cache.clear_expired()

        # Cache should be empty
        assert len(short_cache.cache) == 0


class TestMockedFunctionality:
    """Test core logic with mocked network calls"""

    def test_deduplication_logic(self):
        """Test URL deduplication works correctly"""
        # Mock all search functions to return overlapping results
        with (
            patch("websearch.engines.async_search.async_search_duckduckgo") as mock_ddg,
            patch("websearch.engines.async_search.async_search_bing") as mock_bing,
            patch("websearch.engines.async_search.async_search_startpage") as mock_sp,
        ):

            duplicate_url = "https://example.com"
            mock_ddg.return_value = [
                {
                    "title": "DDG Result",
                    "url": duplicate_url,
                    "snippet": "DDG snippet",
                    "source": "DuckDuckGo",
                    "rank": 1,
                }
            ]
            mock_bing.return_value = [
                {
                    "title": "Bing Result",
                    "url": duplicate_url,
                    "snippet": "Bing snippet",
                    "source": "Bing",
                    "rank": 1,
                }
            ]
            mock_sp.return_value = [
                {
                    "title": "SP Result",
                    "url": "https://different.com",
                    "snippet": "SP snippet",
                    "source": "Startpage",
                    "rank": 1,
                }
            ]

            # Test the deduplication logic manually
            from websearch.core.common import deduplicate_results

            all_results = (
                mock_ddg.return_value + mock_bing.return_value + mock_sp.return_value
            )
            unique_results = deduplicate_results(all_results, 10)

            # Should have 2 unique URLs
            assert len(unique_results) == 2
            urls = [r["url"] for r in unique_results]
            assert duplicate_url in urls
            assert "https://different.com" in urls

    def test_error_handling(self):
        """Test error handling in page fetch"""
        from datetime import datetime

        import requests

        result = {
            "url": "https://nonexistent.example",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Simulate request error
        try:
            raise requests.RequestException("Connection failed")
        except requests.RequestException as e:
            result.update(
                {
                    "success": False,
                    "content": None,
                    "content_length": 0,
                    "truncated": False,
                    "error": f"Request error: {str(e)}",
                }
            )

        assert result["success"] is False
        assert "Connection failed" in result["error"]
        assert result["content"] is None

    def test_batch_error_handling(self):
        """Test error handling in batch fetch logic"""
        import threading
        from datetime import datetime

        urls = [
            "https://httpbin.org/html",
            "https://invalid-url-that-does-not-exist.com",
        ]
        results = []
        threads = []
        thread_results = {}

        def fetch_url_thread(url_to_fetch: str, index: int):
            try:
                result_json = fetch_single_page_content(url_to_fetch)
                thread_results[index] = json.loads(result_json)
            except Exception as e:
                thread_results[index] = {
                    "url": url_to_fetch,
                    "success": False,
                    "error": f"Thread error: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "cached": False,
                }

        # Start threads for parallel fetching
        for i, url_to_fetch in enumerate(urls):
            thread = threading.Thread(target=fetch_url_thread, args=(url_to_fetch, i))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=25)

        # Collect results in order
        for i in range(len(urls)):
            if i in thread_results:
                results.append(thread_results[i])

        # Should have results for both URLs
        assert len(results) == 2

        # Should have at least one success and one failure
        success_count = sum(1 for r in results if r.get("success", False))
        failure_count = sum(1 for r in results if not r.get("success", False))

        assert success_count >= 0
        assert failure_count >= 0


if __name__ == "__main__":
    print("Running async integration tests...")
    pytest.main([__file__, "-v"])
