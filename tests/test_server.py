"""Tests for MCP server tool handlers."""

import json
from unittest.mock import AsyncMock, patch

import pytest

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
    assert "must be a non-empty string" in out


@pytest.mark.asyncio
async def test_search_web_clamps_num_results_and_passes_force_refresh():
    fake_response = json.dumps({"query": "q", "results": [], "total_results": 0})
    with patch(
        "websearch.server.async_search_web",
        new=AsyncMock(return_value=fake_response),
    ) as mock_search:
        await search_web("hello", 9999, force_refresh=True)
    args, kwargs = mock_search.call_args
    from websearch.config import MAX_NUM_RESULTS
    assert args[1] == MAX_NUM_RESULTS
    assert kwargs == {"force_refresh": True}


@pytest.mark.asyncio
async def test_fetch_page_content_rejects_private_url():
    out = await fetch_page_content("http://127.0.0.1/admin")
    parsed = json.loads(out)
    assert parsed["success"] is False
    assert parsed["error_type"] == "validation"


@pytest.mark.asyncio
async def test_fetch_page_content_rejects_unsupported_scheme():
    out = await fetch_page_content("ftp://example.com")
    parsed = json.loads(out)
    assert parsed["success"] is False
    assert parsed["error_type"] == "validation"


@pytest.mark.asyncio
async def test_fetch_page_content_rejects_oversize_batch():
    from websearch.config import MAX_BATCH_URLS

    urls = ["https://example.com"] * (MAX_BATCH_URLS + 1)
    out = await fetch_page_content(urls)
    parsed = json.loads(out)
    assert parsed["error_type"] == "validation"
    assert parsed["received"] == MAX_BATCH_URLS + 1


@pytest.mark.asyncio
async def test_fetch_page_content_batch_filters_invalid():
    """Mixed batch: one valid (mocked) and one private URL."""
    fake_dict = {"url": "u", "success": True, "content": "x", "content_length": 1}
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
    parsed = json.loads(out)
    assert parsed["batch_request"] is True
    assert parsed["successful_fetches"] == 1
    assert parsed["failed_fetches"] == 1


def test_get_quota_status_shape():
    out = get_quota_status()
    parsed = json.loads(out)
    assert "timestamp" in parsed
    assert "services" in parsed
    assert "google" in parsed["services"]
    assert "brave" in parsed["services"]
    for svc in parsed["services"].values():
        assert {"used", "limit", "period", "percentage_used", "remaining", "status"} <= set(
            svc.keys()
        )
