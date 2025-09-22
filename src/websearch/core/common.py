"""Common utilities shared between sync and async implementations."""

import json
import logging
from typing import Any, Dict, List
from urllib.parse import quote_plus

from ..utils.advanced_cache import enhanced_search_cache
from ..utils.cache import get_cache_key
from .ranking import (quality_first_ranking, quality_first_ranking_fallback,
                      get_engine_distribution)

logger = logging.getLogger(__name__)


def build_search_urls(query: str) -> Dict[str, str]:
    """Build search URLs for all engines"""
    encoded_query = quote_plus(query)
    return {
        "duckduckgo": f"https://html.duckduckgo.com/html/?q={encoded_query}",
        "bing": f"https://www.bing.com/search?q={encoded_query}",
        "startpage": f"https://www.startpage.com/sp/search?query={encoded_query}",
    }


def format_fallback_search_response(
    search_query: str,
    google_startpage_results: List[Dict[str, Any]],
    bing_ddg_results: List[Dict[str, Any]],
    brave_results: List[Dict[str, Any]],
    num_results: int,
    cached: bool = False,
) -> str:
    """Format search response for 3-engine fallback system."""
    logger.info(
        f"🔍 Fallback results - Google/Startpage: {len(google_startpage_results)}, "
        f"Bing/DDG: {len(bing_ddg_results)}, Brave: {len(brave_results)}"
    )

    # Apply quality-first ranking algorithm for 3 engines
    ranked_results = quality_first_ranking_fallback(
        google_startpage_results, bing_ddg_results, brave_results, num_results
    )

    # Calculate distribution
    distribution = {}
    for result in ranked_results:
        source = result.get("source", "unknown").lower()
        distribution[source] = distribution.get(source, 0) + 1

    response = {
        "query": search_query,
        "total_results": len(ranked_results),
        "sources": {
            "Google/Startpage": len(google_startpage_results),
            "Bing/DuckDuckGo": len(bing_ddg_results),
            "Brave": len(brave_results),
        },
        "engine_distribution": distribution,
        "results": ranked_results,
        "cached": cached,
    }

    return json.dumps(response, indent=2)


def format_search_response(
    search_query: str,
    ddg_results: List[Dict[str, Any]],
    bing_results: List[Dict[str, Any]],
    startpage_results: List[Dict[str, Any]],
    google_results: List[Dict[str, Any]],
    brave_results: List[Dict[str, Any]],
    num_results: int,
    cached: bool = False,
) -> str:
    """Format the final search response with optimized ranking and tracking"""
    from ..utils.tracking import (
        add_tracking_to_url, generate_search_id, log_search_response
    )

    # Generate search ID for tracking
    search_id = generate_search_id()
    logger.info(f"🔍 Generated search_id: {search_id}")

    logger.info(
        f"🔍 Input results - DDG: {len(ddg_results)}, "
        f"Bing: {len(bing_results)}, Startpage: {len(startpage_results)}, "
        f"Google: {len(google_results)}, Brave: {len(brave_results)}"
    )

    # Apply quality-first ranking algorithm
    ranked_results = quality_first_ranking(
        ddg_results, bing_results, startpage_results, google_results,
        brave_results, num_results
    )

    # Get engine distribution for monitoring
    distribution = get_engine_distribution(ranked_results)
    logger.info(f"🔍 Engine distribution: {distribution}")

    # Log search response before adding tracking URLs
    log_search_response(search_query, ranked_results, search_id)

    # Add tracking to final results
    for i, result in enumerate(ranked_results):
        engine = result["source"]
        original_url = result["url"]
        tracked_url = add_tracking_to_url(original_url, engine, search_id)
        result["url"] = tracked_url
        logger.info(
            f"🔍 Result {i+1} - Engine: {engine}, "
            f"Quality: {result['quality_score']:.1f}"
        )

    response = {
        "query": search_query,
        "total_results": len(ranked_results),
        "sources": {
            "DuckDuckGo": len(ddg_results),
            "Bing": len(bing_results),
            "Startpage": len(startpage_results),
            "Google": len(google_results),
            "Brave": len(brave_results),
        },
        "engine_distribution": distribution,
        "results": ranked_results,
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


def cache_search_result(
    search_query: str, num_results: int, response_data: Dict[str, Any]
) -> None:
    """Cache search result in enhanced cache"""
    cache_key = get_cache_key(f"{search_query}:{num_results}")
    enhanced_search_cache.set(cache_key, response_data)
    logger.info(f"Enhanced cache set for key: {cache_key[:32]}...")


def log_search_completion(
    search_query: str, num_results: int, unique_count: int, is_async: bool = False
) -> None:
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
