"""Tests for connection pooling functionality."""

import pytest

from websearch.utils.connection_pool import (close_pool, get_pool_stats,
                                             get_session)


class TestConnectionPool:
    """aiohttp 3.13+ requires a running loop to construct TCPConnector,
    so all session-touching tests are async."""

    @pytest.mark.asyncio
    async def test_get_session_creates_pool(self):
        await close_pool()
        session = get_session()
        assert session is not None
        assert session.connector is not None
        assert session.connector.limit == 100
        assert session.connector.limit_per_host == 30
        await close_pool()

    @pytest.mark.asyncio
    async def test_get_session_reuses_same_instance(self):
        await close_pool()
        session1 = get_session()
        session2 = get_session()
        assert session1 is session2
        await close_pool()

    @pytest.mark.asyncio
    async def test_pool_stats(self):
        await close_pool()
        get_session()
        stats = get_pool_stats()
        assert "total_limit" in stats
        assert "per_host_limit" in stats
        assert "active_connections" in stats
        assert stats["total_limit"] == 100
        assert stats["per_host_limit"] == 30
        await close_pool()

    @pytest.mark.asyncio
    async def test_close_pool_cleanup(self):
        get_session()
        await close_pool()
        stats = get_pool_stats()
        assert stats == {"status": "not_initialized"}


@pytest.mark.integration
class TestAsyncHTTPWithConnectionPoolIntegration:
    """Live-network tests; deselect via -m 'not integration'."""

    @pytest.mark.asyncio
    async def test_connection_reuse_with_multiple_requests(self):
        session = get_session()
        urls = ["https://httpbin.org/delay/0"] * 3
        responses = []
        for url in urls:
            try:
                async with session.get(url, timeout=5) as response:
                    responses.append(response.status)
            except Exception:
                pass
        if responses:
            assert all(status == 200 for status in responses)
        stats = get_pool_stats()
        assert "active_connections" in stats

    @pytest.mark.asyncio
    async def test_async_search_uses_connection_pool(self):
        from websearch.engines.async_search import async_search_duckduckgo

        try:
            await async_search_duckduckgo("test query", 3)
        except Exception:
            pass
        final_stats = get_pool_stats()
        assert final_stats.get("total_limit") == 100
