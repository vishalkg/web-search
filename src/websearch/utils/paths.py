"""Path utilities for websearch installation independence."""

import os
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir, user_log_dir


def get_websearch_home() -> Path:
    """Get websearch home directory, independent of repo."""
    # Allow override via env var, otherwise use OS-appropriate location
    if home := os.getenv("WEBSEARCH_HOME"):
        return Path(home)
    return Path(user_data_dir("websearch", appauthor=False))


def get_config_dir() -> Path:
    """Get configuration directory."""
    if home := os.getenv("WEBSEARCH_HOME"):
        return Path(home) / "config"
    return Path(user_config_dir("websearch", appauthor=False))


def get_data_dir() -> Path:
    """Get data directory."""
    return get_websearch_home() / "data"


def get_logs_dir() -> Path:
    """Get logs directory."""
    if home := os.getenv("WEBSEARCH_HOME"):
        return Path(home) / "logs"
    return Path(user_log_dir("websearch", appauthor=False))


def get_quota_dir() -> Path:
    """Get quota directory."""
    return get_data_dir() / "quota"


def ensure_directories():
    """Create all necessary directories."""
    dirs = [
        get_websearch_home(),
        get_config_dir(),
        get_data_dir(),
        get_logs_dir(),
        get_quota_dir(),
    ]

    for directory in dirs:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)


def get_metrics_file() -> Path:
    """Get metrics file path."""
    ensure_directories()
    return get_data_dir() / "search-metrics.jsonl"


def get_log_file() -> Path:
    """Get log file path."""
    ensure_directories()
    return get_logs_dir() / "web-search.log"


def find_env_file() -> Path:
    """Find .env file in priority order.

    Only ever resolves under the websearch home/config locations — never the
    process CWD. As an MCP server the CWD is arbitrary (it's whatever project
    the MCP client launched us from), so honoring a CWD .env let an unrelated
    project's .env silently hijack config: it would be loaded first, lack the
    search API keys, and — since load_dotenv doesn't override already-set
    values — leave Google/Brave unconfigured, dropping the server to Bing
    scraping.
    """
    # Priority order for .env loading (all under ~/.websearch via WEBSEARCH_HOME)
    candidates = [
        get_config_dir() / ".env",  # User config (WEBSEARCH_HOME/config)
        Path.home() / ".websearch" / ".env",  # Legacy location
    ]

    for env_file in candidates:
        if env_file.exists():
            return env_file

    # Return default location for creation
    ensure_directories()
    return get_config_dir() / ".env"
