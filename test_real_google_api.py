#!/usr/bin/env python3
"""Test real Google Search API."""

import json
import sys
import os

# Add src to path
sys.path.insert(0, 'src')

from websearch.engines.google_api import search_google_api
from websearch.utils.quota import quota_manager


def test_real_api():
    """Test with real Google API."""
    print(f"Quota remaining: {quota_manager.get_remaining()}")
    
    if not quota_manager.can_make_request():
        print("❌ Quota exhausted for today")
        return False
    
    print("🔍 Testing real Google API...")
    results = search_google_api("python programming", 3)
    
    print(f"✅ Got {len(results)} results from Google API")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title'][:50]}...")
        print(f"   {result['url']}")
    
    print(f"Quota remaining after test: {quota_manager.get_remaining()}")
    return True


if __name__ == "__main__":
    test_real_api()
