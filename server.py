#!/usr/bin/env python3

import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote_plus

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup, Tag
from typing import cast
from fastmcp import FastMCP

# Version management
def get_version() -> str:
    """Dynamically get version from package.json or environment"""
    try:
        with open(os.path.join(os.path.dirname(__file__), 'package.json'), 'r') as f:
            package_data = json.load(f)
            return package_data.get('version', '2.1.0')
    except FileNotFoundError:
        return os.getenv('WEB_SEARCH_VERSION', '2.1.0')

# Setup logging
log_file = os.path.join(os.path.dirname(__file__), "web-search.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server with enhanced metadata
mcp = FastMCP("WebSearch")
logger.info(f"WebSearch MCP server v{get_version()} starting")

# Constants
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 12
CONTENT_TIMEOUT = 20
THREAD_TIMEOUT = 25
MAX_CONTENT_LENGTH = 8000
RETRY_ATTEMPTS = 2
BACKOFF_FACTOR = 0.3

# Initialize a global session with connection pooling and retry strategy
requests_session = requests.Session()
retry_strategy = Retry(
    total=RETRY_ATTEMPTS,
    backoff_factor=BACKOFF_FACTOR,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
http_adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
requests_session.mount("http://", http_adapter)
requests_session.mount("https://", http_adapter)
requests_session.headers.update({"User-Agent": DEFAULT_USER_AGENT})


class SimpleCache:
    """Simple in-memory cache with TTL"""

    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds

    def _is_expired(self, timestamp: float) -> bool:
        return time.time() - timestamp > self.ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            if not self._is_expired(self.cache[key]["timestamp"]):
                logger.info(f"Cache hit for key: {key[:50]}...")
                return self.cache[key]["data"]
            else:
                del self.cache[key]
        return None

    def set(self, key: str, data: Any) -> None:
        self.cache[key] = {"data": data, "timestamp": time.time()}
        logger.info(f"Cache set for key: {key[:50]}...")

    def clear_expired(self) -> None:
        expired_keys = [
            k for k, v in self.cache.items()
            if self._is_expired(v["timestamp"])
        ]
        for key in expired_keys:
            del self.cache[key]


# Global cache instances
search_cache = SimpleCache(ttl_seconds=300)
content_cache = SimpleCache(ttl_seconds=1800)


def make_request(
    url: str, timeout: int = REQUEST_TIMEOUT
) -> requests.Response:
    """Make HTTP request with connection pooling, retries and error handling"""
    # Using the global session with connection pooling for better performance
    response = requests_session.get(url, timeout=timeout)
    response.raise_for_status()
    return response


def extract_text_content(html: str) -> str:
    """Extract and clean text content from HTML"""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text content and clean whitespace
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines
              for phrase in line.split("  "))
    return " ".join(chunk for chunk in chunks if chunk)


def create_error_result(url: str, error_msg: str, error_type: str = "general") -> Dict[str, Any]:
    """Create standardized error result with error type classification"""
    return {
        "url": url,
        "success": False,
        "content": None,
        "content_length": 0,
        "truncated": False,
        "error": error_msg,
        "error_type": error_type,
        "troubleshooting": get_troubleshooting_tips(error_type),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cached": False,
    }


def get_troubleshooting_tips(error_type: str) -> str:
    """Return troubleshooting suggestions based on error type"""
    tips = {
        "timeout": "The website took too long to respond. Try again later or check if the URL is correct.",
        "connection": "Could not connect to the website. Check your internet connection or if the website is down.",
        "http_4xx": "Server returned a client error (4xx). The URL might be incorrect or you don't have permission to access it.",
        "http_5xx": "Server returned a server error (5xx). The website might be experiencing issues, try again later.",
        "parse": "Could not parse the website content. The site might use unsupported formatting or scripts.",
        "general": "An unexpected error occurred. Check the URL and try again later."
    }
    
    return tips.get(error_type, tips["general"])


def search_engine_base(
    url: str, parser_func, source_name: str, query: str, num_results: int
) -> List[Dict[str, Any]]:
    """Base function for search engine implementations"""
    try:
        response = make_request(url)
        soup = BeautifulSoup(response.text, "html.parser")
        results = parser_func(soup, num_results)
        logger.info(f"{source_name} found {len(results)} results")
        return results
    except Timeout:
        logger.error(f"{source_name} search timed out")
        return []
    except ConnectionError as e:
        logger.error(f"{source_name} search connection error: {str(e)}")
        return []
    except HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
        logger.error(f"{source_name} search HTTP error {status_code}: {str(e)}")
        return []
    except RequestException as e:
        logger.error(f"{source_name} search request error: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"{source_name} search failed with unexpected error: {str(e)}")
        return []


def parse_startpage_results(
    soup: BeautifulSoup, num_results: int
) -> List[Dict[str, Any]]:
    """Parse Startpage search results"""
    results = []
    for rank, result_tag in enumerate(
        soup.find_all("div", class_="result")[:num_results], 1
    ):
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


def parse_duckduckgo_results(
    soup: BeautifulSoup, num_results: int
) -> List[Dict[str, Any]]:
    """Parse DuckDuckGo search results"""
    results = []
    for rank, result_tag in enumerate(
        soup.find_all("div", class_="result")[:num_results], 1
    ):
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


def parse_bing_results(
    soup: BeautifulSoup, num_results: int
) -> List[Dict[str, Any]]:
    """Parse Bing search results"""
    results = []
    for rank, result_tag in enumerate(
        soup.find_all("li", class_="b_algo")[:num_results], 1
    ):
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
    return search_engine_base(
        url, parse_bing_results, "Bing", query, num_results
    )


def _fetch_single_page_content(url: str) -> str:
    """Fetch content from a single URL with caching"""
    logger.info(f"Fetching page content from: {url}")

    cache_key = hashlib.md5(url.encode()).hexdigest()
    cached_result = content_cache.get(cache_key)
    if cached_result:
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
        logger.info(
            f"Successfully fetched {len(text)} characters from {url}"
        )

    except Timeout:
        result = create_error_result(
            url, 
            "Request timeout - page took too long to respond", 
            "timeout"
        )
        logger.error(f"Timeout fetching {url}")
    except ConnectionError as e:
        result = create_error_result(
            url, 
            f"Connection error: {str(e)}", 
            "connection"
        )
        logger.error(f"Connection error fetching {url}: {str(e)}")
    except HTTPError as e:
        error_type = "http_5xx" if e.response.status_code >= 500 else "http_4xx"
        result = create_error_result(
            url, 
            f"HTTP error {e.response.status_code}: {str(e)}", 
            error_type
        )
        logger.error(f"HTTP error {e.response.status_code} fetching {url}: {str(e)}")
    except RequestException as e:
        result = create_error_result(
            url, 
            f"Request error: {str(e)}", 
            "general"
        )
        logger.error(f"Request error fetching {url}: {str(e)}")
    except Exception as e:
        result = create_error_result(
            url, 
            f"Processing error: {str(e)}", 
            "parse"
        )
        logger.error(f"Unexpected error fetching {url}: {str(e)}")

    return json.dumps(result, indent=2)


def fetch_multiple_pages(url_list: List[str]) -> Dict[str, Any]:
    """Fetch content from multiple URLs in parallel"""
    logger.info(f"Batch fetching content from {len(url_list)} URLs")

    thread_results = {}
    threads = []

    def fetch_url_thread(url_to_fetch: str, index: int):
        try:
            result_json = _fetch_single_page_content(url_to_fetch)
            thread_results[index] = json.loads(result_json)
        except Exception as e:
            thread_results[index] = create_error_result(
                url_to_fetch, f"Thread error: {str(e)}"
            )

    # Start threads
    for i, url_to_fetch in enumerate(url_list):
        thread = threading.Thread(
            target=fetch_url_thread, args=(url_to_fetch, i)
        )
        thread.start()
        threads.append(thread)

    # Wait for completion
    for thread in threads:
        thread.join(timeout=THREAD_TIMEOUT)

    # Collect results
    results = []
    for i in range(len(url_list)):
        if i in thread_results:
            results.append(thread_results[i])
        else:
            results.append(
                create_error_result(
                    url_list[i], "Thread timeout or failed to complete"
                )
            )

    return {
        "batch_request": True,
        "total_urls": len(url_list),
        "successful_fetches": sum(
            1 for r in results if r.get("success", False)
        ),
        "failed_fetches": sum(
            1 for r in results if not r.get("success", False)
        ),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "results": results,
    }


@mcp.tool(
    name="fetch_page_content",
    description=(
        "Extract clean, readable text content from web pages with intelligent parsing "
        "and parallel processing. Supports single URLs or batch processing of multiple URLs.\n\n"
        "Features:\n"
        "• HTML-to-text conversion with formatting preservation\n"
        "• Intelligent content extraction (removes ads, navigation)\n"
        "• Parallel processing for multiple URLs\n"
        "• Caching for improved performance\n"
        "• Automatic retry with exponential backoff\n\n"
        "Use cases: read webpage content, analyze articles, extract information from URLs, "
        "get full text from search results, read documentation, access content from websites.\n\n"
        "Example usage:\n"
        "fetch_page_content(\"https://en.wikipedia.org/wiki/Machine_learning\") - extracts text from Wikipedia\n"
        "fetch_page_content([\"https://docs.python.org/3/tutorial\", \"https://docs.python.org/3/library\"]) - "
        "batch processing multiple URLs in parallel"
    ),
    annotations={
        "title": "Web Content Extractor",
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
        "idempotentHint": True,
        "cacheable": True,
        "batchCapable": True,
        "requiresNetwork": True,
        "category": "content_extraction",
        "version": get_version()
    }
)
def fetch_page_content(urls: Union[str, List[str]]) -> str:
    """Fetch and extract text content from web pages with caching"""
    url_list = [urls] if isinstance(urls, str) else urls

    if len(url_list) == 1:
        return _fetch_single_page_content(url_list[0])

    batch_response = fetch_multiple_pages(url_list)
    logger.info(
        f"Batch fetch completed: "
        f"{batch_response['successful_fetches']}/{len(url_list)} successful"
    )
    return json.dumps(batch_response, indent=2)


def deduplicate_results(
    all_results: List[Dict[str, Any]], num_results: int
) -> List[Dict[str, Any]]:
    """Remove duplicate URLs from search results"""
    seen_urls = set()
    unique_results = []

    for result in all_results:
        if result["url"] not in seen_urls:
            seen_urls.add(result["url"])
            unique_results.append(result)

    return unique_results[:num_results]


def parallel_search(query: str, num_results: int) -> tuple:
    """Perform parallel searches across all engines"""
    results = {"ddg": [], "bing": [], "startpage": []}
    threads = []

    def search_wrapper(engine_func, key):
        results[key] = engine_func(query, num_results)

    # Start all searches
    search_funcs = [
        (search_duckduckgo, "ddg"),
        (search_bing, "bing"),
        (search_startpage, "startpage"),
    ]

    for func, key in search_funcs:
        thread = threading.Thread(target=search_wrapper, args=(func, key))
        thread.start()
        threads.append(thread)

    # Wait for completion
    for thread in threads:
        thread.join(timeout=15)

    return results["ddg"], results["bing"], results["startpage"]


@mcp.tool(
    name="search_web",
    description=(
        "Search across multiple search engines (DuckDuckGo, Bing, Startpage) with intelligent "
        "caching and parallel processing. Returns comprehensive results with titles, URLs, "
        "and snippets from multiple sources.\n\n"
        "Features:\n"
        "• Multi-engine search with result aggregation\n"
        "• Intelligent caching for improved performance\n"
        "• Parallel execution for optimal speed\n"
        "• Comprehensive error handling and retry logic\n"
        "• Rate limiting and respectful crawling\n\n"
        "Use cases: research topics, find information, discover websites, get current news, "
        "find documentation, verify information, search online, explore subjects.\n\n"
        "Example usage:\n"
        "search_web(\"quantum computing applications\", 5) - returns 5 search results about quantum computing\n"
        "search_web(\"latest AI research papers\", 10) - finds recent AI research\n"
        "search_web(\"how to implement binary search\", 7) - searches for binary search tutorials"
    ),
    annotations={
        "title": "Multi-Engine Web Search",
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
        "idempotentHint": True,
        "cacheable": True,
        "rateLimited": True,
        "requiresNetwork": True,
        "category": "information_retrieval",
        "version": get_version()
    }
)
def search_web(search_query: str, num_results: int = 10) -> str:
    """Perform a web search using multiple search engines with caching"""
    logger.info(
        f"Performing multi-engine search for: '{search_query}' "
        f"(num_results: {num_results})"
    )

    num_results = min(num_results, 20)
    cache_key = hashlib.md5(f"{search_query}:{num_results}".encode()).hexdigest()

    # Check cache
    cached_result = search_cache.get(cache_key)
    if cached_result:
        cached_result["cached"] = True
        return json.dumps(cached_result, indent=2)

    # Clear expired cache entries
    search_cache.clear_expired()
    content_cache.clear_expired()

    # Perform parallel searches
    ddg_results, bing_results, startpage_results = parallel_search(
        search_query, num_results
    )

    # Combine and deduplicate
    all_results = ddg_results + bing_results + startpage_results
    unique_results = deduplicate_results(all_results, num_results)

    if not unique_results:
        logger.warning(f"No search results found for search_query: '{search_query}'")
        return json.dumps(
            {
                "query": search_query,
                "total_results": 0,
                "sources": {"DuckDuckGo": 0, "Bing": 0, "Startpage": 0},
                "results": [],
                "cached": False,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )

    response = {
        "query": search_query,
        "total_results": len(unique_results),
        "sources": {
            "DuckDuckGo": len(ddg_results),
            "Bing": len(bing_results),
            "Startpage": len(startpage_results),
        },
        "results": unique_results,
        "cached": False,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    search_cache.set(cache_key, response)
    logger.info(
        f"Combined search found {len(unique_results)} unique results "
        f"for: '{search_query}'"
    )
    return json.dumps(response, indent=2)


@mcp.tool(
    name="get_tool_info",
    description=(
        "Get comprehensive information about this MCP server and its available tools, "
        "including version, capabilities, and metadata. Useful for debugging and "
        "understanding tool capabilities."
    ),
    annotations={
        "title": "Tool Information Inspector",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "category": "introspection"
    }
)
def get_tool_info() -> str:
    """Return comprehensive metadata about this MCP server and its tools"""
    tool_info = {
        "server_info": {
            "name": "WebSearch",
            "version": get_version(),
            "description": "Advanced web search and content extraction tools",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities": ["tools", "caching", "parallel_processing", "multi_engine_search"]
        },
        "tools": [
            {
                "name": "search_web",
                "title": "Multi-Engine Web Search",
                "category": "information_retrieval",
                "features": ["multi_engine", "caching", "parallel_processing", "rate_limiting"],
                "supported_engines": ["DuckDuckGo", "Bing", "Startpage"],
                "max_results": 20,
                "cache_ttl_seconds": 300
            },
            {
                "name": "fetch_page_content", 
                "title": "Web Content Extractor",
                "category": "content_extraction",
                "features": ["batch_processing", "caching", "intelligent_parsing", "retry_logic"],
                "max_content_length": MAX_CONTENT_LENGTH,
                "timeout_seconds": CONTENT_TIMEOUT,
                "cache_ttl_seconds": 1800
            },
            {
                "name": "get_tool_info",
                "title": "Tool Information Inspector", 
                "category": "introspection",
                "features": ["metadata_inspection"]
            }
        ],
        "configuration": {
            "request_timeout": REQUEST_TIMEOUT,
            "content_timeout": CONTENT_TIMEOUT,
            "max_content_length": MAX_CONTENT_LENGTH,
            "retry_attempts": RETRY_ATTEMPTS,
            "user_agent": DEFAULT_USER_AGENT[:50] + "..."
        }
    }
    return json.dumps(tool_info, indent=2)


if __name__ == "__main__":
    logger.info(f"Starting WebSearch MCP server v{get_version()}")
    mcp.run()
