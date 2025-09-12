#!/usr/bin/env python3
"""WebSearch MCP Server - Main server implementation with async optimizations."""

import asyncio
import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Union

from fastmcp import FastMCP

from . import __version__
from .core.content import fetch_single_page_content
from .core.search import search_web as sync_search_web
from .core.async_search import async_search_web

# Setup logging
log_file = os.path.join(os.path.dirname(__file__), "web-search.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("WebSearch")
logger.info(f"WebSearch MCP server v{__version__} starting with async optimizations")


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
        "version": __version__
    }
)
def search_web(search_query: str, num_results: int = 10) -> str:
    """Perform a web search using multiple search engines with async optimizations"""
    try:
        # Use async implementation for better performance
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(async_search_web(search_query, num_results))
            return result
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Async search failed, falling back to sync: {e}")
        # Fallback to sync implementation
        return sync_search_web(search_query, num_results)


@mcp.tool(
    name="fetch_page_content",
    description=(
        "Extract clean, readable text content from web pages with intelligent parsing and "
        "parallel processing. Supports single URLs or batch processing of multiple URLs.\n\n"
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
        "fetch_page_content([\"https://docs.python.org/3/tutorial\", \"https://docs.python.org/3/library\"]) - batch processing multiple URLs in parallel"
    ),
    annotations={
        "title": "Web Page Content Extraction",
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
        "idempotentHint": True,
        "cacheable": True,
        "rateLimited": True,
        "requiresNetwork": True,
        "category": "content_extraction",
        "version": __version__
    }
)
def fetch_page_content(urls: Union[str, List[str]]) -> str:
    """Fetch and extract content from web pages"""
    if isinstance(urls, str):
        return fetch_single_page_content(urls)
    
    # Batch processing for multiple URLs
    logger.info(f"Starting batch fetch for {len(urls)} URLs")
    
    results = []
    threads = []
    thread_results = {}
    
    def fetch_url_thread(url_to_fetch: str, index: int):
        try:
            result_json = fetch_single_page_content(url_to_fetch)
            thread_results[index] = json.loads(result_json)
        except Exception as e:
            thread_results[index] = {
                "url": url_to_fetch,
                "success": False,
                "error": f"Thread error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cached": False,
            }
    
    # Start threads for parallel fetching
    for i, url_to_fetch in enumerate(urls):
        thread = threading.Thread(target=fetch_url_thread, args=(url_to_fetch, i))
        thread.start()
        threads.append(thread)
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join(timeout=25)
    
    # Collect results in order
    for i in range(len(urls)):
        if i in thread_results:
            results.append(thread_results[i])
    
    batch_response = {
        "batch_request": True,
        "total_urls": len(urls),
        "successful_fetches": sum(1 for r in results if r.get("success", False)),
        "failed_fetches": sum(1 for r in results if not r.get("success", False)),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "results": results,
    }
    
    logger.info(
        f"Batch fetch completed: "
        f"{batch_response['successful_fetches']}/{len(urls)} successful"
    )
    return json.dumps(batch_response, indent=2)


def main():
    """Main entry point for the server"""
    mcp.run()


if __name__ == "__main__":
    main()
