#!/usr/bin/env python3
"""Terminal chat for the checkpoint-2 agent (with memory).

Demonstrates two scopes of memory:
  - Short-term: conversation history within a session
  - Long-term: user-scoped facts that persist across sessions

Usage:
    uv run python main.py                       # new session, default user
    uv run python main.py --user alice          # new session, user "alice"
    uv run python main.py --user alice --session my-session  # resume a session
"""

from __future__ import annotations

import asyncio
import argparse
import uuid

from daily_dev_assistant.agent import build_agent, build_mcp_tools
from daily_dev_assistant.config import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Checkpoint-2: agent with memory")
    parser.add_argument("--user", default="dev", help="User identity (default: dev)")
    parser.add_argument("--session", default=None, help="Session id (default: new random session)")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    settings = load_settings()

    user_id = args.user
    session_id = args.session or str(uuid.uuid4())

    mcp_tools = build_mcp_tools(settings)
    try:
        await mcp_tools.connect()
    except Exception:
        pass

    if mcp_tools.functions:
        print(f"Connected. Tools: {sorted(mcp_tools.functions)}")
    else:
        print(f"WARNING: MCP server at {settings.mcp_server_url} not reachable — running without tools.")
        mcp_tools = None

    print(f"User: {user_id} | Session: {session_id}\n")

    try:
        agent = build_agent(settings, mcp_tools, user_id=user_id, session_id=session_id)

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
        if mcp_tools:
            await mcp_tools.close()


if __name__ == "__main__":
    asyncio.run(main())
