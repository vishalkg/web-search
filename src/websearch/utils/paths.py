"""Path utilities for websearch installation independence."""

import os
from pathlib import Path


def get_websearch_home() -> Path:
    """Get websearch home directory, independent of repo."""
    home = os.getenv('WEBSEARCH_HOME', os.path.expanduser('~/.websearch'))
    return Path(home)


def get_config_dir() -> Path:
    """Get configuration directory."""
    return get_websearch_home() / 'config'


def get_data_dir() -> Path:
    """Get data directory."""
    return get_websearch_home() / 'data'


def get_logs_dir() -> Path:
    """Get logs directory."""
    return get_websearch_home() / 'logs'


def get_quota_dir() -> Path:
    """Get quota directory."""
    return get_data_dir() / 'quota'


def ensure_directories():
    """Create all necessary directories."""
    dirs = [
        get_websearch_home(),
        get_config_dir(),
        get_data_dir(),
        get_logs_dir(),
        get_quota_dir()
    ]

    for directory in dirs:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)


def get_metrics_file() -> Path:
    """Get metrics file path."""
    ensure_directories()
    return get_data_dir() / 'search-metrics.jsonl'


def get_log_file() -> Path:
    """Get log file path."""
    ensure_directories()
    return get_logs_dir() / 'web-search.log'


def find_env_file() -> Path:
    """Find .env file in priority order."""
    # Priority order for .env loading
    candidates = [
        Path.cwd() / '.env',  # Current directory (highest priority)
        get_config_dir() / '.env',  # User config
        Path.home() / '.websearch' / '.env',  # Legacy location
    ]

    for env_file in candidates:
        if env_file.exists():
            return env_file

    # Return default location for creation
    ensure_directories()
    return get_config_dir() / '.env'
