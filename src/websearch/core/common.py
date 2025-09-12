"""Common utilities shared between sync and async implementations."""

import json
import logging
from typing import Any, Dict, List
from urllib.parse import quote_plus

from ..utils.cache import get_cache_key
from ..utils.advanced_cache import enhanced_search_cache

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


def build_search_urls(query: str) -> Dict[str, str]:
    """Build search URLs for all engines"""
    encoded_query = quote_plus(query)
    return {
        "duckduckgo": f"https://html.duckduckgo.com/html/?q={encoded_query}",
        "bing": f"https://www.bing.com/search?q={encoded_query}",
        "startpage": f"https://www.startpage.com/sp/search?query={encoded_query}",
    }


def format_search_response(
    search_query: str,
    ddg_results: List[Dict[str, Any]],
    bing_results: List[Dict[str, Any]], 
    startpage_results: List[Dict[str, Any]],
    num_results: int,
    cached: bool = False
) -> str:
    """Format the final search response"""
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
        "cached": cached,
    }

    return json.dumps(response, indent=2)


def get_cached_search_result(search_query: str, num_results: int) -> str | None:
    """Check enhanced cache for existing search result"""
    cache_key = get_cache_key(f"{search_query}:{num_results}")
    cached_result = enhanced_search_cache.get(cache_key)
    
    if cached_result:
        logger.info(f"Enhanced cache hit for key: {cache_key[:32]}...")
        cached_result["cached"] = True
        return json.dumps(cached_result, indent=2)
    
    return None


def cache_search_result(search_query: str, num_results: int, response_data: Dict[str, Any]) -> None:
    """Cache search result in enhanced cache"""
    cache_key = get_cache_key(f"{search_query}:{num_results}")
    enhanced_search_cache.set(cache_key, response_data)
    logger.info(f"Enhanced cache set for key: {cache_key[:32]}...")


def log_search_completion(search_query: str, num_results: int, unique_count: int, is_async: bool = False) -> None:
    """Log search completion with cache stats"""
    search_type = "Async" if is_async else "Sync"
    cache_stats = enhanced_search_cache.get_stats()
    logger.info(
        f"{search_type} search for '{search_query}' completed: "
        f"{unique_count} unique results found (requested: {num_results}) "
        f"[Cache: {cache_stats['size']}/{cache_stats['max_size']}]"
    )


def cleanup_expired_cache() -> None:
    """Clean up expired cache entries"""
    removed = enhanced_search_cache.clear_expired()
    if removed > 0:
        logger.info(f"Cleaned up {removed} expired cache entries")
