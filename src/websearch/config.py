"""Centralized configuration for tunable constants.

All timeouts, pool sizes, cache TTLs, and rate limits live here so they can
be tuned in one place instead of scattered across modules. Values may be
overridden via environment variables for deployment flexibility.
"""

import os


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


# HTTP / connection pool
POOL_TOTAL_LIMIT = _int_env("WEBSEARCH_POOL_LIMIT", 100)
POOL_PER_HOST_LIMIT = _int_env("WEBSEARCH_POOL_PER_HOST", 30)
POOL_DNS_CACHE_SECONDS = _int_env("WEBSEARCH_POOL_DNS_TTL", 300)
POOL_KEEPALIVE_SECONDS = _int_env("WEBSEARCH_POOL_KEEPALIVE", 30)
POOL_TOTAL_TIMEOUT = _int_env("WEBSEARCH_POOL_TIMEOUT_TOTAL", 30)
POOL_CONNECT_TIMEOUT = _int_env("WEBSEARCH_POOL_TIMEOUT_CONNECT", 10)
POOL_SOCK_READ_TIMEOUT = _int_env("WEBSEARCH_POOL_TIMEOUT_READ", 20)

# Content fetching
CONTENT_TIMEOUT = _int_env("WEBSEARCH_CONTENT_TIMEOUT", 15)
MAX_CONTENT_LENGTH = _int_env("WEBSEARCH_MAX_CONTENT_LENGTH", 50_000)
MAX_RESPONSE_BYTES = _int_env("WEBSEARCH_MAX_RESPONSE_BYTES", 5_000_000)
MAX_REDIRECTS = _int_env("WEBSEARCH_MAX_REDIRECTS", 5)

# Cache TTLs (seconds)
SEARCH_CACHE_TTL = _int_env("WEBSEARCH_SEARCH_CACHE_TTL", 300)
CONTENT_CACHE_TTL = _int_env("WEBSEARCH_CONTENT_CACHE_TTL", 1800)
SEARCH_CACHE_SIZE = _int_env("WEBSEARCH_SEARCH_CACHE_SIZE", 500)
CONTENT_CACHE_SIZE = _int_env("WEBSEARCH_CONTENT_CACHE_SIZE", 200)

# Search request bounds
MAX_NUM_RESULTS = _int_env("WEBSEARCH_MAX_NUM_RESULTS", 20)
MAX_BATCH_URLS = _int_env("WEBSEARCH_MAX_BATCH_URLS", 20)

# Per-engine rate limits as (min_delay, max_delay) seconds with jitter
RATE_LIMITS = {
    "duckduckgo": (1.5, 3.0),
    "bing": (1.0, 2.5),
    "startpage": (2.0, 4.0),
}

# Quotas (used by unified_quota; env vars retained for backward compat)
GOOGLE_DAILY_QUOTA = _int_env("GOOGLE_DAILY_QUOTA", 100)
BRAVE_MONTHLY_QUOTA = _int_env("BRAVE_MONTHLY_QUOTA", 2000)

def _default_user_agent() -> str:
    """Build the default UA from package version. Override via env var."""
    from . import __version__

    return f"WebSearch-MCP/{__version__}"


USER_AGENT = os.getenv("WEBSEARCH_USER_AGENT") or _default_user_agent()
