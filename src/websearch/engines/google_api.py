"""Google Custom Search API implementation."""

import logging
import os
from typing import Any, Dict, List

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    build = None
    HttpError = Exception

from ..utils.unified_quota import unified_quota

logger = logging.getLogger(__name__)


def search_google_api(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Search using Google Custom Search API."""
    if not GOOGLE_API_AVAILABLE:
        logger.warning(
            "Google API client library not available. "
            "Install with: pip install google-api-python-client"
        )
        return []

    api_key = os.getenv("GOOGLE_CSE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        logger.warning("Google API key or CSE ID not configured")
        return []

    if not unified_quota.can_make_request("google"):
        logger.warning("Google API quota exhausted for today")
        return []

    try:
        service = build("customsearch", "v1", developerKey=api_key)
        # pylint: disable=no-member
        result = service.cse().list(
            q=query,
            cx=cse_id,
            num=min(num_results, 10)
        ).execute()

        unified_quota.record_request("google")

        results = []
        for item in result.get("items", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "google"
            })

        logger.info(f"Google API found {len(results)} results")
        return results

    except HttpError as e:
        if e.resp.status in [403, 429]:  # Quota exceeded or rate limited
            logger.warning(f"Google API quota/rate limit: {e}")
        else:
            logger.error(f"Google API HTTP error: {e}")
        return []


async def async_search_google_api(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Async wrapper for Google API search."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, search_google_api, query, num_results)
