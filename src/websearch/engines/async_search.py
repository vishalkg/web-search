"""Async search engine implementations."""

import asyncio
import logging
from typing import Any, Dict, List
from urllib.parse import quote_plus

import aiohttp
from bs4 import BeautifulSoup

from .parsers import (parse_bing_results, parse_duckduckgo_results,
                      parse_startpage_results)

logger = logging.getLogger(__name__)


async def async_search_engine_base(
    url: str, parser_func, source_name: str, query: str, num_results: int
) -> List[Dict[str, Any]]:
    """Base async function for search engine implementations"""
    try:
        async with aiohttp.ClientSession() as session:
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
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    return await async_search_engine_base(
        url, parse_duckduckgo_results, "DuckDuckGo", query, num_results
    )


async def async_search_bing(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Async search Bing"""
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    return await async_search_engine_base(
        url, parse_bing_results, "Bing", query, num_results
    )


async def async_search_startpage(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Async search Startpage"""
    url = f"https://www.startpage.com/sp/search?query={quote_plus(query)}"
    return await async_search_engine_base(
        url, parse_startpage_results, "Startpage", query, num_results
    )
