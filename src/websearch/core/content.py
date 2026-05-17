"""Content fetching and processing."""

import asyncio
import json
import logging
from datetime import datetime, timezone

import aiohttp
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import HTTPError, RequestException, Timeout

from ..config import CONTENT_TIMEOUT, MAX_CONTENT_LENGTH
from ..utils.cache import content_cache, get_cache_key
from ..utils.content import create_error_result, extract_text_content
from ..utils.http import (ResponseTooLargeError, make_request,
                          make_request_async)

logger = logging.getLogger(__name__)


def _success_result(url: str, text: str) -> dict:
    truncated = len(text) > MAX_CONTENT_LENGTH
    if truncated:
        text = text[:MAX_CONTENT_LENGTH] + "... [Content truncated]"
    return {
        "url": url,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cached": False,
        "success": True,
        "content": text,
        "content_length": len(text),
        "truncated": truncated,
        "error": None,
    }


def fetch_single_page_content(url: str) -> str:
    """Fetch content from a single URL with caching (sync path)."""
    logger.info(f"Fetching page content from: {url}")

    cache_key = get_cache_key(url)
    cached_result = content_cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for key: {cache_key[:32]}")
        cached_result = {**cached_result, "cached": True}
        return json.dumps(cached_result, indent=2)

    try:
        response = make_request(url, CONTENT_TIMEOUT)
        text = extract_text_content(response.text)
        result = _success_result(url, text)
        content_cache.set(cache_key, result)
        logger.info(f"Successfully fetched {len(text)} characters from {url}")
    except Timeout:
        result = create_error_result(
            url, "Request timeout - page took too long to respond", "timeout"
        )
        logger.error(f"Timeout fetching {url}")
    except ResponseTooLargeError as e:
        result = create_error_result(url, str(e), "too_large")
        logger.error(f"Response too large for {url}: {e}")
    except RequestsConnectionError as e:
        result = create_error_result(url, f"Connection error: {str(e)}", "connection")
        logger.error(f"Connection error fetching {url}: {str(e)}")
    except HTTPError as e:
        status = getattr(e.response, "status_code", 0) or 0
        error_type = "http_5xx" if status >= 500 else "http_4xx"
        result = create_error_result(
            url, f"HTTP error {status}: {str(e)}", error_type
        )
        logger.error(f"HTTP error {status} fetching {url}: {str(e)}")
    except RequestException as e:
        result = create_error_result(url, f"Request error: {str(e)}", "general")
        logger.error(f"Request error fetching {url}: {str(e)}")

    return json.dumps(result, indent=2)


async def fetch_single_page_content_async(url: str) -> dict:
    """Async fetch content with caching and connection pooling."""
    logger.info(f"Fetching page content from: {url}")

    cache_key = get_cache_key(url)
    cached_result = content_cache.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for key: {cache_key[:32]}")
        return {**cached_result, "cached": True}

    try:
        response_text = await make_request_async(url, CONTENT_TIMEOUT)
        text = extract_text_content(response_text)
        result = _success_result(url, text)
        content_cache.set(cache_key, result)
        logger.info(f"Successfully fetched {len(text)} characters from {url}")
    except asyncio.TimeoutError:
        result = create_error_result(
            url, "Request timeout - page took too long to respond", "timeout"
        )
        logger.error(f"Timeout fetching {url}")
    except ResponseTooLargeError as e:
        result = create_error_result(url, str(e), "too_large")
        logger.error(f"Response too large for {url}: {e}")
    except aiohttp.TooManyRedirects as e:
        result = create_error_result(
            url, f"Redirect limit exceeded: {str(e)}", "redirect"
        )
        logger.error(f"Too many redirects for {url}")
    except aiohttp.ClientConnectionError as e:
        result = create_error_result(url, f"Connection error: {str(e)}", "connection")
        logger.error(f"Connection error fetching {url}: {str(e)}")
    except aiohttp.ClientResponseError as e:
        error_type = "http_5xx" if e.status >= 500 else "http_4xx"
        result = create_error_result(
            url, f"HTTP error {e.status}: {str(e)}", error_type
        )
        logger.error(f"HTTP error {e.status} fetching {url}: {str(e)}")
    except aiohttp.ClientError as e:
        result = create_error_result(url, f"Request error: {str(e)}", "general")
        logger.error(f"Request error fetching {url}: {str(e)}")

    return result
