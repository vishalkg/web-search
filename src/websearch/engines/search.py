"""Search engine implementations."""

from typing import Any, Dict, List
from urllib.parse import quote_plus

from .base import search_engine_base
from .parsers import parse_bing_results, parse_duckduckgo_results, parse_startpage_results


def search_startpage(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Search Startpage"""
    url = f"https://www.startpage.com/sp/search?query={quote_plus(query)}"
    return search_engine_base(
        url, parse_startpage_results, "Startpage", query, num_results
    )


def search_duckduckgo(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Search DuckDuckGo"""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    return search_engine_base(
        url, parse_duckduckgo_results, "DuckDuckGo", query, num_results
    )


def search_bing(query: str, num_results: int) -> List[Dict[str, Any]]:
    """Search Bing"""
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    return search_engine_base(url, parse_bing_results, "Bing", query, num_results)
