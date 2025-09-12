"""Google Custom Search API implementation."""

import logging
import os
from typing import Any, Dict, List

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..utils.quota import quota_manager

logger = logging.getLogger(__name__)

API_KEY = os.getenv("GOOGLE_CSE_API_KEY")
CSE_ID = os.getenv("GOOGLE_CSE_ID")


def search_google_api(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Search using Google Custom Search API."""
    if not API_KEY or not CSE_ID:
        logger.warning("Google API key or CSE ID not configured")
        return []
        
    if not quota_manager.can_make_request():
        logger.warning("Google API quota exhausted for today")
        return []

    try:
        service = build("customsearch", "v1", developerKey=API_KEY)
        result = service.cse().list(
            q=query,
            cx=CSE_ID,
            num=min(num_results, 10)
        ).execute()

        quota_manager.record_request()
        
        results = []
        for item in result.get("items", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "Google"
            })

        logger.info(f"Google API found {len(results)} results")
        return results

    except HttpError as e:
        if e.resp.status in [403, 429]:  # Quota exceeded or rate limited
            logger.warning(f"Google API quota/rate limit: {e}")
            return []
        logger.error(f"Google API HTTP error: {e}")
        return []
    except Exception as e:
        logger.error(f"Google API search failed: {e}")
        return []


async def async_search_google_api(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Async wrapper for Google API search."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, search_google_api, query, num_results)
