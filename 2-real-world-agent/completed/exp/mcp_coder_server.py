#!/usr/bin/env python3
"""
MCP Server for Coder Agent Tool
Exposes the coder agent functionality as an MCP tool
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server
from mcp.types import Tool, TextContent
from tools.coder_agent_tool import handle_coder_agent_tool

# Initialize MCP server
app = Server("coder-agent")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="coder_agent_tool",
            description="Execute Python code and bash commands using a specialized coder agent. This tool provides access to a coder agent that can execute Python code for data analysis and calculations, run bash commands for system operations, and handle complex programming tasks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The coding task or question that needs to be executed by the coder agent."
                    }
                },
                "required": ["task"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute tool"""
    if name != "coder_agent_tool":
        raise ValueError(f"Unknown tool: {name}")
    
    task = arguments.get("task")
    if not task:
        raise ValueError("Missing required argument: task")
    
    # Execute coder agent tool
    result = handle_coder_agent_tool(task)
    
    return [TextContent(type="text", text=result)]

async def main():
    """Run MCP server"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
