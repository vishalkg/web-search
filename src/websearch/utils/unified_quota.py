"""Unified quota management for all search APIs."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

QUOTA_DIR = Path.home() / ".websearch"
QUOTA_DIR.mkdir(exist_ok=True)


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
        """Load quota data for a service."""
        config = self.configs[service]
        quota_file = config["file"]

        if not quota_file.exists():
            period_key = "date" if config["period"] == "daily" else "month"
            return {period_key: None, "used": 0}

        try:
            with open(quota_file, "r") as f:
                return json.load(f)
        except Exception:
            period_key = "date" if config["period"] == "daily" else "month"
            return {period_key: None, "used": 0}

    def _save_quota(self, service: str, data: Dict[str, Any]):
        """Save quota data for a service."""
        quota_file = self.configs[service]["file"]
        try:
            with open(quota_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save {service} quota: {e}")

    def _is_new_period(self, service: str, data: Dict[str, Any]) -> bool:
        """Check if we're in a new quota period."""
        config = self.configs[service]
        now = datetime.now(timezone.utc)

        if config["period"] == "daily":
            current_date = now.strftime("%Y-%m-%d")
            return data.get("date") != current_date
        else:  # monthly
            current_month = now.strftime("%Y-%m")
            return data.get("month") != current_month

    def can_make_request(self, service: str) -> bool:
        """Check if service can make a request within quota."""
        if service not in self.configs:
            return True  # Unknown service, allow request

        data = self._load_quota(service)
        config = self.configs[service]

        # Reset quota if new period
        if self._is_new_period(service, data):
            now = datetime.now(timezone.utc)
            if config["period"] == "daily":
                data = {"date": now.strftime("%Y-%m-%d"), "used": 0}
            else:
                data = {"month": now.strftime("%Y-%m"), "used": 0}
            self._save_quota(service, data)

        return data["used"] < config["limit"]

    def record_request(self, service: str):
        """Record a request for the service."""
        if service not in self.configs:
            return

        data = self._load_quota(service)
        config = self.configs[service]

        # Reset if new period
        if self._is_new_period(service, data):
            now = datetime.now(timezone.utc)
            if config["period"] == "daily":
                data = {"date": now.strftime("%Y-%m-%d"), "used": 0}
            else:
                data = {"month": now.strftime("%Y-%m"), "used": 0}

        data["used"] += 1
        self._save_quota(service, data)

        logger.info(f"{service.title()} API usage: {data['used']}/{config['limit']}")

    def get_usage(self, service: str) -> Dict[str, Any]:
        """Get current usage for a service."""
        if service not in self.configs:
            return {"used": 0, "limit": 0, "remaining": 0}

        data = self._load_quota(service)
        config = self.configs[service]

        # Reset if new period
        if self._is_new_period(service, data):
            data = {"used": 0}

        return {
            "used": data.get("used", 0),
            "limit": config["limit"],
            "remaining": config["limit"] - data.get("used", 0),
            "period": config["period"]
        }


# Global instances
unified_quota = UnifiedQuotaManager()

# Backward compatibility - keep existing interfaces
quota_manager = type('GoogleQuotaManager', (), {
    'can_make_request': lambda: unified_quota.can_make_request("google"),
    'record_request': lambda: unified_quota.record_request("google"),
    'get_usage': lambda: unified_quota.get_usage("google")
})()
