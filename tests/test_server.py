"""Tests for MCP server tool handlers (Pydantic-typed responses)."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from websearch.schemas import (BatchPageContent, PageContentError,
                               PageContentSuccess, QuotaStatus, SearchResponse,
                               ToolValidationError)
from websearch.server import (_clamp_num_results, fetch_page_content,
                              get_quota_status, search_web)


def test_clamp_num_results():
    from websearch.config import MAX_NUM_RESULTS

    assert _clamp_num_results(0) == 1
    assert _clamp_num_results(-5) == 1
    assert _clamp_num_results(5) == 5
    assert _clamp_num_results(MAX_NUM_RESULTS + 100) == MAX_NUM_RESULTS
    assert _clamp_num_results("abc") == 1  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_search_web_rejects_empty_query():
    out = await search_web("   ", 5)
    assert isinstance(out, ToolValidationError)
    assert "non-empty string" in out.error
    assert out.error_type == "validation"


@pytest.mark.asyncio
async def test_search_web_returns_pydantic_model():
    fake_response = json.dumps(
        {
            "query": "q",
            "total_results": 1,
            "sources": {"Google/Startpage": 1, "Bing/DuckDuckGo": 0, "Brave": 0},
            "engine_distribution": {"google": 1},
            "results": [
                {
                    "title": "T",
                    "url": "https://example.com",
                    "snippet": "S",
                    "source": "google",
                    "quality_score": 9.0,
                    "rank": 1,
                }
            ],
            "cached": False,
        }
    )
    with patch(
        "websearch.server.async_search_web", new=AsyncMock(return_value=fake_response)
    ):
        out = await search_web("hello", 5)

    assert isinstance(out, SearchResponse)
    assert out.query == "q"
    assert out.results[0].source == "google"
    # Pydantic validation enforces shape
    dumped = out.model_dump()
    assert dumped["results"][0]["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_search_web_clamps_num_results_and_passes_force_refresh():
    fake_response = json.dumps(
        {
            "query": "q",
            "total_results": 0,
            "sources": {"Google/Startpage": 0, "Bing/DuckDuckGo": 0, "Brave": 0},
            "engine_distribution": {},
            "results": [],
            "cached": False,
        }
    )
    with patch(
        "websearch.server.async_search_web", new=AsyncMock(return_value=fake_response)
    ) as mock_search:
        await search_web("hello", 9999, force_refresh=True)
    args, kwargs = mock_search.call_args
    from websearch.config import MAX_NUM_RESULTS
    assert args[1] == MAX_NUM_RESULTS
    assert kwargs == {"force_refresh": True}


@pytest.mark.asyncio
async def test_fetch_page_content_rejects_private_url():
    out = await fetch_page_content("http://127.0.0.1/admin")
    assert isinstance(out, PageContentError)
    assert out.error_type == "validation"
    assert out.success is False


@pytest.mark.asyncio
async def test_fetch_page_content_rejects_unsupported_scheme():
    out = await fetch_page_content("ftp://example.com")
    assert isinstance(out, PageContentError)
    assert out.error_type == "validation"


@pytest.mark.asyncio
async def test_fetch_page_content_rejects_oversize_batch():
    from websearch.config import MAX_BATCH_URLS

    urls = ["https://example.com"] * (MAX_BATCH_URLS + 1)
    out = await fetch_page_content(urls)
    assert isinstance(out, ToolValidationError)
    assert out.received == MAX_BATCH_URLS + 1


@pytest.mark.asyncio
async def test_fetch_page_content_returns_typed_success():
    fake_dict = {
        "url": "https://example.com",
        "success": True,
        "content": "hello",
        "content_length": 5,
        "truncated": False,
        "cached": False,
        "error": None,
    }
    with patch(
        "websearch.server.fetch_single_page_content_async",
        new=AsyncMock(return_value=fake_dict),
    ), patch(
        "websearch.utils.url_validation.socket.gethostbyname_ex",
        return_value=("h", [], ["93.184.216.34"]),
    ):
        out = await fetch_page_content("https://example.com")
    assert isinstance(out, PageContentSuccess)
    assert out.content_length == 5


@pytest.mark.asyncio
async def test_fetch_page_content_batch_filters_invalid():
    fake_dict = {
        "url": "https://example.com",
        "success": True,
        "content": "x",
        "content_length": 1,
        "truncated": False,
        "cached": False,
        "error": None,
    }
    with patch(
        "websearch.server.fetch_single_page_content_async",
        new=AsyncMock(return_value=fake_dict),
    ), patch(
        "websearch.utils.url_validation.socket.gethostbyname_ex",
        return_value=("h", [], ["93.184.216.34"]),
    ):
        out = await fetch_page_content(
            ["https://example.com", "http://127.0.0.1/"]
        )
    assert isinstance(out, BatchPageContent)
    assert out.total_urls == 2
    assert out.successful_fetches == 1
    assert out.failed_fetches == 1
    # Per-URL types preserved
    types = sorted(type(r).__name__ for r in out.results)
    assert types == ["PageContentError", "PageContentSuccess"]


def test_get_quota_status_returns_typed_model():
    out = get_quota_status()
    assert isinstance(out, QuotaStatus)
    assert "google" in out.services
    assert "brave" in out.services
    google = out.services["google"]
    for key in {"used", "limit", "period", "percentage_used", "remaining", "status"}:
        assert key in google


@pytest.mark.asyncio
async def test_mcp_call_tool_round_trip():
    """Smoke test that FastMCP serializes the typed return correctly."""
    from websearch.server import mcp

    fake_response = json.dumps(
        {
            "query": "q",
            "total_results": 0,
            "sources": {"Google/Startpage": 0, "Bing/DuckDuckGo": 0, "Brave": 0},
            "engine_distribution": {},
            "results": [],
            "cached": False,
        }
    )
    with patch(
        "websearch.server.async_search_web", new=AsyncMock(return_value=fake_response)
    ):
        result = await mcp.call_tool("search_web", {"search_query": "hi"})
    # FastMCP returns ToolResult with both text content and structured_content.
    # Union return types are wrapped in {"result": ...} by the MCP schema.
    assert hasattr(result, "structured_content")
    sc = result.structured_content
    payload = sc.get("result", sc)
    assert payload["query"] == "q"
    assert "results" in payload
    # Text content carries the same JSON
    parsed_text = json.loads(result.content[0].text)
    assert parsed_text["query"] == "q"
