"""Core search functionality."""

import json
import logging
import threading
from typing import Any, Dict, List

from ..engines.search import search_bing, search_duckduckgo, search_startpage
from ..utils.cache import get_cache_key, search_cache

logger = logging.getLogger(__name__)


def deduplicate_results(
    all_results: List[Dict[str, Any]], num_results: int
) -> List[Dict[str, Any]]:
    """Remove duplicate URLs from search results"""
    seen_urls = set()
    unique_results = []

    for result in all_results:
        if result["url"] not in seen_urls:
            seen_urls.add(result["url"])
            unique_results.append(result)

    return unique_results[:num_results]


def parallel_search(query: str, num_results: int) -> tuple:
    """Perform parallel searches across all engines"""
    results = {"ddg": [], "bing": [], "startpage": []}
    threads = []

    def search_wrapper(engine_func, key):
        results[key] = engine_func(query, num_results)

    # Start all searches
    search_funcs = [
        (search_duckduckgo, "ddg"),
        (search_bing, "bing"),
        (search_startpage, "startpage"),
    ]

    for func, key in search_funcs:
        thread = threading.Thread(target=search_wrapper, args=(func, key))
        thread.start()
        threads.append(thread)

    # Wait for completion
    for thread in threads:
        thread.join(timeout=15)

    return results["ddg"], results["bing"], results["startpage"]


def search_web(search_query: str, num_results: int = 10) -> str:
    """Perform a web search using multiple search engines with caching"""
    logger.info(
        f"Performing multi-engine search for: '{search_query}' "
        f"(num_results: {num_results})"
    )

    num_results = min(num_results, 20)
    cache_key = get_cache_key(f"{search_query}:{num_results}")

    # Check cache
    cached_result = search_cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for key: {cache_key[:32]}...")
        cached_result["cached"] = True
        return json.dumps(cached_result, indent=2)

    # Clear expired cache entries
    search_cache.clear_expired()

    # Perform parallel searches
    ddg_results, bing_results, startpage_results = parallel_search(search_query, num_results)

    # Combine and deduplicate results
    all_results = ddg_results + bing_results + startpage_results
    unique_results = deduplicate_results(all_results, num_results)

    response = {
        "query": search_query,
        "total_results": len(unique_results),
        "sources": {
            "DuckDuckGo": len(ddg_results),
            "Bing": len(bing_results),
            "Startpage": len(startpage_results),
        },
        "results": unique_results,
        "cached": False,
    }

    # Cache the result
    search_cache.set(cache_key, response)
    logger.info(f"Cache set for key: {cache_key[:32]}...")
    logger.info(f"Search completed: {len(unique_results)} unique results found")

    return json.dumps(response, indent=2)
