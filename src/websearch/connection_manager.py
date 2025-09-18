#!/usr/bin/env python3
"""Connection management for WebSearch MCP daemon."""

import asyncio
import logging
import time
from typing import Dict, Set, Optional
from contextlib import asynccontextmanager
import weakref

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages HTTP connections for the MCP daemon."""
    
    def __init__(self, max_connections: int = 100, connection_timeout: int = 300):
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.active_connections: Dict[str, dict] = {}
        self.connection_count = 0
        self.total_connections = 0
        self.cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start the connection manager."""
        logger.info("Starting connection manager")
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
    async def stop(self):
        """Stop the connection manager and cleanup all connections."""
        logger.info("Stopping connection manager")
        self._shutdown_event.set()
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all active connections
        await self._cleanup_all_connections()
        logger.info(f"Connection manager stopped. Total connections served: {self.total_connections}")
    
    def register_connection(self, connection_id: str, client_info: dict = None) -> bool:
        """Register a new connection."""
        if self.connection_count >= self.max_connections:
            logger.warning(f"Connection limit reached ({self.max_connections}), rejecting connection {connection_id}")
            return False
        
        self.active_connections[connection_id] = {
            'created_at': time.time(),
            'last_activity': time.time(),
            'client_info': client_info or {},
            'requests_count': 0
        }
        self.connection_count += 1
        self.total_connections += 1
        
        logger.info(f"Connection {connection_id} registered. Active: {self.connection_count}/{self.max_connections}")
        return True
    
    def update_connection_activity(self, connection_id: str):
        """Update last activity time for a connection."""
        if connection_id in self.active_connections:
            self.active_connections[connection_id]['last_activity'] = time.time()
            self.active_connections[connection_id]['requests_count'] += 1
    
    def unregister_connection(self, connection_id: str):
        """Unregister a connection."""
        if connection_id in self.active_connections:
            conn_info = self.active_connections.pop(connection_id)
            self.connection_count -= 1
            duration = time.time() - conn_info['created_at']
            logger.info(f"Connection {connection_id} unregistered. Duration: {duration:.1f}s, Requests: {conn_info['requests_count']}")
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics."""
        now = time.time()
        active_durations = [now - conn['created_at'] for conn in self.active_connections.values()]
        
        return {
            'active_connections': self.connection_count,
            'total_connections': self.total_connections,
            'max_connections': self.max_connections,
            'avg_connection_duration': sum(active_durations) / len(active_durations) if active_durations else 0,
            'oldest_connection_age': max(active_durations) if active_durations else 0
        }
    
    async def _cleanup_loop(self):
        """Periodic cleanup of stale connections."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=60)  # Check every minute
                break
            except asyncio.TimeoutError:
                await self._cleanup_stale_connections()
    
    async def _cleanup_stale_connections(self):
        """Remove connections that have been inactive for too long."""
        now = time.time()
        stale_connections = []
        
        for conn_id, conn_info in self.active_connections.items():
            if now - conn_info['last_activity'] > self.connection_timeout:
                stale_connections.append(conn_id)
        
        for conn_id in stale_connections:
            logger.info(f"Cleaning up stale connection {conn_id}")
            self.unregister_connection(conn_id)
    
    async def _cleanup_all_connections(self):
        """Force cleanup of all connections."""
        connection_ids = list(self.active_connections.keys())
        for conn_id in connection_ids:
            self.unregister_connection(conn_id)

# Global connection manager instance
connection_manager = ConnectionManager()

@asynccontextmanager
async def managed_connection(connection_id: str, client_info: dict = None):
    """Context manager for handling connections."""
    if not connection_manager.register_connection(connection_id, client_info):
        raise ConnectionError("Connection limit exceeded")
    
    try:
        yield connection_manager
    finally:
        connection_manager.unregister_connection(connection_id)
