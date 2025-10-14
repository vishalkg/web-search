"""File rotation utilities for logs and metrics."""

import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def get_rotated_file(base_path: Path, rotation_days: int) -> Path:
    """Get current file with rotation, creating new timestamped file if needed."""
    pattern = f"{base_path.stem}_*{base_path.suffix}"
    existing = sorted(base_path.parent.glob(pattern))

    if existing:
        latest = existing[-1]
        try:
            # Extract timestamp: web-search_2025-10-13.log -> 2025-10-13
            timestamp_str = latest.stem.split("_")[-1]
            file_date = datetime.strptime(timestamp_str, "%Y-%m-%d")

            # Check if still within rotation period
            days_since = (datetime.now(UTC).replace(tzinfo=None) - file_date).days
            if days_since < rotation_days:
                return latest

            # Rotation period passed - delete old files
            for old_file in existing:
                old_file.unlink()
                logger.info("Deleted old file: %s", old_file.name)
        except (ValueError, IndexError) as e:
            logger.warning("Failed to parse timestamp from %s: %s", latest, e)

    # Create new timestamped file
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d")
    new_file = base_path.parent / f"{base_path.stem}_{timestamp}{base_path.suffix}"
    logger.info("Created new rotated file: %s", new_file.name)
    return new_file
