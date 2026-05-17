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


def _worker_increment(quota_dir: str, n: int) -> None:
    """Subprocess worker: bump 'google' n times against the shared file."""
    import os as _os
    import sys as _sys

    # Re-import in subprocess to get a fresh module state
    _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "src"))
    from websearch.utils import unified_quota as _uq

    # Point at shared dir
    _uq.get_quota_dir = lambda: __import__("pathlib").Path(quota_dir)
    mgr = _uq.UnifiedQuotaManager()
    mgr.configs = {
        "google": {"limit": 100_000, "period": "daily"},
        "brave": {"limit": 100_000, "period": "monthly"},
    }
    for _ in range(n):
        mgr.record_request("google")


def test_concurrent_increments_across_processes(tmp_path, monkeypatch):
    """fcntl file lock prevents lost updates between processes."""
    import multiprocessing as mp

    n_procs = 4
    per_proc = 25
    procs = [
        mp.get_context("spawn").Process(
            target=_worker_increment, args=(str(tmp_path), per_proc)
        )
        for _ in range(n_procs)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)
        assert p.exitcode == 0, f"worker exited {p.exitcode}"

    # Read the final state directly with a fresh manager. monkeypatch is
    # important: without it, get_quota_dir leaks tmp_path into later tests.
    from websearch.utils import unified_quota as uq_mod

    monkeypatch.setattr(uq_mod, "get_quota_dir", lambda: tmp_path)
    mgr = uq_mod.UnifiedQuotaManager()
    mgr.configs = {
        "google": {"limit": 100_000, "period": "daily"},
        "brave": {"limit": 100_000, "period": "monthly"},
    }
    assert mgr.get_usage("google")["used"] == n_procs * per_proc
