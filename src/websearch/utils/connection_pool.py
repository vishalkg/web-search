#!/usr/bin/env python3
"""Connection pool manager for HTTP requests with connection reuse."""

import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """Global connection pool for all HTTP requests with optimal configuration."""

    def __init__(self):
        """Initialize connection pool manager (actual session created lazily)."""
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure connection pool is initialized (must be called in async context)."""
        if self._initialized:
            return

        self._connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Max connections per host
            ttl_dns_cache=300,  # DNS cache for 5 minutes
            enable_cleanup_closed=True,  # Clean up closed connections
            force_close=False,  # Enable connection reuse
            keepalive_timeout=30,  # Keep connections alive 30s
        )

        timeout = aiohttp.ClientTimeout(
            total=30,  # Total timeout
            connect=10,  # Connection timeout
            sock_read=20,  # Socket read timeout
        )

        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers={"User-Agent": "WebSearch-MCP/2.1.0"},
        )

        self._initialized = True
        logger.info(
            f"Connection pool initialized: limit={self._connector.limit}, "
            f"per_host={self._connector.limit_per_host}"
        )

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get the session, initializing if needed."""
        self._ensure_initialized()
        return self._session

    @property
    def connector(self) -> aiohttp.TCPConnector:
        """Get the connector, initializing if needed."""
        self._ensure_initialized()
        return self._connector

    async def close(self):
        """Clean shutdown of connection pool."""
        if not self._initialized:
            return

        logger.info("Closing connection pool")
        if self._session:
            await self._session.close()
        if self._connector:
            await self._connector.close()
        self._initialized = False

    def get_stats(self) -> dict:
        """Get connection pool statistics."""
        if not self._initialized:
            return {"status": "not_initialized"}

        return {
            "total_limit": self._connector.limit,
            "per_host_limit": self._connector.limit_per_host,
            "active_connections": len(self._connector._conns),  # pylint: disable=protected-access
        }


# Global connection pool instance
_pool_manager: Optional[ConnectionPoolManager] = None  # pylint: disable=invalid-name


def get_session() -> aiohttp.ClientSession:
    """
    Get the global HTTP session with connection pooling.

    Returns:
        aiohttp.ClientSession: Shared session with connection pool

    Example:
        >>> session = get_session()
        >>> async with session.get(url) as response:
        ...     data = await response.text()
    """
    global _pool_manager  # pylint: disable=global-statement
    if _pool_manager is None:
        _pool_manager = ConnectionPoolManager()
    return _pool_manager.session


async def close_pool():
    """Close the global connection pool."""
    global _pool_manager  # pylint: disable=global-statement
    if _pool_manager:
        await _pool_manager.close()
        _pool_manager = None


def get_pool_stats() -> dict:
    """Get connection pool statistics."""
    global _pool_manager  # pylint: disable=global-statement,global-variable-not-assigned
    if _pool_manager:
        return _pool_manager.get_stats()
    return {"status": "not_initialized"}
