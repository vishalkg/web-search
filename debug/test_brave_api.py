#!/usr/bin/env python3
"""Test Brave Search API integration with real API."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.websearch.engines.brave_api import search_brave_api
from src.websearch.utils.unified_quota import unified_quota

def test_brave_api():
    """Test Brave API with real key."""
    # Check API key from environment
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        print("❌ BRAVE_SEARCH_API_KEY environment variable not set")
        return
    
    print("🔍 Testing Brave Search API...")
    
    # Check quota status
    usage = unified_quota.get_usage("brave")
    print(f"📊 Quota status: {usage['used']}/{usage['limit']} used this month")
    
    if not unified_quota.can_make_request("brave"):
        print("❌ Quota exhausted - cannot make request")
        return
    
    # Test search
    results = search_brave_api("python programming", 5)
    
    print(f"✅ Found {len(results)} results")
    for i, result in enumerate(results[:3], 1):
        print(f"{i}. {result['title']}")
        print(f"   {result['url']}")
        print(f"   {result['snippet'][:100]}...")
        print()
    
    # Check quota after request
    usage = unified_quota.get_usage("brave")
    print(f"📊 Updated quota: {usage['used']}/{usage['limit']} used this month")

if __name__ == "__main__":
    test_brave_api()
