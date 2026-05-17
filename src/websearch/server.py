#!/usr/bin/env python3
"""WebSearch MCP Server - Main server implementation with async optimizations."""

import asyncio
import json
import logging
from typing import List, Union

from fastmcp import FastMCP

from .config import MAX_BATCH_URLS, MAX_NUM_RESULTS
from .schemas import (BatchPageContent, PageContent, PageContentError,
                      QuotaStatus, SearchResponse, ServiceQuota,
                      ToolValidationError, _utc_now_z, page_content_from_dict)
from .utils.paths import find_env_file
from .utils.url_validation import URLValidationError, require_valid_url

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
from .core.content import fetch_single_page_content_async
from .utils.connection_pool import close_pool
from .utils.paths import get_log_file
from .utils.rotation import get_rotated_file

# Get rotated log file (weekly rotation)
log_file = get_rotated_file(get_log_file(), rotation_days=7)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("WebSearch")
logger.info(f"WebSearch MCP server v{__version__} starting with async optimizations")


def _clamp_num_results(num_results: int) -> int:
    if not isinstance(num_results, int) or num_results < 1:
        return 1
    return min(num_results, MAX_NUM_RESULTS)


def _url_validation_error(url: str, reason: str) -> PageContentError:
    return PageContentError(
        url=url,
        error=f"URL rejected: {reason}",
        error_type="validation",
    )


@mcp.tool(
    name="search_web",
    description=(
        "Search across multiple search engines (DuckDuckGo, Bing, Startpage, "
        "Google, Brave) with a 3-engine fallback system and parallel execution. "
        "Returns titles, URLs, and snippets from multiple sources.\n\n"
        "Fallback System:\n"
        "- Google API -> Startpage fallback (if quota exhausted)\n"
        "- Bing -> DuckDuckGo fallback (if blocked/failed)\n"
        "- Brave API (standalone)\n\n"
        "Parameters:\n"
        "- search_query (str): the query string\n"
        f"- num_results (int, 1-{MAX_NUM_RESULTS}, default 10): max results\n"
        "- force_refresh (bool, default False): bypass the search cache\n\n"
        "Returns a SearchResponse with: query, total_results, sources (per-engine "
        "counts), engine_distribution, results (list of {title, url, snippet, "
        "source, quality_score, rank}), and cached (bool). On invalid input "
        "returns a ToolValidationError instead."
    ),
)
async def search_web(
    search_query: str, num_results: int = 10, force_refresh: bool = False
) -> Union[SearchResponse, ToolValidationError]:
    """Perform a web search using multiple search engines with native async."""
    if not isinstance(search_query, str) or not search_query.strip():
        return ToolValidationError(error="search_query must be a non-empty string")

    raw = await async_search_web(
        search_query, _clamp_num_results(num_results), force_refresh=force_refresh
    )
    return SearchResponse.model_validate(json.loads(raw))


