"""Unified quota management for all search APIs.

State is persisted atomically to a single JSON file via os.replace.
All read-modify-write operations execute under a single re-entrant lock so
concurrent **threads** cannot lose increments. For cross-process safety
(e.g. uvx spawning multiple MCP servers, or a server plus a CLI sharing
quotas.json), we additionally take an exclusive fcntl lock on a sibling
.lock file around the full read-modify-write window.
"""

import json
import logging
import os
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator

try:
    import fcntl  # POSIX only
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]

from ..config import BRAVE_MONTHLY_QUOTA, GOOGLE_DAILY_QUOTA
from .paths import get_quota_dir

logger = logging.getLogger(__name__)


@contextmanager
def _file_lock(lock_path: Path) -> Iterator[None]:
    """Cross-process exclusive lock via fcntl on POSIX; no-op elsewhere."""
    if fcntl is None:
        yield
        return
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # 'a' so the file is created if missing without truncating
    with open(lock_path, "a", encoding="utf-8") as fh:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


class UnifiedQuotaManager:
    """Unified quota manager for all search APIs."""

    def __init__(self):
        self.quota_dir = get_quota_dir()
        self.quota_file = self.quota_dir / "quotas.json"
        self.lock_file = self.quota_dir / "quotas.lock"
        google_limit = int(
            os.getenv("GOOGLE_DAILY_QUOTA", str(GOOGLE_DAILY_QUOTA))
        )
        brave_limit = int(
            os.getenv("BRAVE_MONTHLY_QUOTA", str(BRAVE_MONTHLY_QUOTA))
        )
        self.configs = {
            "google": {"limit": google_limit, "period": "daily"},
            "brave": {"limit": brave_limit, "period": "monthly"},
        }
        self._lock = threading.RLock()

    def _load_all_quotas_locked(self) -> Dict[str, Any]:
        if not self.quota_file.exists():
            return {}
        try:
            with open(self.quota_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error loading quotas (starting fresh): {e}")
            return {}

    def _save_all_quotas_locked(self, data: Dict[str, Any]) -> None:
        try:
            self.quota_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", dir=self.quota_dir, delete=False, encoding="utf-8"
            ) as temp_file:
                json.dump(data, temp_file, indent=2)
                temp_filename = temp_file.name
            os.chmod(temp_filename, 0o600)
            os.replace(temp_filename, self.quota_file)
        except OSError as e:
            logger.error(f"Error saving quotas: {e}")

    def _is_new_period(self, service: str, data: Dict[str, Any]) -> bool:
        config = self.configs[service]
        now = datetime.now(timezone.utc)

        if config["period"] == "daily":
            if not data.get("date"):
                return True
            try:
                last_date = datetime.fromisoformat(data["date"]).date()
            except (ValueError, TypeError):
                return True
            return now.date() > last_date

        if not data.get("month"):
            return True
        return f"{now.year}-{now.month:02d}" != data["month"]

    def _maybe_reset(
        self, service: str, all_quotas: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Reset quota for service if we're in a new period; returns service data."""
        config = self.configs[service]
        period_key = "date" if config["period"] == "daily" else "month"
        data = all_quotas.get(service, {period_key: None, "used": 0})

        if self._is_new_period(service, data):
            now = datetime.now(timezone.utc)
            if config["period"] == "daily":
                data = {"date": now.isoformat(), "used": 0}
            else:
                data = {"month": f"{now.year}-{now.month:02d}", "used": 0}
            all_quotas[service] = data
            self._save_all_quotas_locked(all_quotas)

        return data

    def can_make_request(self, service: str) -> bool:
        if service not in self.configs:
            return False
        # Lock order: thread RLock outside, fcntl inside. RLock is per-thread,
        # so the same thread re-entering get_usage from record_request still
        # works; fcntl is per-process so we serialize cross-process here.
        with self._lock, _file_lock(self.lock_file):
            all_quotas = self._load_all_quotas_locked()
            data = self._maybe_reset(service, all_quotas)
            return data.get("used", 0) < self.configs[service]["limit"]

    def record_request(self, service: str) -> None:
        if service not in self.configs:
            return
        with self._lock, _file_lock(self.lock_file):
            all_quotas = self._load_all_quotas_locked()
            data = self._maybe_reset(service, all_quotas)
            data["used"] = data.get("used", 0) + 1
            all_quotas[service] = data
            self._save_all_quotas_locked(all_quotas)

    def get_usage(self, service: str) -> Dict[str, Any]:
        if service not in self.configs:
            return {"used": 0, "limit": 0, "period": "unknown"}
        with self._lock, _file_lock(self.lock_file):
            all_quotas = self._load_all_quotas_locked()
            data = self._maybe_reset(service, all_quotas)
            return {
                "used": data.get("used", 0),
                "limit": self.configs[service]["limit"],
                "period": self.configs[service]["period"],
            }


# Global instance
unified_quota = UnifiedQuotaManager()
