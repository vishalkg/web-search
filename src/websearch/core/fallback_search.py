"""Fallback-based search orchestration with backward compatibility."""

import logging
import os
import threading
from typing import Any, Dict, List, Tuple

from ..engines.search import (search_bing, search_brave, search_duckduckgo,
                              search_google, search_startpage)

logger = logging.getLogger(__name__)

# Configurable timeout
SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "8"))


def search_with_fallback(
    primary_func, fallback_func, query: str, num_results: int
) -> List[Dict[str, Any]]:
    """Search with primary engine, fallback to secondary if primary fails."""
    try:
        results = primary_func(query, num_results)
        if results:  # Primary succeeded
            return results
        else:  # Primary returned empty, try fallback
            logger.warning("Primary engine returned empty, trying fallback")
            return fallback_func(query, num_results)
    except Exception as e:
        logger.error(f"Primary engine failed: {e}, trying fallback")
        try:
            return fallback_func(query, num_results)
        except Exception as fe:
            logger.error(f"Fallback engine also failed: {fe}")
            return []


def fallback_parallel_search(
    query: str, num_results: int
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Perform parallel searches with 3-engine fallback system."""
    results = {"google_startpage": [], "bing_ddg": [], "brave": []}
    threads = []

    def search_wrapper(search_func, key):
        results[key] = search_func()

    # Define search functions with fallbacks
    search_funcs = [
        (
            lambda: search_with_fallback(
                search_google, search_startpage, query, num_results
            ),
            "google_startpage",
        ),
        (
            lambda: search_with_fallback(
                search_bing, search_duckduckgo, query, num_results
            ),
            "bing_ddg",
        ),
        (lambda: search_brave(query, num_results), "brave"),
    ]

    for func, key in search_funcs:
        thread = threading.Thread(target=search_wrapper, args=(func, key))
        thread.start()
        threads.append(thread)

    # Wait for completion
    for thread in threads:
        thread.join(timeout=SEARCH_TIMEOUT)

    return results["google_startpage"], results["bing_ddg"], results["brave"]
