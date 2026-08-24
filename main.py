#!/usr/bin/env python3
"""Terminal chat for the checkpoint-1 agent.

Connects to the MCP server, builds the agent, then sends whatever you type to
it and prints the reply plus which tool(s) it called along the way.

Usage:
    uv run python main.py
"""

from __future__ import annotations

import asyncio

from daily_dev_assistant.agent import build_agent, build_mcp_tools
from daily_dev_assistant.config import load_settings


async def main() -> None:
    settings = load_settings()

    mcp_tools = build_mcp_tools(settings)
    await mcp_tools.connect()
    if not mcp_tools.functions:
        raise SystemExit(f"Could not reach MCP server at {settings.mcp_server_url} — is it running?")

    try:
        print(f"Connected. Tools available to the agent: {sorted(mcp_tools.functions)}\n")
        agent = build_agent(settings, mcp_tools)

        print('Type a message, or "exit" to quit.\n')
        while True:
            message = input("> ").strip()
            if not message or message.lower() in ("exit", "quit"):
                break

            response = await agent.arun(message)

            print(f"\nAssistant: {response.content}")
            for tool in response.tools or []:
                print(f"  [tool call] {tool.tool_name}({tool.tool_args})")
            print()
    finally:
        await mcp_tools.close()


if __name__ == "__main__":
    asyncio.run(main())
