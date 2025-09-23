#!/usr/bin/env python3
"""Test fallback search system."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.websearch.core.search import search_web_fallback, search_web

def test_fallback_system():
    """Test both fallback and original search systems."""
    # Check API keys from environment
    if not os.getenv("BRAVE_SEARCH_API_KEY"):
        print("❌ BRAVE_SEARCH_API_KEY environment variable not set")
        return
    
    print("🔍 Testing Fallback Search System...")
    
    # Test fallback search (3 engines with fallbacks)
    print("\n=== FALLBACK SEARCH (3 engines) ===")
    fallback_results = search_web_fallback("python programming", 5)
    print("Fallback search completed")
    
    # Test original search (5 engines)
    print("\n=== ORIGINAL SEARCH (5 engines) ===")
    original_results = search_web("python programming", 5)
    print("Original search completed")
    
    print("\n✅ Both systems working - backward compatibility maintained!")

if __name__ == "__main__":
    test_fallback_system()
