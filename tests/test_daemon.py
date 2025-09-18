#!/usr/bin/env python3
"""Unit tests for daemon management."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from websearch.daemon import DaemonManager


class TestDaemonManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.pid_file = os.path.join(self.temp_dir, "test.pid")
        self.daemon = DaemonManager(self.pid_file)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.pid_file).exists():
            Path(self.pid_file).unlink()
        os.rmdir(self.temp_dir)
    
    def test_write_and_read_pid(self):
        """Test PID file writing and reading."""
        test_pid = 12345
        
        with patch('os.getpid', return_value=test_pid):
            self.daemon.write_pid()
        
        self.assertTrue(Path(self.pid_file).exists())
        self.assertEqual(self.daemon.read_pid(), test_pid)
    
    def test_read_pid_no_file(self):
        """Test reading PID when file doesn't exist."""
        self.assertIsNone(self.daemon.read_pid())
    
    def test_read_pid_invalid_content(self):
        """Test reading PID with invalid file content."""
        Path(self.pid_file).write_text("invalid")
        self.assertIsNone(self.daemon.read_pid())
    
    def test_is_running_no_pid_file(self):
        """Test is_running when no PID file exists."""
        self.assertFalse(self.daemon.is_running())
    
    @patch('os.kill')
    def test_is_running_process_exists(self, mock_kill):
        """Test is_running when process exists."""
        Path(self.pid_file).write_text("12345")
        mock_kill.return_value = None  # No exception means process exists
        
        self.assertTrue(self.daemon.is_running())
        mock_kill.assert_called_once_with(12345, 0)
    
    @patch('os.kill')
    def test_is_running_process_not_exists(self, mock_kill):
        """Test is_running when process doesn't exist."""
        Path(self.pid_file).write_text("12345")
        mock_kill.side_effect = OSError("No such process")
        
        self.assertFalse(self.daemon.is_running())
    
    @patch('os.kill')
    def test_stop_daemon_success(self, mock_kill):
        """Test successful daemon stop."""
        Path(self.pid_file).write_text("12345")
        mock_kill.return_value = None
        
        result = self.daemon.stop_daemon()
        
        self.assertTrue(result)
        mock_kill.assert_called_once_with(12345, 15)  # SIGTERM
    
    @patch('os.kill')
    def test_stop_daemon_no_pid(self, mock_kill):
        """Test stop daemon when no PID file exists."""
        result = self.daemon.stop_daemon()
        
        self.assertFalse(result)
        mock_kill.assert_not_called()
    
    @patch('os.kill')
    def test_stop_daemon_process_not_found(self, mock_kill):
        """Test stop daemon when process doesn't exist."""
        Path(self.pid_file).write_text("12345")
        mock_kill.side_effect = OSError("No such process")
        
        result = self.daemon.stop_daemon()
        
        self.assertFalse(result)
    
    def test_cleanup(self):
        """Test PID file cleanup."""
        Path(self.pid_file).write_text("12345")
        self.assertTrue(Path(self.pid_file).exists())
        
        self.daemon.cleanup()
        
        self.assertFalse(Path(self.pid_file).exists())
    
    @patch('signal.signal')
    def test_setup_signal_handlers(self, mock_signal):
        """Test signal handler setup."""
        self.daemon.setup_signal_handlers()
        
        # Should set up handlers for SIGTERM and SIGINT
        self.assertEqual(mock_signal.call_count, 2)


if __name__ == '__main__':
    unittest.main()
