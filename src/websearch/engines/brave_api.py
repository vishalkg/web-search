"""Brave Search API implementation."""

import logging
import os
from typing import Any, Dict, List

import requests

from ..utils.unified_quota import unified_quota

logger = logging.getLogger(__name__)

BASE_URL = "https://api.search.brave.com/res/v1/web/search"


def search_brave_api(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Search using Brave Search API."""
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")

    if not api_key:
        logger.warning("Brave API key not configured")
        return []

    if not unified_quota.can_make_request("brave"):
        logger.warning("Brave API quota exhausted for this month")
        return []

    try:
        headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}

        params = {
            "q": query,
            "count": min(num_results, 20),
            "country": "us",
            "search_lang": "en",
        }

        response = requests.get(BASE_URL, headers=headers, params=params, timeout=5)
        response.raise_for_status()

        unified_quota.record_request("brave")

        data = response.json()
        results = []

        web_results = data.get("web", {}).get("results", [])
        for item in web_results:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", ""),
                    "source": "brave",
                }
            )

        logger.info(f"Brave API found {len(results)} results")
        return results

    except requests.exceptions.RequestException as e:
        logger.error(f"Brave API request error: {e}")
        return []
    except Exception as e:
        logger.error(f"Brave API search failed: {e}")
        return []


async def async_search_brave_api(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Async wrapper for Brave API search."""
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, search_brave_api, query, num_results)
