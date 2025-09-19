#!/usr/bin/env python3
"""Test individual search engines to diagnose issues."""

import asyncio
import sys
from src.websearch.engines.async_search import (
    async_search_duckduckgo, 
    async_search_bing, 
    async_search_startpage
)

async def test_engine(engine_name, engine_func, query, num_results=5):
    """Test a single search engine"""
    print(f"\n🔍 Testing {engine_name}...")
    print(f"Query: '{query}' (requesting {num_results} results)")
    print("-" * 50)
    
    try:
        results = await engine_func(query, num_results)
        
        if results:
            print(f"✅ Success: {len(results)} results found")
            for i, result in enumerate(results[:3], 1):
                title = result.get('title', 'No title')[:60]
                url = result.get('url', 'No URL')[:80]
                print(f"{i}. {title}...")
                print(f"   {url}")
        else:
            print("❌ No results returned")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return len(results) if 'results' in locals() else 0

async def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "python programming tutorial"
    num_results = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    print(f"🚀 Testing Search Engines")
    print(f"Query: '{query}'")
    print(f"Requested results: {num_results}")
    print("=" * 60)
    
    engines = [
        ("DuckDuckGo", async_search_duckduckgo),
        ("Bing", async_search_bing),
        ("Startpage", async_search_startpage)
    ]
    
    results_summary = {}
    
    for name, func in engines:
        count = await test_engine(name, func, query, num_results)
        results_summary[name] = count
    
    print(f"\n📊 Summary:")
    print("=" * 30)
    total = sum(results_summary.values())
    for engine, count in results_summary.items():
        status = "✅" if count > 0 else "❌"
        print(f"{status} {engine:12}: {count:2d} results")
    
    print(f"\nTotal results: {total}")
    
    if total == 0:
        print("\n⚠️  All engines returned 0 results - possible rate limiting or network issues")
    elif any(count == 0 for count in results_summary.values()):
        working = [name for name, count in results_summary.items() if count > 0]
        failing = [name for name, count in results_summary.items() if count == 0]
        print(f"\n⚠️  Working: {', '.join(working)}")
        print(f"   Failing: {', '.join(failing)}")

if __name__ == "__main__":
    asyncio.run(main())
