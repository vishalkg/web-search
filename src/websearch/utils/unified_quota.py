"""Unified quota management for all search APIs."""

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from typing import Any, Dict

from .paths import get_quota_dir

logger = logging.getLogger(__name__)

# Thread lock for file operations
_quota_lock = threading.Lock()


class UnifiedQuotaManager:
    """Unified quota manager for all search APIs."""

    def __init__(self):
        self.quota_dir = get_quota_dir()
        self.quota_file = self.quota_dir / "quotas.json"
        self.configs = {
            "google": {
                "limit": int(os.getenv("GOOGLE_DAILY_QUOTA", "100")),
                "period": "daily",
            },
            "brave": {
                "limit": int(os.getenv("BRAVE_MONTHLY_QUOTA", "2000")),
                "period": "monthly",
            },
        }

    def _load_all_quotas(self) -> Dict[str, Any]:
        """Load all quota data from single file."""
        with _quota_lock:
            if not self.quota_file.exists():
                return {}
            try:
                with open(self.quota_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading quotas: {e}")
                return {}

    def _save_all_quotas(self, data: Dict[str, Any]) -> None:
        """Save all quota data to single file."""
        with _quota_lock:
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", dir=self.quota_dir, delete=False, encoding="utf-8"
                ) as temp_file:
                    json.dump(data, temp_file, indent=2)
                    temp_filename = temp_file.name

                os.chmod(temp_filename, 0o600)
                os.replace(temp_filename, self.quota_file)
            except Exception as e:
                logger.error(f"Error saving quotas: {e}")

    def _load_quota(self, service: str) -> Dict[str, Any]:
        """Load quota data for a service."""
        all_quotas = self._load_all_quotas()
        config = self.configs[service]
        period_key = "date" if config["period"] == "daily" else "month"
        return all_quotas.get(service, {period_key: None, "used": 0})

    def _save_quota(self, service: str, data: Dict[str, Any]):
        """Save quota data for a service."""
        all_quotas = self._load_all_quotas()
        all_quotas[service] = data
        self._save_all_quotas(all_quotas)

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
            "period": config["period"],
        }


# Global instance
unified_quota = UnifiedQuotaManager()
