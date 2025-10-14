#!/usr/bin/env python3
"""WebSearch MCP Server - Main server implementation with async optimizations."""

import asyncio
import json
import logging
import threading
from datetime import datetime
from typing import List, Union

from fastmcp import FastMCP

from .utils.paths import get_log_file, find_env_file

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = find_env_file()
    if env_file.exists():
        load_dotenv(env_file)
        logging.info(f"Loaded environment variables from {env_file}")
    else:
        logging.info("No .env file found, using system environment variables")
except ImportError:
    logging.warning("python-dotenv not installed, skipping .env file loading")

from . import __version__
from .core.async_search import async_search_web_fallback as async_search_web
from .core.content import fetch_single_page_content
from .core.search import search_web_fallback as sync_search_web
from .utils.rotation import rotate_file_async
from .utils.paths import get_metrics_file

# Setup logging
log_file = get_log_file()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Rotate files on startup (non-blocking, only if needed)
rotate_file_async(log_file, max_lines=1000)
rotate_file_async(get_metrics_file(), max_lines=1000, max_days=30)

# Initialize FastMCP server
mcp = FastMCP("WebSearch")
logger.info(f"WebSearch MCP server v{__version__} starting with async optimizations")


@mcp.tool(
    name="search_web",
    description=(
        "Search across multiple search engines (DuckDuckGo, Bing, Startpage, "
        "Google, Brave) with intelligent 3-engine fallback system and parallel "
        "processing. Returns comprehensive results with titles, URLs, and snippets "
        "from multiple sources.\n\n"
        "Fallback System:\n"
        "• Google API → Startpage fallback (if quota exhausted)\n"
        "• Bing → DuckDuckGo fallback (if blocked/failed)\n"
        "• Brave API (standalone)\n\n"
        "Features:\n"
        "• 3-engine fallback with result aggregation\n"
        "• Intelligent caching for improved performance\n"
        "• Parallel execution for optimal speed\n"
        "• Comprehensive error handling and retry logic\n"
        "• Rate limiting and respectful crawling\n\n"
        "Use cases: research topics, find information, discover websites, get current "
        "news, find documentation, verify information, search online, explore "
        "subjects.\n\n"
        "Example usage:\n"
        'search_web("quantum computing applications", 5) - returns 5 search results '
        "about quantum computing\n"
        'search_web("latest AI research papers", 10) - finds recent AI research\n'
        'search_web("how to implement binary search", 7) - searches for binary search '
        "tutorials"
    ),
)
def search_web(search_query: str, num_results: int = 10) -> str:
    """Perform a web search using multiple search engines with async optimizations"""
    try:
        # Use async implementation for better performance
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                async_search_web(search_query, num_results)
            )
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
        "Extract clean, readable text content from web pages with intelligent parsing "
        "and parallel processing. Supports single URLs or batch processing of multiple "
        "URLs.\n\n"
        "Features:\n"
        "• HTML-to-text conversion with formatting preservation\n"
        "• Intelligent content extraction (removes ads, navigation)\n"
        "• Parallel processing for multiple URLs\n"
        "• Caching for improved performance\n"
        "• Automatic retry with exponential backoff\n\n"
        "Use cases: read webpage content, analyze articles, extract information from "
        "URLs, get full text from search results, read documentation, access content "
        "from websites.\n\n"
        "Example usage:\n"
        'fetch_page_content("https://en.wikipedia.org/wiki/Machine_learning") - '
        "extracts text from Wikipedia\n"
        'fetch_page_content(["https://docs.python.org/3/tutorial", '
        '"https://docs.python.org/3/library"]) - batch processing multiple URLs in '
        "parallel"
    ),
)
def fetch_page_content(urls: Union[str, List[str]]) -> str:
    """Fetch and extract content from web pages"""
    from .utils.tracking import (extract_tracking_from_url,
                                 log_selection_metrics)

    # Handle single URL
    if isinstance(urls, str):
        logger.info(f"📥 DEBUG: Single URL fetch: {urls[:100]}...")

        # Log single URL selection
        log_selection_metrics([urls])

        # Extract tracking and get clean URL
        engine, search_id, clean_url = extract_tracking_from_url(urls)
        logger.info(
            f"📥 DEBUG: Extracted - Engine: {engine}, Search ID: {search_id}, "
            f"Clean URL: {clean_url[:50]}..."
        )

        return fetch_single_page_content(clean_url)

    # Log batch URL selections
    logger.info(f"📥 DEBUG: Batch URL fetch: {len(urls)} URLs")
    for i, url in enumerate(urls):
        logger.info(f"📥 DEBUG: URL {i+1}: {url[:100]}...")

    log_selection_metrics(urls)

    # Batch processing for multiple URLs
    logger.info(f"Starting batch fetch for {len(urls)} URLs")

    results = []
    threads = []
    thread_results = {}

    def fetch_url_thread(url_to_fetch: str, index: int):
        try:
            # Extract tracking and get clean URL
            engine, search_id, clean_url = extract_tracking_from_url(url_to_fetch)
            logger.info(
                f"📥 DEBUG: Thread {index} - Engine: {engine}, "
                f"Clean URL: {clean_url[:50]}..."
            )
            result_json = fetch_single_page_content(clean_url)
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


@mcp.tool(
    name="get_quota_status",
    description=(
        "Display current API quota usage for search engines. Shows used/limit "
        "and quota period (daily/monthly) for Google and Brave APIs.\n\n"
        "Returns quota information including:\n"
        "• Current usage count\n"
        "• Total quota limit\n"
        "• Quota period (daily for Google, monthly for Brave)\n"
        "• Percentage used\n"
        "• Remaining quota\n\n"
        "Use this to monitor API usage and avoid hitting quota limits."
    ),
)
def get_quota_status() -> str:
    """Get current quota status for all search APIs"""
    from .utils.unified_quota import unified_quota

    quota_status = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {}
    }

    for service in ["google", "brave"]:
        usage = unified_quota.get_usage(service)
        used = usage["used"]
        limit = usage["limit"]
        period = usage["period"]

        percentage = (used / limit * 100) if limit > 0 else 0
        remaining = max(0, limit - used)

        quota_status["services"][service] = {
            "used": used,
            "limit": limit,
            "period": period,
            "percentage_used": round(percentage, 1),
            "remaining": remaining,
            "status": "available" if remaining > 0 else "exhausted"
        }

    return json.dumps(quota_status, indent=2)


def main():
    """Main entry point for the server"""
    mcp.run()


if __name__ == "__main__":
    main()
