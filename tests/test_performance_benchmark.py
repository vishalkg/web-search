#!/usr/bin/env python3
"""Performance benchmarks comparing sync vs async implementations."""

import asyncio
import sys
import os
import time
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from websearch.core.search import search_web as sync_search_web
from websearch.core.async_search import async_search_web


class TestPerformanceBenchmarks:
    """Performance benchmarks for sync vs async implementations"""

    def test_sync_single_search(self, benchmark):
        """Benchmark single sync search"""
        result = benchmark(sync_search_web, "python programming", 5)
        assert len(result) > 100

    @pytest.mark.asyncio
    async def test_async_single_search(self, benchmark):
        """Benchmark single async search"""
        
        async def async_wrapper():
            return await async_search_web("python programming", 5)
        
        result = await benchmark(async_wrapper)
        assert len(result) > 100

    def test_sync_concurrent_searches(self, benchmark):
        """Benchmark concurrent sync searches using threading"""
        
        def run_concurrent_sync():
            import threading
            results = []
            threads = []
            
            def search_thread(query):
                result = sync_search_web(f"{query} tutorial", 3)
                results.append(result)
            
            queries = ["python", "javascript", "rust", "go", "java"]
            for query in queries:
                thread = threading.Thread(target=search_thread, args=(query,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            return results
        
        results = benchmark(run_concurrent_sync)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_async_concurrent_searches(self, benchmark):
        """Benchmark concurrent async searches"""
        
        async def run_concurrent_async():
            queries = ["python", "javascript", "rust", "go", "java"]
            tasks = [
                async_search_web(f"{query} tutorial", 3) 
                for query in queries
            ]
            return await asyncio.gather(*tasks)
        
        results = await benchmark(run_concurrent_async)
        assert len(results) == 5

    def test_sync_sequential_searches(self, benchmark):
        """Benchmark sequential sync searches"""
        
        def run_sequential_sync():
            queries = ["python", "javascript", "rust"]
            results = []
            for query in queries:
                result = sync_search_web(f"{query} basics", 2)
                results.append(result)
            return results
        
        results = benchmark(run_sequential_sync)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_async_sequential_searches(self, benchmark):
        """Benchmark sequential async searches"""
        
        async def run_sequential_async():
            queries = ["python", "javascript", "rust"]
            results = []
            for query in queries:
                result = await async_search_web(f"{query} basics", 2)
                results.append(result)
            return results
        
        results = await benchmark(run_sequential_async)
        assert len(results) == 3


if __name__ == '__main__':
    print("Running performance benchmarks...")
    pytest.main([__file__, '-v', '--benchmark-only', '--benchmark-sort=mean'])
