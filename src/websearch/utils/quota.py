"""Google API quota management."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

QUOTA_FILE = Path(__file__).parent.parent / "google_quota.json"
DAILY_LIMIT = 100


class GoogleQuotaManager:
    def __init__(self):
        self._quota_data = self._load_quota()

    def _load_quota(self) -> dict:
        """Load quota data from file."""
        if not QUOTA_FILE.exists():
            return {"date": None, "used": 0}

        try:
            with open(QUOTA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {"date": None, "used": 0}

    def _save_quota(self):
        """Save quota data to file."""
        try:
            with open(QUOTA_FILE, "w") as f:
                json.dump(self._quota_data, f)
        except Exception as e:
            logger.error(f"Failed to save quota data: {e}")

    def _is_new_day(self) -> bool:
        """Check if it's a new UTC day."""
        today = datetime.now(timezone.utc).date().isoformat()
        return self._quota_data.get("date") != today

    def can_make_request(self) -> bool:
        """Check if we can make a request within quota."""
        if self._is_new_day():
            self._quota_data = {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "used": 0
            }
            self._save_quota()

        return self._quota_data["used"] < DAILY_LIMIT

    def record_request(self):
        """Record a successful API request."""
        if self._is_new_day():
            self._quota_data = {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "used": 0
            }

        self._quota_data["used"] += 1
        self._save_quota()
        logger.info(
            f"Google API quota used: {self._quota_data['used']}/{DAILY_LIMIT}"
        )

    def get_remaining(self) -> int:
        """Get remaining quota for today."""
        if self._is_new_day():
            return DAILY_LIMIT
        return max(0, DAILY_LIMIT - self._quota_data["used"])


# Global instance
quota_manager = GoogleQuotaManager()
