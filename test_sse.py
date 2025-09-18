#!/usr/bin/env python3
"""Test FastMCP SSE transport capabilities"""

import asyncio
from fastmcp import FastMCP

# Create minimal test server
mcp = FastMCP("TestSSE")

@mcp.tool(name="test_tool", description="Test tool for SSE transport")
def test_tool(message: str) -> str:
    return f"Echo: {message}"

async def test_sse():
    """Test SSE transport"""
    print("Testing SSE transport...")
    try:
        # Check if run_sse_async exists and what it does
        if hasattr(mcp, 'run_sse_async'):
            print("run_sse_async method found")
            # Don't actually run it, just check signature
            import inspect
            sig = inspect.signature(mcp.run_sse_async)
            print(f"Signature: {sig}")
        else:
            print("run_sse_async method not found")
            
        # Check regular run method with sse
        print("Testing run method with sse transport...")
        import inspect
        sig = inspect.signature(mcp.run)
        print(f"run method signature: {sig}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_sse())
