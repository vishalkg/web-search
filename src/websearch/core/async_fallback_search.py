"""Async fallback-based search orchestration with backward compatibility."""

import asyncio
import logging
from typing import Any, Dict, List, Tuple

from ..engines.async_search import (
    async_search_bing, async_search_brave, async_search_duckduckgo,
    async_search_google, async_search_startpage
)

logger = logging.getLogger(__name__)


async def async_search_with_fallback(
    primary_func, fallback_func, query: str, num_results: int
) -> List[Dict[str, Any]]:
    """Async search with primary engine, fallback to secondary if primary fails."""
    try:
        results = await primary_func(query, num_results)
        if results:  # Primary succeeded
            return results
        else:  # Primary returned empty, try fallback
            logger.warning("Primary engine returned empty, trying fallback")
            return await fallback_func(query, num_results)
    except Exception as e:
        logger.error(f"Primary engine failed: {e}, trying fallback")
        try:
            return await fallback_func(query, num_results)
        except Exception as fe:
            logger.error(f"Fallback engine also failed: {fe}")
            return []


async def async_fallback_parallel_search(
    query: str, num_results: int
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Perform async parallel searches with 3-engine fallback system."""
    # Create tasks for concurrent execution with fallbacks
    tasks = [
        async_search_with_fallback(
            async_search_google, async_search_startpage, query, num_results
        ),
        async_search_with_fallback(
            async_search_bing, async_search_duckduckgo, query, num_results
        ),
        async_search_brave(query, num_results),
    ]

    # Execute all searches concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions and return results
    google_startpage_results = (
        results[0] if not isinstance(results[0], Exception) else []
    )
    bing_ddg_results = (
        results[1] if not isinstance(results[1], Exception) else []
    )
    brave_results = results[2] if not isinstance(results[2], Exception) else []

    return google_startpage_results, bing_ddg_results, brave_results
