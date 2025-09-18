#!/usr/bin/env python3
"""Unit tests for connection management."""

import asyncio
import os
import sys
import unittest
from unittest.mock import patch, AsyncMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from websearch.connection_manager import ConnectionManager, managed_connection


class TestConnectionManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ConnectionManager(max_connections=3, connection_timeout=1)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Ensure cleanup
        asyncio.run(self.manager.stop())
    
    def test_register_connection_success(self):
        """Test successful connection registration."""
        result = self.manager.register_connection("conn1", {"client": "test"})
        
        self.assertTrue(result)
        self.assertEqual(self.manager.connection_count, 1)
        self.assertEqual(self.manager.total_connections, 1)
        self.assertIn("conn1", self.manager.active_connections)
    
    def test_register_connection_limit_exceeded(self):
        """Test connection registration when limit is exceeded."""
        # Fill up to limit
        for i in range(3):
            self.manager.register_connection(f"conn{i}")
        
        # Try to add one more
        result = self.manager.register_connection("conn3")
        
        self.assertFalse(result)
        self.assertEqual(self.manager.connection_count, 3)
    
    def test_update_connection_activity(self):
        """Test connection activity update."""
        self.manager.register_connection("conn1")
        initial_activity = self.manager.active_connections["conn1"]["last_activity"]
        initial_requests = self.manager.active_connections["conn1"]["requests_count"]
        
        # Small delay to ensure time difference
        import time
        time.sleep(0.01)
        
        self.manager.update_connection_activity("conn1")
        
        self.assertGreater(self.manager.active_connections["conn1"]["last_activity"], initial_activity)
        self.assertEqual(self.manager.active_connections["conn1"]["requests_count"], initial_requests + 1)
    
    def test_unregister_connection(self):
        """Test connection unregistration."""
        self.manager.register_connection("conn1")
        self.assertEqual(self.manager.connection_count, 1)
        
        self.manager.unregister_connection("conn1")
        
        self.assertEqual(self.manager.connection_count, 0)
        self.assertNotIn("conn1", self.manager.active_connections)
    
    def test_get_connection_stats(self):
        """Test connection statistics."""
        self.manager.register_connection("conn1")
        self.manager.register_connection("conn2")
        
        stats = self.manager.get_connection_stats()
        
        self.assertEqual(stats["active_connections"], 2)
        self.assertEqual(stats["total_connections"], 2)
        self.assertEqual(stats["max_connections"], 3)
        self.assertGreaterEqual(stats["avg_connection_duration"], 0)
    
    async def test_start_stop(self):
        """Test manager start and stop."""
        await self.manager.start()
        self.assertIsNotNone(self.manager.cleanup_task)
        
        await self.manager.stop()
        self.assertTrue(self.manager._shutdown_event.is_set())
    
    async def test_cleanup_stale_connections(self):
        """Test cleanup of stale connections."""
        # Register connection and make it stale
        self.manager.register_connection("conn1")
        
        # Manually set old timestamp to simulate stale connection
        import time
        self.manager.active_connections["conn1"]["last_activity"] = time.time() - 2  # 2 seconds ago
        
        await self.manager._cleanup_stale_connections()
        
        self.assertEqual(self.manager.connection_count, 0)
        self.assertNotIn("conn1", self.manager.active_connections)


class TestManagedConnection(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ConnectionManager(max_connections=2)
    
    def tearDown(self):
        """Clean up test fixtures."""
        asyncio.run(self.manager.stop())
    
    async def test_managed_connection_success(self):
        """Test successful managed connection context."""
        async with managed_connection("conn1", {"client": "test"}) as mgr:
            self.assertEqual(mgr.connection_count, 1)
            self.assertIn("conn1", mgr.active_connections)
        
        # Should be cleaned up after context
        self.assertEqual(self.manager.connection_count, 0)
    
    async def test_managed_connection_limit_exceeded(self):
        """Test managed connection when limit is exceeded."""
        # Fill up connections
        self.manager.register_connection("conn1")
        self.manager.register_connection("conn2")
        
        with self.assertRaises(ConnectionError):
            async with managed_connection("conn3"):
                pass


if __name__ == '__main__':
    # Run async tests
    class AsyncTestRunner:
        def run_async_tests(self):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run connection manager tests
                suite = unittest.TestLoader().loadTestsFromTestCase(TestConnectionManager)
                for test in suite:
                    if hasattr(test, '_testMethodName') and 'async' in test._testMethodName:
                        loop.run_until_complete(getattr(test, test._testMethodName)())
                
                # Run managed connection tests
                suite = unittest.TestLoader().loadTestsFromTestCase(TestManagedConnection)
                for test in suite:
                    if hasattr(test, '_testMethodName') and 'async' in test._testMethodName:
                        loop.run_until_complete(getattr(test, test._testMethodName)())
                        
            finally:
                loop.close()
    
    # Run regular tests
    unittest.main(verbosity=2, exit=False)
    
    # Run async tests
    AsyncTestRunner().run_async_tests()
