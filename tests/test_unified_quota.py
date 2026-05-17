"""Tests for unified quota manager."""

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def quota_manager(tmp_path, monkeypatch):
    """Build a fresh manager pointed at tmp_path with small limits."""
    from websearch.utils import unified_quota as uq_mod

    monkeypatch.setattr(uq_mod, "get_quota_dir", lambda: tmp_path)
    manager = uq_mod.UnifiedQuotaManager()
    # Override limits to keep tests fast
    manager.configs = {
        "google": {"limit": 3, "period": "daily"},
        "brave": {"limit": 3, "period": "monthly"},
    }
    return manager


def test_can_make_request_when_no_state(quota_manager):
    assert quota_manager.can_make_request("google") is True
    assert quota_manager.can_make_request("brave") is True


def test_unknown_service_rejected(quota_manager):
    assert quota_manager.can_make_request("yahoo") is False


def test_record_increments_until_exhausted(quota_manager):
    for _ in range(3):
        assert quota_manager.can_make_request("google")
        quota_manager.record_request("google")
    assert quota_manager.can_make_request("google") is False


def test_get_usage_reflects_increments(quota_manager):
    quota_manager.record_request("brave")
    usage = quota_manager.get_usage("brave")
    assert usage == {"used": 1, "limit": 3, "period": "monthly"}


def test_daily_reset(quota_manager, tmp_path):
    # Pre-populate state from yesterday with usage at the cap
    yesterday = datetime.now(timezone.utc) - timedelta(days=2)
    state = {"google": {"date": yesterday.isoformat(), "used": 999}}
    (tmp_path / "quotas.json").write_text(json.dumps(state))
    # Daily reset should kick in
    assert quota_manager.can_make_request("google") is True
    assert quota_manager.get_usage("google")["used"] == 0


def test_monthly_reset(quota_manager, tmp_path):
    state = {"brave": {"month": "2000-01", "used": 999}}
    (tmp_path / "quotas.json").write_text(json.dumps(state))
    assert quota_manager.can_make_request("brave") is True
    assert quota_manager.get_usage("brave")["used"] == 0


def test_corrupt_file_recovers(quota_manager, tmp_path):
    (tmp_path / "quotas.json").write_text("not json {")
    # Should not raise, should treat as empty
    assert quota_manager.can_make_request("google") is True


def test_concurrent_increments_are_atomic(quota_manager):
    """Increments from many threads should sum correctly."""
    quota_manager.configs["google"] = {"limit": 1000, "period": "daily"}
    threads = []
    for _ in range(50):
        t = threading.Thread(target=quota_manager.record_request, args=("google",))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    assert quota_manager.get_usage("google")["used"] == 50
