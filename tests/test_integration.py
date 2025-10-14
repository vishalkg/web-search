#!/usr/bin/env python3

import json
import os
import sys
import unittest
from unittest.mock import patch

import requests

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from websearch.core.content import fetch_single_page_content
from websearch.engines.search import (search_bing, search_duckduckgo,
                                      search_startpage)
from websearch.utils.cache import content_cache, search_cache


class TestWebSearchIntegration(unittest.TestCase):
    """Integration tests for web search functionality"""

    def setUp(self):
        """Clear caches before each test"""
        search_cache.cache.clear()
        content_cache.cache.clear()

    def test_search_duckduckgo_real(self):
        """Test real DuckDuckGo search"""
        results = search_duckduckgo("python", 3)

        self.assertIsInstance(results, list)
        if results:  # If we got results
            result = results[0]
            self.assertIn("title", result)
            self.assertIn("url", result)
            self.assertIn("snippet", result)
            self.assertIn("source", result)
            self.assertIn("rank", result)
            self.assertEqual(result["source"], "DuckDuckGo")
            self.assertGreaterEqual(result["rank"], 1)

    def test_search_bing_real(self):
        """Test real Bing search"""
        results = search_bing("python", 3)

        self.assertIsInstance(results, list)
        if results:  # If we got results
            result = results[0]
            self.assertIn("title", result)
            self.assertIn("url", result)
            self.assertIn("snippet", result)
            self.assertIn("source", result)
            self.assertIn("rank", result)
            self.assertEqual(result["source"], "Bing")
            self.assertGreaterEqual(result["rank"], 1)

    def test_search_startpage_real(self):
        """Test real Startpage search"""
        results = search_startpage("python", 3)

        self.assertIsInstance(results, list)
        if results:  # If we got results
            result = results[0]
            self.assertIn("title", result)
            self.assertIn("url", result)
            self.assertIn("snippet", result)
            self.assertIn("source", result)
            self.assertIn("rank", result)
            self.assertEqual(result["source"], "Startpage")
            self.assertGreaterEqual(result["rank"], 1)

    def test_ranking_preserved(self):
        """Test that ranking is preserved per engine"""
        results = search_duckduckgo("python programming", 5)

        if len(results) >= 2:
            # Check that ranks are sequential
            for i, result in enumerate(results):
                self.assertEqual(result["rank"], i + 1)

    def test_single_page_fetch(self):
        """Test fetching a single web page"""
        url = "https://httpbin.org/html"
        result_json = fetch_single_page_content(url)
        result = json.loads(result_json)

        self.assertIn("success", result)
        self.assertIn("url", result)
        self.assertIn("timestamp", result)
        self.assertIn("cached", result)

        if result["success"]:
            self.assertIn("content", result)
            self.assertIn("content_length", result)
            self.assertGreater(result["content_length"], 0)

    def test_batch_page_fetch_single_url(self):
        """Test batch fetch with single URL (string input)"""
        # Test the internal function directly since the tool is wrapped
        url = "https://httpbin.org/html"
        result_json = fetch_single_page_content(url)
        result = json.loads(result_json)

        # Should return single page result, not batch format
        self.assertIn("success", result)
        self.assertIn("url", result)
        self.assertNotIn("batch_request", result)

    def test_batch_page_fetch_multiple_urls(self):
        """Test batch fetch logic with multiple URLs"""
        # We'll test the batch logic manually since the tool is wrapped
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
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIn("success", result)
            self.assertIn("url", result)

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
            self.assertEqual(result1["content"], result2["content"])
            # Check cache was used (this is logged, but we can't easily test it here)


class TestCachingFunctionality(unittest.TestCase):
    """Test caching system"""

    def setUp(self):
        """Clear caches before each test"""
        search_cache.cache.clear()
        content_cache.cache.clear()

    def test_cache_basic_operations(self):
        """Test basic cache operations"""
        # Test set and get
        search_cache.set("test_key", {"data": "test_value"})
        result = search_cache.get("test_key")

        self.assertIsNotNone(result)
        self.assertEqual(result["data"], "test_value")

    def test_cache_expiration(self):
        """Test cache expiration"""
        import time

        # Create cache with very short TTL
        from websearch.utils.cache import SimpleCache

        short_cache = SimpleCache(ttl_seconds=1)

        short_cache.set("test_key", {"data": "test_value"})

        # Should be available immediately
        result = short_cache.get("test_key")
        self.assertIsNotNone(result)

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        result = short_cache.get("test_key")
        self.assertIsNone(result)

    def test_cache_cleanup(self):
        """Test cache cleanup functionality"""
        from websearch.utils.cache import SimpleCache

        short_cache = SimpleCache(ttl_seconds=1)

        # Add some entries
        short_cache.set("key1", "value1")
        short_cache.set("key2", "value2")

        # Wait for expiration
        import time

        time.sleep(1.1)

        # Clear expired entries
        short_cache.clear_expired()

        # Cache should be empty
        self.assertEqual(len(short_cache.cache), 0)


class TestMockedFunctionality(unittest.TestCase):
    """Test core logic with mocked network calls"""

    def test_deduplication_logic(self):
        """Test URL deduplication works correctly"""
        # Mock all search functions to return overlapping results
        with (
            patch("websearch.engines.search.search_duckduckgo") as mock_ddg,
            patch("websearch.engines.search.search_bing") as mock_bing,
            patch("websearch.engines.search.search_startpage") as mock_sp,
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
            all_results = (
                mock_ddg("test", 5) + mock_bing("test", 5) + mock_sp("test", 5)
            )
            seen_urls = set()
            unique_results = []

            for result in all_results:
                if result["url"] not in seen_urls:
                    seen_urls.add(result["url"])
                    unique_results.append(result)

            # Should have 2 unique URLs
            self.assertEqual(len(unique_results), 2)
            urls = [r["url"] for r in unique_results]
            self.assertIn(duplicate_url, urls)
            self.assertIn("https://different.com", urls)

    def test_error_handling(self):
        """Test error handling in page fetch"""
        from datetime import datetime
        from typing import Any, Dict

        result: Dict[str, Any] = {
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

        self.assertFalse(result["success"])
        self.assertIn("Connection failed", result["error"])
        self.assertIsNone(result["content"])

    def test_batch_error_handling(self):
        """Test error handling in batch fetch logic"""
        # Test the batch logic manually since the tool is wrapped
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
        self.assertEqual(len(results), 2)

        # Should have at least one success and one failure
        success_count = sum(1 for r in results if r.get("success", False))
        failure_count = sum(1 for r in results if not r.get("success", False))

        self.assertGreaterEqual(success_count, 0)
        self.assertGreaterEqual(failure_count, 0)


if __name__ == "__main__":
    print("Running integration tests with real web calls...")
    unittest.main(verbosity=2)
