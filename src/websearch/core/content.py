"""Content fetching and processing."""

import json
import logging
from datetime import datetime, timezone

from requests.exceptions import (ConnectionError, HTTPError, RequestException,
                                 Timeout)

from ..utils.cache import content_cache, get_cache_key
from ..utils.content import create_error_result, extract_text_content
from ..utils.http import make_request

logger = logging.getLogger(__name__)

# Constants
CONTENT_TIMEOUT = 15
MAX_CONTENT_LENGTH = 50000


def fetch_single_page_content(url: str) -> str:
    """Fetch content from a single URL with caching"""
    logger.info(f"Fetching page content from: {url}")

    cache_key = get_cache_key(url)
    cached_result = content_cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for key: {cache_key[:32]}...")
        return json.dumps(cached_result, indent=2)

    result = {
        "url": url,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cached": False,
    }

    try:
        response = make_request(url, CONTENT_TIMEOUT)
        text = extract_text_content(response.text)

        truncated = len(text) > MAX_CONTENT_LENGTH
        if truncated:
            text = text[:MAX_CONTENT_LENGTH] + "... [Content truncated]"

        result.update(
            {
                "success": True,
                "content": text,
                "content_length": len(text),
                "truncated": truncated,
                "error": None,
            }
        )

        content_cache.set(cache_key, result)
        logger.info(f"Cache set for key: {cache_key[:32]}...")
        logger.info(f"Successfully fetched {len(text)} characters from {url}")

    except Timeout:
        result = create_error_result(
            url, "Request timeout - page took too long to respond", "timeout"
        )
        logger.error(f"Timeout fetching {url}")
    except ConnectionError as e:
        result = create_error_result(url, f"Connection error: {str(e)}", "connection")
        logger.error(f"Connection error fetching {url}: {str(e)}")
    except HTTPError as e:
        error_type = "http_5xx" if e.response.status_code >= 500 else "http_4xx"
        result = create_error_result(
            url, f"HTTP error {e.response.status_code}: {str(e)}", error_type
        )
        logger.error(f"HTTP error {e.response.status_code} fetching {url}: {str(e)}")
    except RequestException as e:
        result = create_error_result(url, f"Request error: {str(e)}", "general")
        logger.error(f"Request error fetching {url}: {str(e)}")
    except Exception as e:
        result = create_error_result(url, f"Processing error: {str(e)}", "parse")
        logger.error(f"Processing error fetching {url}: {str(e)}")

    return json.dumps(result, indent=2)
