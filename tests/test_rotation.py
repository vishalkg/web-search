"""Tests for file rotation utilities."""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.websearch.utils.rotation import get_rotated_file


class TestRotation:
    """Test file rotation logic."""

    def test_creates_timestamped_file(self):
        """Test that rotation creates timestamped file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "test.log"

            rotated = get_rotated_file(base_path, rotation_days=7)

            # Should have timestamp in name
            assert "_" in rotated.name
            assert rotated.name.startswith("test_")
            assert rotated.name.endswith(".log")

            # Should match YYYY-MM-DD pattern
            timestamp_str = rotated.stem.split("_")[-1]
            datetime.strptime(timestamp_str, "%Y-%m-%d")  # Should not raise

    def test_reuses_file_within_rotation_period(self):
        """Test that file is reused if within rotation period."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "test.log"

            # Create first file
            file1 = get_rotated_file(base_path, rotation_days=7)
            file1.touch()

            # Get file again - should return same file
            file2 = get_rotated_file(base_path, rotation_days=7)

            assert file1 == file2

    def test_creates_new_file_after_rotation_period(self):
        """Test that new file is created after rotation period."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "test.log"

            # Create old file with past timestamp
            old_date = (datetime.now(UTC) - timedelta(days=8)).strftime("%Y-%m-%d")
            old_file = Path(temp_dir) / f"test_{old_date}.log"
            old_file.touch()

            # Get rotated file - should create new one
            new_file = get_rotated_file(base_path, rotation_days=7)

            assert new_file != old_file
            assert not old_file.exists()  # Old file should be deleted

    def test_deletes_multiple_old_files(self):
        """Test that all old files are deleted on rotation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "test.log"

            # Create multiple old files
            for days_ago in [8, 15, 30]:
                old_date = (datetime.now(UTC) - timedelta(days=days_ago)).strftime(
                    "%Y-%m-%d"
                )
                old_file = Path(temp_dir) / f"test_{old_date}.log"
                old_file.touch()

            # Get rotated file - should delete old files
            new_file = get_rotated_file(base_path, rotation_days=7)

            # Old files should be deleted
            old_files = [f for f in Path(temp_dir).glob("test_*.log") if f != new_file]
            assert len(old_files) == 0

    def test_handles_different_extensions(self):
        """Test rotation works with different file extensions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "metrics.jsonl"

            rotated = get_rotated_file(base_path, rotation_days=30)

            assert rotated.name.startswith("metrics_")
            assert rotated.name.endswith(".jsonl")
