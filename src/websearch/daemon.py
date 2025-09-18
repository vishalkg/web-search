#!/usr/bin/env python3
"""Daemon management for WebSearch MCP server."""

import os
import sys
import signal
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DaemonManager:
    def __init__(self, pid_file: str = None):
        if pid_file is None:
            pid_file = os.path.join(os.path.dirname(__file__), "../../websearch.pid")
        self.pid_file = Path(pid_file)
    
    def write_pid(self):
        """Write current process PID to file."""
        self.pid_file.write_text(str(os.getpid()))
        logger.info(f"PID {os.getpid()} written to {self.pid_file}")
    
    def read_pid(self) -> int:
        """Read PID from file."""
        if not self.pid_file.exists():
            return None
        try:
            return int(self.pid_file.read_text().strip())
        except (ValueError, FileNotFoundError):
            return None
    
    def is_running(self) -> bool:
        """Check if daemon is running."""
        pid = self.read_pid()
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    def stop_daemon(self) -> bool:
        """Stop running daemon."""
        pid = self.read_pid()
        if not pid:
            logger.info("No PID file found")
            return False
        
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to process {pid}")
            return True
        except OSError as e:
            logger.error(f"Failed to stop process {pid}: {e}")
            return False
    
    def cleanup(self):
        """Clean up PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()
            logger.info(f"Removed PID file {self.pid_file}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
