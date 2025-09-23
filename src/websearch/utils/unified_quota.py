"""Unified quota management for all search APIs."""

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Thread lock for file operations
_quota_lock = threading.Lock()


def _ensure_secure_directory():
    """Create quota directory with secure permissions."""
    quota_dir = Path.home() / ".websearch"
    try:
        quota_dir.mkdir(mode=0o700, exist_ok=True)
        # Ensure directory has correct permissions
        os.chmod(quota_dir, 0o700)
        return quota_dir
    except Exception as e:
        logger.error(f"Failed to create secure quota directory: {e}")
        return quota_dir


QUOTA_DIR = _ensure_secure_directory()


class UnifiedQuotaManager:
    """Unified quota manager for all search APIs."""

    def __init__(self):
        self.configs = {
            "google": {
                "limit": int(os.getenv("GOOGLE_DAILY_QUOTA", "100")),
                "period": "daily",
                "file": QUOTA_DIR / "google_quota.json"
            },
            "brave": {
                "limit": int(os.getenv("BRAVE_MONTHLY_QUOTA", "2000")),
                "period": "monthly",
                "file": QUOTA_DIR / "brave_quota.json"
            }
        }

    def _load_quota(self, service: str) -> Dict[str, Any]:
        """Load quota data for a service with thread safety."""
        config = self.configs[service]
        quota_file = config["file"]

        with _quota_lock:
            if not quota_file.exists():
                period_key = "date" if config["period"] == "daily" else "month"
                return {period_key: None, "used": 0}

            try:
                with open(quota_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading quota for {service}: {e}")
                period_key = "date" if config["period"] == "daily" else "month"
                return {period_key: None, "used": 0}

    def _save_quota(self, service: str, data: Dict[str, Any]):
        """Save quota data with atomic write and secure permissions."""
        config = self.configs[service]
        quota_file = config["file"]

        with _quota_lock:
            try:
                # Atomic write: write to temp file, then rename
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    dir=quota_file.parent,
                    delete=False,
                    encoding='utf-8'
                ) as temp_file:
                    json.dump(data, temp_file, indent=2)
                    temp_filename = temp_file.name

                # Set secure permissions before moving
                os.chmod(temp_filename, 0o600)

                # Atomic rename
                os.rename(temp_filename, quota_file)

            except Exception as e:
                logger.error(f"Error saving quota for {service}: {e}")
                # Clean up temp file if it exists
                try:
                    if 'temp_filename' in locals():
                        os.unlink(temp_filename)
                except OSError:
                    pass

    def _is_new_period(self, service: str, data: Dict[str, Any]) -> bool:
        """Check if we're in a new quota period."""
        config = self.configs[service]
        now = datetime.now(timezone.utc)

        if config["period"] == "daily":
            if not data.get("date"):
                return True
            last_date = datetime.fromisoformat(data["date"]).date()
            return now.date() > last_date
        else:  # monthly
            if not data.get("month"):
                return True
            last_month = data["month"]
            current_month = f"{now.year}-{now.month:02d}"
            return current_month != last_month

    def can_make_request(self, service: str) -> bool:
        """Check if service can make a request within quota limits."""
        if service not in self.configs:
            return False

        config = self.configs[service]
        data = self._load_quota(service)

        # Reset quota if new period
        if self._is_new_period(service, data):
            now = datetime.now(timezone.utc)
            if config["period"] == "daily":
                data = {"date": now.isoformat(), "used": 0}
            else:  # monthly
                data = {"month": f"{now.year}-{now.month:02d}", "used": 0}
            self._save_quota(service, data)

        return data.get("used", 0) < config["limit"]

    def record_request(self, service: str):
        """Record a request for the service."""
        if service not in self.configs:
            return

        data = self._load_quota(service)
        data["used"] = data.get("used", 0) + 1
        self._save_quota(service, data)

    def get_usage(self, service: str) -> Dict[str, Any]:
        """Get current usage stats for a service."""
        if service not in self.configs:
            return {"used": 0, "limit": 0, "period": "unknown"}

        config = self.configs[service]
        data = self._load_quota(service)

        return {
            "used": data.get("used", 0),
            "limit": config["limit"],
            "period": config["period"]
        }


# Global instance
unified_quota = UnifiedQuotaManager()
