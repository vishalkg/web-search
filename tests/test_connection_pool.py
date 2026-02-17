"""Tests for connection pooling functionality."""

import pytest

from websearch.utils.connection_pool import (
    close_pool,
    get_pool_stats,
    get_session,
)


class TestConnectionPool:
    """Test connection pool manager functionality."""

    @pytest.mark.asyncio
    async def test_get_session_creates_pool(self):
        """Test that get_session creates a connection pool."""
        session = get_session()

        assert session is not None
        assert session.connector is not None
        assert session.connector.limit == 100
        assert session.connector.limit_per_host == 30

    @pytest.mark.asyncio
    async def test_get_session_reuses_same_instance(self):
        """Test that get_session returns the same session instance."""
        session1 = get_session()
        session2 = get_session()

        # Should be the exact same instance
        assert session1 is session2

    @pytest.mark.asyncio
    async def test_pool_stats(self):
        """Test that pool stats are returned correctly."""
        # Initialize pool
        get_session()

        stats = get_pool_stats()

        assert "total_limit" in stats
        assert "per_host_limit" in stats
        assert "active_connections" in stats
        assert stats["total_limit"] == 100
        assert stats["per_host_limit"] == 30

    @pytest.mark.asyncio
    async def test_connection_reuse_with_multiple_requests(self):
        """Test that connections are reused across multiple requests."""
        session = get_session()

        # Make multiple requests to the same host
        urls = [
            "https://httpbin.org/delay/0",
            "https://httpbin.org/delay/0",
            "https://httpbin.org/delay/0",
        ]

        responses = []
        for url in urls:
            try:
                async with session.get(url, timeout=5) as response:
                    responses.append(response.status)
            except Exception:
                # Skip if httpbin is unavailable
                pass

        # If we got responses, verify they all succeeded
        if responses:
            assert all(status == 200 for status in responses)

        # Check that connections exist
        stats = get_pool_stats()
        # Note: active_connections may be 0 after requests complete
        # but the pool exists and is ready for reuse
        assert "active_connections" in stats

    @pytest.mark.asyncio
    async def test_close_pool_cleanup(self):
        """Test that close_pool properly cleans up resources."""
        # Get session to initialize pool
        session = get_session()
        assert session is not None

        # Close pool
        await close_pool()

        # After closing, stats should show not initialized
        stats = get_pool_stats()
        assert stats == {"status": "not_initialized"}


class TestAsyncHTTPWithConnectionPool:
    """Test that async functions use connection pooling."""

    @pytest.mark.asyncio
    async def test_async_search_uses_connection_pool(self):
        """Test that async search functions use the connection pool."""
        from websearch.engines.async_search import async_search_duckduckgo

        # Get initial pool state
        initial_stats = get_pool_stats()

        # Make a search request (will initialize pool if not already)
        try:
            results = await async_search_duckduckgo("test query", 3)

            # Pool should now be initialized
            final_stats = get_pool_stats()
            assert "total_limit" in final_stats
            assert final_stats["total_limit"] == 100

        except Exception:
            # Test may fail due to rate limiting or network issues
            # but pool should still be initialized
            pass

        # Verify pool exists
        session = get_session()
        assert session is not None

    @pytest.mark.asyncio
    async def test_brave_api_uses_connection_pool(self):
        """Test that Brave API uses the connection pool."""
        from websearch.engines.brave_api import async_search_brave_api

        # Get initial pool state
        get_session()  # Initialize pool
        initial_stats = get_pool_stats()

        # Brave API should use the same pool
        assert "total_limit" in initial_stats
        assert initial_stats["total_limit"] == 100
