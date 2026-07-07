"""Tests for path resolution — notably that .env is resolved independent of CWD."""

import os
from pathlib import Path

from websearch.utils import paths


def test_find_env_file_ignores_cwd(tmp_path, monkeypatch):
    """A .env in the process CWD must NOT be picked up.

    Regression: as an MCP server the CWD is whatever project launched us, so a
    CWD .env (lacking search keys) used to hijack config and silently disable
    the Google/Brave API engines. find_env_file must resolve only under the
    websearch config home.
    """
    # Arrange: a decoy .env in the CWD, and a real one in the config home.
    cwd = tmp_path / "some_project"
    cwd.mkdir()
    (cwd / ".env").write_text("DECOY=1\n")
    monkeypatch.chdir(cwd)

    home = tmp_path / "wshome"
    monkeypatch.setenv("WEBSEARCH_HOME", str(home))
    config_env = paths.get_config_dir() / ".env"
    config_env.parent.mkdir(parents=True, exist_ok=True)
    config_env.write_text("GOOGLE_CSE_API_KEY=real\n")

    # Act
    found = paths.find_env_file()

    # Assert: the config-home .env wins; the CWD decoy is never returned.
    assert found == config_env
    assert found != cwd / ".env"


def test_find_env_file_falls_back_to_legacy_location(tmp_path, monkeypatch):
    """When no config .env exists, the legacy ~/.websearch/.env is used."""
    home = tmp_path / "home"
    (home / ".websearch").mkdir(parents=True)
    legacy = home / ".websearch" / ".env"
    legacy.write_text("LEGACY=1\n")

    # No WEBSEARCH_HOME → get_config_dir uses platformdirs; point HOME at tmp.
    monkeypatch.delenv("WEBSEARCH_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    found = paths.find_env_file()
    assert found == legacy
