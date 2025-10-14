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
        line_count = sum(1 for _ in open(file_path))
        return line_count > max_lines * 1.5  # Only rotate if 50% over limit
    except:
        return False


def _rotate_file(file_path: Path, max_lines: int, max_days: int) -> None:
    """Rotate file by keeping only recent entries."""
    try:
        lines = file_path.read_text().splitlines()
        
        # Filter by date if JSONL with timestamp
        if file_path.suffix == '.jsonl':
            cutoff = datetime.utcnow() - timedelta(days=max_days)
            filtered = []
            for line in lines:
                try:
                    import json
                    data = json.loads(line)
                    ts = datetime.fromisoformat(data.get('timestamp', '').replace('Z', '+00:00'))
                    if ts > cutoff:
                        filtered.append(line)
                except:
                    filtered.append(line)
            lines = filtered
        
        # Keep only last N lines
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
            file_path.write_text('\n'.join(lines) + '\n')
            logger.info(f"Rotated {file_path.name}: kept {len(lines)} lines")
    
    except Exception as e:
        logger.error(f"Failed to rotate {file_path}: {e}")


def rotate_file_async(file_path: Path, max_lines: int = 1000, max_days: int = 30) -> None:
    """Rotate file asynchronously if needed."""
    if not _should_rotate(file_path, max_lines):
        return
    
    thread = threading.Thread(
        target=_rotate_file,
        args=(file_path, max_lines, max_days),
        daemon=True
    )
    thread.start()
