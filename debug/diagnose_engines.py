#!/usr/bin/env python3
"""Diagnose search engine issues - rate limiting vs parsing failures."""

import asyncio
import aiohttp
from urllib.parse import quote_plus

async def diagnose_engine(name, url, expected_patterns):
    """Diagnose a single search engine"""
    print(f"\n🔍 Diagnosing {name}")
    print(f"URL: {url}")
    print("-" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                print(f"Status Code: {response.status}")
                print(f"Content-Type: {response.headers.get('content-type', 'Unknown')}")
                
                if response.status == 200:
                    content = await response.text()
                    print(f"Content Length: {len(content)} characters")
                    
                    # Check for rate limiting indicators
                    rate_limit_indicators = [
                        "rate limit", "too many requests", "blocked", 
                        "captcha", "verify you are human", "403", "429"
                    ]
                    
                    content_lower = content.lower()
                    rate_limited = any(indicator in content_lower for indicator in rate_limit_indicators)
                    
                    if rate_limited:
                        print("❌ RATE LIMITED - Found rate limiting indicators")
                        for indicator in rate_limit_indicators:
                            if indicator in content_lower:
                                print(f"   Found: '{indicator}'")
                    else:
                        print("✅ No rate limiting detected")
                        
                        # Check if expected content patterns exist
                        patterns_found = []
                        for pattern in expected_patterns:
                            if pattern.lower() in content_lower:
                                patterns_found.append(pattern)
                        
                        if patterns_found:
                            print(f"✅ Expected patterns found: {patterns_found}")
                        else:
                            print(f"❌ PARSING ISSUE - Expected patterns not found: {expected_patterns}")
                            
                        # Show a sample of the content
                        print(f"\nContent sample (first 500 chars):")
                        print(content[:500] + "..." if len(content) > 500 else content)
                
                elif response.status == 429:
                    print("❌ RATE LIMITED - HTTP 429 Too Many Requests")
                elif response.status == 403:
                    print("❌ BLOCKED - HTTP 403 Forbidden")
                else:
                    print(f"❌ HTTP ERROR - Status {response.status}")
                    
    except asyncio.TimeoutError:
        print("❌ TIMEOUT - Request timed out")
    except Exception as e:
        print(f"❌ ERROR - {e}")

async def main():
    query = "python programming"
    encoded_query = quote_plus(query)
    
    engines = [
        ("DuckDuckGo", f"https://html.duckduckgo.com/html/?q={encoded_query}", 
         ["result", "links", "web-result"]),
        ("Bing", f"https://www.bing.com/search?q={encoded_query}", 
         ["b_algo", "b_title", "results"]),
        ("Startpage", f"https://www.startpage.com/sp/search?query={encoded_query}", 
         ["result", "w-gl__result", "search-result"])
    ]
    
    print(f"🚀 Diagnosing Search Engine Issues")
    print(f"Query: '{query}'")
    print("=" * 70)
    
    for name, url, patterns in engines:
        await diagnose_engine(name, url, patterns)

if __name__ == "__main__":
    asyncio.run(main())
