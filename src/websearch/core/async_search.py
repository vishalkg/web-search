"""Async core search functionality."""

import asyncio
import json
import logging

from ..engines.async_search import (async_search_bing, async_search_brave,
                                    async_search_duckduckgo,
                                    async_search_google,
                                    async_search_startpage)
from .async_fallback_search import async_fallback_parallel_search
from .common import (cache_search_result, cleanup_expired_cache,
                     format_fallback_search_response, format_search_response,
                     get_cached_search_result, log_search_completion)

logger = logging.getLogger(__name__)


async def async_parallel_search(query: str, num_results: int) -> tuple:
    """Perform async parallel searches across all engines"""
    # Create tasks for concurrent execution
    tasks = [
        async_search_duckduckgo(query, num_results),
        async_search_bing(query, num_results),
        async_search_startpage(query, num_results),
        async_search_google(query, num_results),
        async_search_brave(query, num_results),
    ]

    # Execute all searches concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions and return results
    ddg_results = results[0] if not isinstance(results[0], Exception) else []
    bing_results = results[1] if not isinstance(results[1], Exception) else []
    startpage_results = results[2] if not isinstance(results[2], Exception) else []
    google_results = results[3] if not isinstance(results[3], Exception) else []
    brave_results = results[4] if not isinstance(results[4], Exception) else []

    return ddg_results, bing_results, startpage_results, google_results, brave_results


async def async_search_web_fallback(search_query: str, num_results: int = 10) -> str:
    """
    Async search the web using 3-engine fallback system.

    Fallback pairs:
    - Google -> Startpage (if Google fails/quota exhausted)
    - Bing -> DuckDuckGo (if Bing fails)
    - Brave (standalone)
    """
    # Check cache first
    cached_result = get_cached_search_result(search_query, num_results)
    if cached_result:
        return cached_result

    logger.info(f"🔍 Async fallback search: '{search_query}' (limit: {num_results})")

    # Perform async fallback parallel searches
    google_startpage_results, bing_ddg_results, brave_results = (
        await async_fallback_parallel_search(search_query, num_results)
    )

    # Format response for 3-engine fallback system
    response_json = format_fallback_search_response(
        search_query,
        google_startpage_results,
        bing_ddg_results,
        brave_results,
        num_results,
    )

    # Cache and log
    cache_search_result(search_query, num_results, response_json)

    # Parse response to get unique count for logging
    response_data = json.loads(response_json)
    unique_count = response_data.get("total_results", 0)
    log_search_completion(search_query, num_results, unique_count, is_async=True)

    return response_json


async def async_search_web(search_query: str, num_results: int = 10) -> str:
    """Async web search using multiple search engines with enhanced caching"""
    logger.info(
        f"Performing async multi-engine search for: '{search_query}' "
        f"(num_results: {num_results})"
    )

    num_results = min(num_results, 20)

    # Check enhanced cache
    cached_result = get_cached_search_result(search_query, num_results)
    if cached_result:
        return cached_result

    # Clean up expired cache entries
    cleanup_expired_cache()

    # Perform async parallel searches
    ddg_results, bing_results, startpage_results, google_results, brave_results = (
        await async_parallel_search(search_query, num_results)
    )

    # Format response
    response_json = format_search_response(
        search_query,
        ddg_results,
        bing_results,
        startpage_results,
        google_results,
        brave_results,
        num_results,
    )

    # Cache the result
    response_data = json.loads(response_json)
    cache_search_result(search_query, num_results, response_data)

    # Log completion
    log_search_completion(
        search_query, num_results, response_data["total_results"], is_async=True
    )

    return response_json
