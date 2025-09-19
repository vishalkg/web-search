#!/usr/bin/env python3
"""Debug parsing issues for DuckDuckGo and Startpage."""

import asyncio
import aiohttp
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

async def debug_engine(name, url, expected_selectors):
    """Debug a single search engine's parsing"""
    print(f"\n🔍 Debugging {name}")
    print(f"URL: {url}")
    print("-" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                print(f"Status: {response.status}")
                
                if response.status == 200:
                    content = await response.text()
                    print(f"Content length: {len(content)} chars")
                    
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Check each expected selector
                    for selector_name, selector in expected_selectors.items():
                        elements = soup.select(selector)
                        print(f"Selector '{selector_name}' ({selector}): {len(elements)} matches")
                        
                        if elements:
                            for i, elem in enumerate(elements[:3]):
                                print(f"  {i+1}. {elem.get_text()[:100]}...")
                        else:
                            print(f"  No matches found")
                    
                    # Show page structure
                    print(f"\nPage structure sample:")
                    body = soup.find('body')
                    if body:
                        # Find divs with class attributes
                        divs_with_class = body.find_all('div', class_=True)[:10]
                        print(f"Found {len(divs_with_class)} divs with classes:")
                        for div in divs_with_class:
                            classes = ' '.join(div.get('class', []))
                            print(f"  <div class='{classes}'> - {div.get_text()[:50]}...")
                    
                elif response.status == 202:
                    print("HTTP 202 - Request accepted but not processed")
                    content = await response.text()
                    print(f"Content sample: {content[:500]}...")
                else:
                    print(f"HTTP {response.status} - Error response")
                    
    except Exception as e:
        print(f"Error: {e}")

async def main():
    query = "python tutorial"
    encoded_query = quote_plus(query)
    
    engines = {
        "DuckDuckGo": {
            "url": f"https://html.duckduckgo.com/html/?q={encoded_query}",
            "selectors": {
                "results": ".result",
                "links": ".result__a",
                "titles": ".result__title",
                "snippets": ".result__snippet",
                "web_results": ".web-result"
            }
        },
        "Startpage": {
            "url": f"https://www.startpage.com/sp/search?query={encoded_query}",
            "selectors": {
                "results": ".w-gl__result",
                "search_results": ".search-result", 
                "result_items": ".result",
                "titles": ".result-title",
                "links": ".result-link"
            }
        }
    }
    
    print(f"🚀 Debugging Search Engine Parsing")
    print(f"Query: '{query}'")
    print("=" * 70)
    
    for name, config in engines.items():
        await debug_engine(name, config["url"], config["selectors"])

if __name__ == "__main__":
    asyncio.run(main())