@mcp.tool(
    name="fetch_page_content",
    description=(
        "Extract clean, readable text content from web pages. Accepts a single URL "
        "string or a list of URLs (up to "
        f"{MAX_BATCH_URLS}); batch requests fetch concurrently.\n\n"
        "Only http/https URLs are accepted. Requests to private, loopback, or cloud "
        "metadata addresses are rejected with error_type='validation'. Per-URL "
        "errors carry an error_type the agent can branch on (timeout, connection, "
        "http_4xx, http_5xx, redirect, too_large, validation, parse, general).\n\n"
        "A single URL returns a PageContent (success or error). A list returns a "
        "BatchPageContent. An invalid input returns a ToolValidationError."
    ),
)
async def fetch_page_content(
    urls: Union[str, List[str]],
) -> Union[PageContent, BatchPageContent, ToolValidationError]:
    """Fetch and extract content from web pages using native async."""
    from .utils.tracking import (extract_tracking_from_url,
                                 log_selection_metrics)

    if isinstance(urls, str):
        logger.debug(f"Single URL fetch: {urls[:100]}")
        log_selection_metrics([urls])

        engine, search_id, clean_url = extract_tracking_from_url(urls)
        logger.debug(
            f"Extracted - Engine: {engine}, Search ID: {search_id}, "
            f"Clean URL: {clean_url[:50]}"
        )

        try:
            require_valid_url(clean_url)
        except URLValidationError as exc:
            return _url_validation_error(clean_url, str(exc))

        result_dict = await fetch_single_page_content_async(clean_url)
        return page_content_from_dict(result_dict)

    if not isinstance(urls, list) or not urls:
        return ToolValidationError(error="urls must be a non-empty list or string")
    if len(urls) > MAX_BATCH_URLS:
        return ToolValidationError(
            error=f"too many URLs (max {MAX_BATCH_URLS})", received=len(urls)
        )

    logger.info(f"Batch URL fetch: {len(urls)} URLs")
    log_selection_metrics(urls)

    async def fetch_with_tracking(url_to_fetch: str) -> dict:
        """Fetch a single URL with tracking extraction and error handling."""
        try:
            engine, search_id, clean_url = extract_tracking_from_url(url_to_fetch)
            logger.debug(
                f"Async fetch - Engine: {engine}, Clean URL: {clean_url[:50]}"
            )
            try:
                require_valid_url(clean_url)
            except URLValidationError as exc:
                return _url_validation_error(clean_url, str(exc)).model_dump()
            return await fetch_single_page_content_async(clean_url)
        except Exception as e:
            return {
                "url": url_to_fetch,
                "success": False,
                "error": f"Fetch error: {str(e)}",
                "error_type": "general",
                "timestamp": _utc_now_z(),
                "cached": False,
            }

    raw_results = await asyncio.gather(
        *[fetch_with_tracking(url) for url in urls],
        return_exceptions=True,
    )

    typed_results: List[PageContent] = []
    for url, raw in zip(urls, raw_results):
        if isinstance(raw, BaseException):
            typed_results.append(
                PageContentError(
                    url=url,
                    error=f"Unhandled error: {raw}",
                    error_type="general",
                )
            )
        else:
            typed_results.append(page_content_from_dict(raw))

    successful = sum(1 for r in typed_results if r.success)
    batch = BatchPageContent(
        total_urls=len(urls),
        successful_fetches=successful,
        failed_fetches=len(urls) - successful,
        results=typed_results,
    )
    logger.info(
        f"Async batch fetch completed: {successful}/{len(urls)} successful"
    )
    return batch


@mcp.tool(
    name="get_quota_status",
    description=(
        "Display current API quota usage for Google Custom Search and Brave Search. "
        "Returns per-service used/limit/period/percentage_used/remaining/status. "
        "Use this to monitor API usage before issuing quota-bound search calls."
    ),
)
def get_quota_status() -> QuotaStatus:
    """Get current quota status for all search APIs."""
    from .utils.unified_quota import unified_quota

    services: dict = {}
    for service in ["google", "brave"]:
        usage = unified_quota.get_usage(service)
        used = usage["used"]
        limit = usage["limit"]
        period = usage["period"]
        percentage = (used / limit * 100) if limit > 0 else 0
        remaining = max(0, limit - used)
        services[service] = ServiceQuota(
            used=used,
            limit=limit,
            period=period,
            percentage_used=round(percentage, 1),
            remaining=remaining,
            status="available" if remaining > 0 else "exhausted",
        ).model_dump()

    return QuotaStatus(services=services)


def main():
    """Main entry point for the server."""
    import atexit

    def cleanup():
        """Clean shutdown of connection pool. Best-effort: atexit may run after
        the FastMCP loop has already torn down."""
        logger.info("Shutting down WebSearch MCP Server")
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
            if loop.is_closed():
                return
            if loop.is_running():
                # FastMCP is still draining; schedule and let it finish
                loop.create_task(close_pool())
            else:
                loop.run_until_complete(close_pool())
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    atexit.register(cleanup)
    mcp.run()


if __name__ == "__main__":
    main()
