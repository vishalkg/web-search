"""Search result parsers for different engines."""

from typing import Any, Dict, List, cast

from bs4 import BeautifulSoup, Tag


def parse_startpage_results(soup: BeautifulSoup, num_results: int) -> List[Dict[str, Any]]:
    """Parse Startpage search results"""
    results = []
    for rank, result_tag in enumerate(soup.find_all("div", class_="result")[:num_results], 1):
        result = cast(Tag, result_tag)
        title_elem = result.find("a", class_="result-link")

        if title_elem and isinstance(title_elem, Tag):
            title = title_elem.get_text().strip()
            url_found = title_elem.get("href")
        else:
            title = None
            url_found = None

        snippet_elem = result.find("p", class_="description")
        if snippet_elem and isinstance(snippet_elem, Tag):
            snippet = snippet_elem.get_text().strip()
        else:
            snippet = "No description"

        if title and url_found:
            results.append(
                {
                    "title": title,
                    "url": url_found,
                    "snippet": snippet,
                    "source": "Startpage",
                    "rank": rank,
                }
            )
    return results


def parse_duckduckgo_results(soup: BeautifulSoup, num_results: int) -> List[Dict[str, Any]]:
    """Parse DuckDuckGo search results"""
    results = []
    for rank, result_tag in enumerate(soup.find_all("div", class_="result")[:num_results], 1):
        result = cast(Tag, result_tag)
        title_elem = result.find("a", class_="result__a")

        if title_elem and isinstance(title_elem, Tag):
            title = title_elem.get_text().strip()
            url_found = title_elem.get("href")
        else:
            title = None
            url_found = None

        snippet_elem = result.find("a", class_="result__snippet")
        if snippet_elem and isinstance(snippet_elem, Tag):
            snippet = snippet_elem.get_text().strip()
        else:
            snippet = "No description"

        if title and url_found:
            results.append(
                {
                    "title": title,
                    "url": url_found,
                    "snippet": snippet,
                    "source": "DuckDuckGo",
                    "rank": rank,
                }
            )
    return results


def parse_bing_results(soup: BeautifulSoup, num_results: int) -> List[Dict[str, Any]]:
    """Parse Bing search results"""
    results = []
    for rank, result_tag in enumerate(soup.find_all("li", class_="b_algo")[:num_results], 1):
        result = cast(Tag, result_tag)
        title_elem = result.find("h2")
        title = None
        url_found = None

        if title_elem and isinstance(title_elem, Tag):
            link_elem = title_elem.find("a")
            if link_elem and isinstance(link_elem, Tag):
                title = link_elem.get_text().strip()
                url_found = link_elem.get("href")

        snippet_elem = result.find("p")
        if snippet_elem and isinstance(snippet_elem, Tag):
            snippet = snippet_elem.get_text().strip()
        else:
            snippet = "No description"

        if title and url_found:
            results.append(
                {
                    "title": title,
                    "url": url_found,
                    "snippet": snippet,
                    "source": "Bing",
                    "rank": rank,
                }
            )
    return results
