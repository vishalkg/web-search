"""Brave Search API quota management."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Brave API limits: 2000 requests per month
MONTHLY_LIMIT = 2000
QUOTA_FILE = Path.home() / ".websearch" / "brave_quota.json"


class BraveQuotaManager:
    """Manages Brave API quota tracking."""

    def __init__(self):
        QUOTA_FILE.parent.mkdir(exist_ok=True)
        self._quota_data = self._load_quota()

    def _load_quota(self) -> dict:
        """Load quota data from file."""
        if not QUOTA_FILE.exists():
            return {"month": None, "used": 0}

        try:
            with open(QUOTA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {"month": None, "used": 0}

    def _save_quota(self):
        """Save quota data to file."""
        try:
            with open(QUOTA_FILE, "w") as f:
                json.dump(self._quota_data, f)
        except Exception as e:
            logger.error(f"Failed to save Brave quota data: {e}")

    def _is_new_month(self) -> bool:
        """Check if it's a new month."""
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        return self._quota_data.get("month") != current_month

    def can_make_request(self) -> bool:
        """Check if we can make a request within quota."""
        if self._is_new_month():
            self._quota_data = {
                "month": datetime.now(timezone.utc).strftime("%Y-%m"),
                "used": 0
            }
            self._save_quota()

        return self._quota_data["used"] < MONTHLY_LIMIT

    def record_request(self):
        """Record a successful API request."""
        if self._is_new_month():
            self._quota_data = {
                "month": datetime.now(timezone.utc).strftime("%Y-%m"),
                "used": 0
            }

        self._quota_data["used"] += 1
        self._save_quota()
        logger.info(
            f"Brave API quota used: {self._quota_data['used']}/{MONTHLY_LIMIT}"
        )

    def get_usage(self) -> dict:
        """Get current quota usage."""
        return {
            "used": self._quota_data["used"],
            "limit": MONTHLY_LIMIT,
            "remaining": MONTHLY_LIMIT - self._quota_data["used"],
            "month": self._quota_data.get("month")
        }


# Global quota manager instance
quota_manager = BraveQuotaManager()
