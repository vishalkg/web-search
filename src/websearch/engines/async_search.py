"""Async search engine implementations."""

import asyncio
import logging
import random
from typing import Any, Dict, List
from urllib.parse import quote_plus

import aiohttp
from bs4 import BeautifulSoup

from ..utils.connection_pool import get_session
from .brave_api import async_search_brave_api
from .google_api import async_search_google_api
from .parsers import (parse_bing_results, parse_duckduckgo_results,
                      parse_startpage_results)

logger = logging.getLogger(__name__)

# Rate limiting: base delay + random jitter (min, max) seconds
RATE_LIMITS = {
    "duckduckgo": (1.5, 3.0),  # 1.5-3.0s random delay
    "bing": (1.0, 2.5),  # 1.0-2.5s random delay
    "startpage": (2.0, 4.0),  # 2.0-4.0s random delay
}

# Track last request time per engine
_last_request_time = {}


async def _rate_limit_delay(engine_name: str) -> None:
    """Apply rate limiting delay with random jitter"""
    if engine_name not in RATE_LIMITS:
        return

    current_time = asyncio.get_event_loop().time()
    last_time = _last_request_time.get(engine_name, 0)
    min_delay, max_delay = RATE_LIMITS[engine_name]

    # Random delay between min and max
    random_delay = random.uniform(min_delay, max_delay)

    time_since_last = current_time - last_time
    if time_since_last < random_delay:
        delay = random_delay - time_since_last
        logger.info(f"Rate limiting {engine_name}: waiting {delay:.1f}s")
        await asyncio.sleep(delay)

    _last_request_time[engine_name] = asyncio.get_event_loop().time()


async def async_search_engine_base(
    url: str, parser_func, source_name: str, query: str, num_results: int
) -> List[Dict[str, Any]]:
    """Base async function for search engine implementations"""
    try:
        session = get_session()  # Use global connection pool
        async with session.get(url) as response:
            response.raise_for_status()
            html = await response.text()

        soup = BeautifulSoup(html, "lxml")
        results = parser_func(soup, num_results)
        logger.info(f"{source_name} found {len(results)} results")
        return results

    except asyncio.TimeoutError:
        logger.error(f"{source_name} search timed out")
        return []
    except aiohttp.ClientError as e:
        logger.error(f"{source_name} search client error: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"{source_name} search failed with unexpected error: {str(e)}")
        return []


async def async_search_duckduckgo(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Async search DuckDuckGo"""
    await _rate_limit_delay("duckduckgo")
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    return await async_search_engine_base(
        url, parse_duckduckgo_results, "DuckDuckGo", query, num_results
    )


async def async_search_bing(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Async search Bing"""
    await _rate_limit_delay("bing")
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    return await async_search_engine_base(
        url, parse_bing_results, "Bing", query, num_results
    )


async def async_search_startpage(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Async search Startpage"""
    await _rate_limit_delay("startpage")
    url = f"https://www.startpage.com/sp/search?query={quote_plus(query)}"
    return await async_search_engine_base(
        url, parse_startpage_results, "Startpage", query, num_results
    )


async def async_search_google(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Async search Google API"""
    return await async_search_google_api(query, num_results)


async def async_search_brave(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Async search Brave API"""
    return await async_search_brave_api(query, num_results)
