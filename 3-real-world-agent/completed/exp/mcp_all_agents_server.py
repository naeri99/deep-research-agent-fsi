#!/usr/bin/env python3
"""
MCP Server for All Agent Tools
Exposes Coder, Validator, Reporter, and Tracker as MCP tools
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server
from mcp.types import Tool, TextContent
from tools.coder_agent_tool import handle_coder_agent_tool
from tools.validator_agent_tool import handle_validator_agent_tool
from tools.reporter_agent_tool import handle_reporter_agent_tool
from tools.tracker_agent_tool import handle_tracker_agent_tool

app = Server("bedrock-agents")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available agent tools"""
    return [
        Tool(
            name="coder_agent",
            description="Execute Python code and bash commands for data analysis, calculations, and system operations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The coding task to execute"
                    }
                },
                "required": ["task"]
            }
        ),
        Tool(
            name="validator_agent",
            description="Validate numerical calculations and generate citation metadata for reports.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The validation task"
                    }
                },
                "required": ["task"]
            }
        ),
        Tool(
            name="reporter_agent",
            description="Generate comprehensive reports in docx format based on analysis results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The reporting task"
                    }
                },
                "required": ["task"]
            }
        ),
        Tool(
            name="tracker_agent",
            description="Track and update task completion status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "completed_agent": {
                        "type": "string",
                        "description": "Name of the agent that completed"
                    },
                    "completion_summary": {
                        "type": "string",
                        "description": "Summary of what was completed"
                    }
                },
                "required": ["completed_agent", "completion_summary"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute requested tool"""
    
    if name == "coder_agent":
        result = handle_coder_agent_tool(arguments["task"])
    elif name == "validator_agent":
        result = handle_validator_agent_tool(arguments["task"])
    elif name == "reporter_agent":
        result = handle_reporter_agent_tool(arguments["task"])
    elif name == "tracker_agent":
        result = handle_tracker_agent_tool(
            arguments["completed_agent"],
            arguments["completion_summary"]
        )
    else:
        raise ValueError(f"Unknown tool: {name}")
    
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
