"""Core search functionality."""

import json
import logging
import threading

from ..engines.search import (
    search_bing, search_brave, search_duckduckgo, search_google, search_startpage
)
from .common import (cache_search_result, cleanup_expired_cache,
                     format_search_response, format_fallback_search_response,
                     get_cached_search_result, log_search_completion)
from .fallback_search import fallback_parallel_search

logger = logging.getLogger(__name__)


def parallel_search(query: str, num_results: int) -> tuple:
    """Perform parallel searches across all engines"""
    results = {"ddg": [], "bing": [], "startpage": [], "google": [], "brave": []}
    threads = []

    def search_wrapper(engine_func, key):
        results[key] = engine_func(query, num_results)

    # Start all searches
    search_funcs = [
        (search_duckduckgo, "ddg"),
        (search_bing, "bing"),
        (search_startpage, "startpage"),
        (search_google, "google"),
        (search_brave, "brave"),
    ]

    for func, key in search_funcs:
        thread = threading.Thread(target=search_wrapper, args=(func, key))
        thread.start()
        threads.append(thread)

    # Wait for completion with reduced timeout
    for thread in threads:
        thread.join(timeout=8)

    return (
        results["ddg"], results["bing"], results["startpage"],
        results["google"], results["brave"]
    )


def search_web_fallback(search_query: str, num_results: int = 10) -> str:
    """
    Search the web using 3-engine fallback system.

    Fallback pairs:
    - Google -> Startpage (if Google fails/quota exhausted)
    - Bing -> DuckDuckGo (if Bing fails)
    - Brave (standalone)
    """
    # Check cache first
    cached_result = get_cached_search_result(search_query, num_results)
    if cached_result:
        return cached_result

    logger.info(f"🔍 Fallback search: '{search_query}' (limit: {num_results})")

    # Perform fallback parallel searches
    google_startpage_results, bing_ddg_results, brave_results = (
        fallback_parallel_search(search_query, num_results)
    )

    # Format response for 3-engine fallback system
    response_json = format_fallback_search_response(
        search_query, google_startpage_results, bing_ddg_results,
        brave_results, num_results
    )

    # Cache and log
    cache_search_result(search_query, num_results, response_json)

    # Parse response to get unique count for logging
    response_data = json.loads(response_json)
    unique_count = response_data.get("total_results", 0)
    log_search_completion(search_query, num_results, unique_count)

    return response_json


def search_web(search_query: str, num_results: int = 10) -> str:
    """Perform a web search using multiple search engines with enhanced caching"""
    logger.info(
        f"Performing multi-engine search for: '{search_query}' "
        f"(num_results: {num_results})"
    )

    num_results = min(num_results, 20)

    # Check enhanced cache
    cached_result = get_cached_search_result(search_query, num_results)
    if cached_result:
        return cached_result

    # Clean up expired cache entries
    cleanup_expired_cache()

    # Perform parallel searches
    ddg_results, bing_results, startpage_results, google_results, brave_results = (
        parallel_search(search_query, num_results)
    )

    # Format response
    response_json = format_search_response(
        search_query, ddg_results, bing_results, startpage_results,
        google_results, brave_results, num_results
    )

    # Cache the result
    response_data = json.loads(response_json)
    cache_search_result(search_query, num_results, response_data)

    # Log completion
    log_search_completion(
        search_query, num_results, response_data["total_results"], is_async=False
    )

    return response_json
