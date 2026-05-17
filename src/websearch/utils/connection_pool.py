#!/usr/bin/env python3
"""Connection pool manager for HTTP requests with connection reuse."""

import logging
from typing import Optional

import aiohttp

from ..config import (POOL_CONNECT_TIMEOUT, POOL_DNS_CACHE_SECONDS,
                      POOL_KEEPALIVE_SECONDS, POOL_PER_HOST_LIMIT,
                      POOL_SOCK_READ_TIMEOUT, POOL_TOTAL_LIMIT,
                      POOL_TOTAL_TIMEOUT, USER_AGENT)

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """Global connection pool for all HTTP requests with optimal configuration."""

    def __init__(self):
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return

        # enable_cleanup_closed dropped in 3.12+ aiohttp because the upstream
        # CPython bug it worked around (cpython#118960) is fixed.
        self._connector = aiohttp.TCPConnector(
            limit=POOL_TOTAL_LIMIT,
            limit_per_host=POOL_PER_HOST_LIMIT,
            ttl_dns_cache=POOL_DNS_CACHE_SECONDS,
            force_close=False,
            keepalive_timeout=POOL_KEEPALIVE_SECONDS,
        )

        timeout = aiohttp.ClientTimeout(
            total=POOL_TOTAL_TIMEOUT,
            connect=POOL_CONNECT_TIMEOUT,
            sock_read=POOL_SOCK_READ_TIMEOUT,
        )

        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )

        self._initialized = True
        logger.info(
            f"Connection pool initialized: limit={self._connector.limit}, "
            f"per_host={self._connector.limit_per_host}"
        )

    @property
    def session(self) -> aiohttp.ClientSession:
        self._ensure_initialized()
        return self._session

    @property
    def connector(self) -> aiohttp.TCPConnector:
        self._ensure_initialized()
        return self._connector

    async def close(self):
        if not self._initialized:
            return

        logger.info("Closing connection pool")
        if self._session:
            await self._session.close()
        if self._connector:
            await self._connector.close()
        self._initialized = False

    def get_stats(self) -> dict:
        if not self._initialized:
            return {"status": "not_initialized"}

        return {
            "total_limit": self._connector.limit,
            "per_host_limit": self._connector.limit_per_host,
            # pylint: disable=protected-access
            "active_connections": len(self._connector._conns),
        }


# Global connection pool instance
_pool_manager: Optional[ConnectionPoolManager] = None  # pylint: disable=invalid-name


def get_session() -> aiohttp.ClientSession:
    """Get the global HTTP session with connection pooling."""
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
    # pylint: disable=global-statement,global-variable-not-assigned
    global _pool_manager
    if _pool_manager:
        return _pool_manager.get_stats()
    return {"status": "not_initialized"}
