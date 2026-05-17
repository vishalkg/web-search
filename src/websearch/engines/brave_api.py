"""Brave Search API implementation."""

import logging
import os
from typing import Any, Dict, List

import aiohttp
import requests

from ..utils.connection_pool import get_session
from ..utils.unified_quota import unified_quota

logger = logging.getLogger(__name__)

BASE_URL = "https://api.search.brave.com/res/v1/web/search"
SOURCE_NAME = "brave"


def _build_request(query: str, num_results: int):
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return None, None
    headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
    params = {
        "q": query,
        "count": min(max(int(num_results), 1), 20),
        "country": "us",
        "search_lang": "en",
    }
    return headers, params


def _parse_brave_results(data: dict) -> List[Dict[str, Any]]:
    results = []
    for item in data.get("web", {}).get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "source": SOURCE_NAME,
                "rank": len(results) + 1,
            }
        )
    return results


def search_brave_api(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Search using Brave Search API (sync)."""
    headers_params = _build_request(query, num_results)
    if headers_params == (None, None):
        logger.warning("Brave API key not configured")
        return []
    headers, params = headers_params

    if not unified_quota.can_make_request("brave"):
        logger.warning("Brave API quota exhausted for this month")
        return []

    try:
        response = requests.get(BASE_URL, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        unified_quota.record_request("brave")
        results = _parse_brave_results(response.json())
        logger.info(f"Brave API found {len(results)} results")
        return results
    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", 0) or 0
        if status == 429:
            logger.warning(f"Brave API rate-limited (429): {e}")
        elif status == 401:
            logger.error("Brave API auth failed (401) - check BRAVE_SEARCH_API_KEY")
        else:
            logger.error(f"Brave API HTTP {status}: {e}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Brave API request error: {e}")
        return []


# pylint: disable=too-many-return-statements
async def async_search_brave_api_native(
    query: str, num_results: int
) -> List[Dict[str, Any]]:
    """Native async implementation using aiohttp with connection pool."""
    headers_params = _build_request(query, num_results)
    if headers_params == (None, None):
        logger.warning("Brave API key not configured")
        return []
    headers, params = headers_params

    if not unified_quota.can_make_request("brave"):
        logger.warning("Brave API quota exhausted for this month")
        return []

    try:
        session = get_session()
        async with session.get(BASE_URL, headers=headers, params=params) as response:
            if response.status == 429:
                logger.warning("Brave API rate-limited (429)")
                return []
            if response.status == 401:
                logger.error("Brave API auth failed (401) - check BRAVE_SEARCH_API_KEY")
                return []
            response.raise_for_status()
            data = await response.json()

        unified_quota.record_request("brave")
        results = _parse_brave_results(data)
        logger.info(f"Brave API found {len(results)} results")
        return results
    except aiohttp.ClientResponseError as e:
        logger.error(f"Brave API HTTP {e.status}: {e}")
        return []
    except aiohttp.ClientError as e:
        logger.error(f"Brave API request error: {e}")
        return []


async def async_search_brave_api(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Async Brave API search using connection pool."""
    return await async_search_brave_api_native(query, num_results)
