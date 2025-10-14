"""File rotation utilities for logs and metrics."""

import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _should_rotate(file_path: Path, max_lines: int) -> bool:
    """Check if file needs rotation."""
    if not file_path.exists():
        return False

    # Quick check: file size > 1MB or line count
    if file_path.stat().st_size < 1_000_000:  # < 1MB
        return False

    try:
        with open(file_path, encoding='utf-8') as f:
            line_count = sum(1 for _ in f)
        return line_count > max_lines * 1.5  # Only rotate if 50% over
    except OSError:
        return False


def _rotate_file(file_path: Path, max_lines: int, max_days: int) -> None:
    """Rotate file by keeping only recent entries."""
    try:
        lines = file_path.read_text(encoding='utf-8').splitlines()

        # Filter by date if JSONL with timestamp
        if file_path.suffix == '.jsonl':
            cutoff = datetime.utcnow() - timedelta(days=max_days)
            filtered = []
            for line in lines:
                try:
                    import json
                    data = json.loads(line)
                    timestamp = data.get('timestamp', '').replace('Z', '+00:00')
                    ts = datetime.fromisoformat(timestamp)
                    if ts > cutoff:
                        filtered.append(line)
                except (ValueError, KeyError):
                    filtered.append(line)
            lines = filtered

        # Keep only last N lines
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
            file_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            logger.info("Rotated %s: kept %d lines", file_path.name, len(lines))

    except OSError as e:
        logger.error("Failed to rotate %s: %s", file_path, e)


def rotate_file_async(
    file_path: Path, max_lines: int = 1000, max_days: int = 30
) -> None:
    """Rotate file asynchronously if needed."""
    if not _should_rotate(file_path, max_lines):
        return

    thread = threading.Thread(
        target=_rotate_file,
        args=(file_path, max_lines, max_days),
        daemon=True
    )
    thread.start()
