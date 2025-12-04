#!/usr/bin/env python3
"""MCP Server using existing TOOL_SPEC definitions"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server
from mcp.types import Tool, TextContent

# Import existing TOOL_SPECs and handlers
from tools.coder_agent_tool import TOOL_SPEC as CODER_SPEC, handle_coder_agent_tool
from tools.validator_agent_tool import TOOL_SPEC as VALIDATOR_SPEC, handle_validator_agent_tool
from tools.reporter_agent_tool import TOOL_SPEC as REPORTER_SPEC, handle_reporter_agent_tool
from tools.tracker_agent_tool import TOOL_SPEC as TRACKER_SPEC, handle_tracker_agent_tool

app = Server("bedrock-agents")

# Map tool names to handlers
TOOL_HANDLERS = {
    "coder_agent_tool": handle_coder_agent_tool,
    "validator_agent_tool": handle_validator_agent_tool,
    "reporter_agent_tool": handle_reporter_agent_tool,
    "tracker_agent_tool": handle_tracker_agent_tool
}

# Convert TOOL_SPECs to MCP Tools
TOOLS = [
    Tool(
        name=CODER_SPEC["name"],
        description=CODER_SPEC["description"],
        inputSchema=CODER_SPEC["inputSchema"]["json"]
    ),
    Tool(
        name=VALIDATOR_SPEC["name"],
        description=VALIDATOR_SPEC["description"],
        inputSchema=VALIDATOR_SPEC["inputSchema"]["json"]
    ),
    Tool(
        name=REPORTER_SPEC["name"],
        description=REPORTER_SPEC["description"],
        inputSchema=REPORTER_SPEC["inputSchema"]["json"]
    ),
    Tool(
        name=TRACKER_SPEC["name"],
        description=TRACKER_SPEC["description"],
        inputSchema=TRACKER_SPEC["inputSchema"]["json"]
    )
]

@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    
    # Call handler with appropriate arguments
    if name == "tracker_agent_tool":
        result = handler(arguments["completed_agent"], arguments["completion_summary"])
    else:
        result = handler(arguments["task"])
    
    return [TextContent(type="text", text=result)]

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
