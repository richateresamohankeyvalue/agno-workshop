#!/usr/bin/env python3
"""Checkpoint 5: the memory agent, with the standup pipeline as a tool, and a
mandatory review step between every draft reply and the user.

Every turn goes: agent responds -> review step checks the reply against its
own tool-call trace -> reply printed, review verdict printed alongside it.
The review step is a plain function call in run_turn() below — comment it
out and the review result just silently stops appearing. That's the actual
regression this project hit once: nothing crashes, the system just quietly
stops checking its own work.

Usage:
    uv run python assistant.py                       # new session, default user
    uv run python assistant.py --user alice
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from agno.db.postgres import PostgresDb

from daily_dev_assistant.agent import INSTRUCTIONS as BASE_INSTRUCTIONS
from daily_dev_assistant.agent import build_agent, build_mcp_tools
from daily_dev_assistant.agent_pipeline import build_reviewer, build_standup_tools, run_turn
from daily_dev_assistant.config import load_settings
from daily_dev_assistant.pipeline import build_mcp_tools_with_approval

STANDUP_TOOL_INSTRUCTIONS = BASE_INSTRUCTIONS + """

You also have start_standup_pipeline and resume_standup_pipeline tools. Use
start_standup_pipeline when asked to prep or post a standup update. It will
pause for human approval before anything is actually posted — relay that
pause to the user honestly, and only call resume_standup_pipeline once they
have actually told you their decision."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Checkpoint-5: agent + pipeline-as-tool + mandatory review")
    parser.add_argument("--user", default="dev", help="User identity (default: dev)")
    parser.add_argument("--session", default=None, help="Session id (default: new random session)")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    settings = load_settings()
    db = PostgresDb(db_url=settings.db_url)

    user_id = args.user
    session_id = args.session or str(uuid.uuid4())

    agent_mcp_tools = build_mcp_tools(settings)
    pipeline_mcp_tools = build_mcp_tools_with_approval(settings)
    await agent_mcp_tools.connect()
    await pipeline_mcp_tools.connect()
    if not agent_mcp_tools.functions or not pipeline_mcp_tools.functions:
        raise SystemExit(f"Could not reach MCP server at {settings.mcp_server_url} — is it running?")

    try:
        start_standup, resume_standup = build_standup_tools(settings, pipeline_mcp_tools, db)
        agent = build_agent(
            settings,
            agent_mcp_tools,
            user_id=user_id,
            session_id=session_id,
            instructions=STANDUP_TOOL_INSTRUCTIONS,
            extra_tools=[start_standup, resume_standup],
        )
        reviewer = build_reviewer(settings)

        print(f"Connected. Agent tools: {sorted(agent_mcp_tools.functions)} + start/resume_standup_pipeline")
        print(f"User: {user_id} | Session: {session_id}\n")
        print('Type a message, or "exit" to quit.\n')

        while True:
            message = input("> ").strip()
            if not message or message.lower() in ("exit", "quit"):
                break

            turn = await run_turn(agent, reviewer, message)

            print(f"\nAssistant: {turn.reply}")
            for call in turn.tool_trace:
                print(f"  [tool call] {call['tool_name']}({call['tool_args']})")
            print(f"\nReview: {turn.review_verdict}\n")
    finally:
        await agent_mcp_tools.close()
        await pipeline_mcp_tools.close()


if __name__ == "__main__":
    asyncio.run(main())
