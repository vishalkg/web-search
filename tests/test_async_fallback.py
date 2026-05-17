"""Tests for async fallback orchestration and content cache flagging."""

from unittest.mock import AsyncMock, patch

import pytest

from websearch.core.async_fallback_search import (async_fallback_parallel_search,
                                                  async_search_with_fallback)
from websearch.core.content import fetch_single_page_content_async
from websearch.utils.cache import content_cache, get_cache_key


@pytest.mark.asyncio
async def test_content_cache_hit_marks_cached_true():
    """Cache-stored entry is `cached: False`; hit must re-stamp to True."""
    url = "https://example.com/page"
    content_cache.cache.clear()
    fake = {
        "url": url,
        "success": True,
        "content": "x",
        "content_length": 1,
        "truncated": False,
        "cached": False,
    }
    content_cache.set(get_cache_key(url), fake)
    out = await fetch_single_page_content_async(url)
    assert out["cached"] is True
    # Original cache entry untouched (still False) so subsequent hits still flip
    cached = content_cache.get(get_cache_key(url))
    assert cached["cached"] is False
    content_cache.cache.clear()


@pytest.mark.asyncio
async def test_primary_success_skips_fallback():
    primary = AsyncMock(return_value=[{"url": "u", "title": "t"}])
    fallback = AsyncMock(return_value=[{"url": "x", "title": "y"}])
    result = await async_search_with_fallback(primary, fallback, "q", 5)
    assert result == [{"url": "u", "title": "t"}]
    fallback.assert_not_called()


@pytest.mark.asyncio
async def test_primary_empty_triggers_fallback():
    primary = AsyncMock(return_value=[])
    fallback = AsyncMock(return_value=[{"url": "x", "title": "y"}])
    result = await async_search_with_fallback(primary, fallback, "q", 5)
    assert result == [{"url": "x", "title": "y"}]
    fallback.assert_called_once()


@pytest.mark.asyncio
async def test_primary_exception_triggers_fallback():
    primary = AsyncMock(side_effect=RuntimeError("boom"))
    fallback = AsyncMock(return_value=[{"url": "x", "title": "y"}])
    result = await async_search_with_fallback(primary, fallback, "q", 5)
    assert result == [{"url": "x", "title": "y"}]


@pytest.mark.asyncio
async def test_both_fail_returns_empty():
    primary = AsyncMock(side_effect=RuntimeError("p"))
    fallback = AsyncMock(side_effect=RuntimeError("f"))
    result = await async_search_with_fallback(primary, fallback, "q", 5)
    assert result == []


@pytest.mark.asyncio
async def test_fallback_parallel_three_branches():
    fake = [{"url": "u", "title": "t"}]
    with (
        patch(
            "websearch.core.async_fallback_search.async_search_google",
            new=AsyncMock(return_value=fake),
        ),
        patch(
            "websearch.core.async_fallback_search.async_search_startpage",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "websearch.core.async_fallback_search.async_search_bing",
            new=AsyncMock(return_value=fake),
        ),
        patch(
            "websearch.core.async_fallback_search.async_search_duckduckgo",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "websearch.core.async_fallback_search.async_search_brave",
            new=AsyncMock(return_value=fake),
        ),
    ):
        gs, bd, br = await async_fallback_parallel_search("q", 3)
        assert gs == fake
        assert bd == fake
        assert br == fake


@pytest.mark.asyncio
async def test_fallback_parallel_isolates_exceptions():
    """If one branch raises, the others must still return."""
    fake = [{"url": "u", "title": "t"}]
    with (
        patch(
            "websearch.core.async_fallback_search.async_search_google",
            new=AsyncMock(side_effect=RuntimeError("x")),
        ),
        patch(
            "websearch.core.async_fallback_search.async_search_startpage",
            new=AsyncMock(side_effect=RuntimeError("x")),
        ),
        patch(
            "websearch.core.async_fallback_search.async_search_bing",
            new=AsyncMock(return_value=fake),
        ),
        patch(
            "websearch.core.async_fallback_search.async_search_duckduckgo",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "websearch.core.async_fallback_search.async_search_brave",
            new=AsyncMock(return_value=fake),
        ),
    ):
        gs, bd, br = await async_fallback_parallel_search("q", 3)
        assert gs == []  # both google and startpage failed
        assert bd == fake
        assert br == fake
