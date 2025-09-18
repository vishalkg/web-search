#!/usr/bin/env python3
"""Test multiple clients connecting to HTTP daemon."""

import asyncio
import time
from fastmcp import Client

async def test_client(client_id: int, num_requests: int = 2):
    """Test a single client making multiple requests."""
    print(f"Client {client_id}: Starting")
    
    try:
        async with Client("http://127.0.0.1:8090/mcp") as client:
            print(f"Client {client_id}: Connected")
            
            # Test list tools
            tools = await client.list_tools()
            print(f"Client {client_id}: Found {len(tools)} tools")
            
            # Test search requests
            for i in range(num_requests):
                result = await client.call_tool("search_web", {
                    "search_query": f"test query {client_id}-{i}",
                    "num_results": 1
                })
                print(f"Client {client_id}: Request {i+1} completed")
                await asyncio.sleep(0.2)
                
    except Exception as e:
        print(f"Client {client_id}: Error - {e}")
    
    print(f"Client {client_id}: Finished")

async def test_multi_client():
    """Test multiple concurrent clients."""
    print("Starting multi-client test...")
    
    # Start 3 clients concurrently
    tasks = [
        test_client(1, 1),
        test_client(2, 1), 
        test_client(3, 1)
    ]
    
    start_time = time.time()
    await asyncio.gather(*tasks)
    end_time = time.time()
    
    print(f"Multi-client test completed in {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(test_multi_client())
