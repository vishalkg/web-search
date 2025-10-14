"""File rotation utilities for logs and metrics."""

import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def rotate_file(file_path: Path, max_lines: int = 1000, max_days: int = 30) -> None:
    """Rotate file by keeping only recent entries."""
    if not file_path.exists():
        return
    
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
                    filtered.append(line)  # Keep if can't parse
            lines = filtered
        
        # Keep only last N lines
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
            file_path.write_text('\n'.join(lines) + '\n')
            logger.info(f"Rotated {file_path.name}: kept {len(lines)} lines")
    
    except Exception as e:
        logger.error(f"Failed to rotate {file_path}: {e}")
