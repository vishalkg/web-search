#!/usr/bin/env python3
"""Test daemon mode startup"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from websearch.server import main
import threading
import time
import requests

def test_daemon():
    """Test if daemon starts and responds"""
    print("Testing daemon startup...")
    
    # Start daemon in thread
    def run_daemon():
        sys.argv = ['test_daemon.py', '--daemon']
        try:
            main()
        except KeyboardInterrupt:
            pass
    
    daemon_thread = threading.Thread(target=run_daemon, daemon=True)
    daemon_thread.start()
    
    # Wait for startup
    time.sleep(3)
    
    # Test if server is responding
    try:
        response = requests.get('http://127.0.0.1:8080/sse', timeout=5)
        print(f"✅ Daemon responding: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Daemon not responding: {e}")
        return False

if __name__ == "__main__":
    test_daemon()
