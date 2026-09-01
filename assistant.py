#!/usr/bin/env python3
"""Checkpoint 7: the full assistant.

Everything from checkpoints 1-6, in one place. A single agent handling three
request shapes — inferring which kind it's looking at from the message alone:

  1. Quick lookups       → 1-2 tool calls (calendar, PRs)
  2. Standup prep        → fixed pipeline, pauses for approval
  3. Sprint planning     → fixed pipeline, ranked priorities back

No external "mode" input anywhere. The agent decides.

Usage:
    uv run python assistant.py --user alice
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from agno.db.postgres import PostgresDb

from daily_dev_assistant.agent import build_agent, build_mcp_tools
from daily_dev_assistant.agent_pipeline import (
    build_reviewer,
    build_sprint_planning_tool,
    build_standup_tools,
    run_turn,
)
from daily_dev_assistant.config import load_settings
from daily_dev_assistant.grader import build_grader, grade_reply
from daily_dev_assistant.pipeline import build_mcp_tools_with_approval, build_sprint_mcp_tools

FULL_ASSISTANT_INSTRUCTIONS = """You are a developer's daily assistant. You handle three kinds
of requests — figure out which one from the message alone, never ask:

1. **Quick lookups** — calendar, PRs, tickets, or anything a single tool call answers.
   Just call the tool and relay what it says.

2. **Standup prep** — use start_standup_pipeline. It gathers data and drafts a Slack post,
   then pauses for the user's approval. Relay the pause honestly ("here's the draft, shall
   I post it?"). Only call resume_standup_pipeline once they actually say yes or no.

3. **Sprint planning** — use prep_sprint_planning. It gathers tickets, PRs, calendar, and
   produces a structured brief with carry-overs, in-review items, and suggested priorities.

You also have memory. If the user tells you something worth remembering (their name,
username, preferences), retain it for future conversations.

Never state a fact you didn't get from a tool call. If a tool returns nothing, say so."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Checkpoint-7: the full assistant")
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
    sprint_mcp_tools = build_sprint_mcp_tools(settings)
    await agent_mcp_tools.connect()
    await pipeline_mcp_tools.connect()
    await sprint_mcp_tools.connect()

    if not agent_mcp_tools.functions or not pipeline_mcp_tools.functions or not sprint_mcp_tools.functions:
        raise SystemExit(f"Could not reach MCP server at {settings.mcp_server_url} — is it running?")

    try:
        start_standup, resume_standup = build_standup_tools(settings, pipeline_mcp_tools, db)
        prep_sprint = build_sprint_planning_tool(settings, sprint_mcp_tools)

        agent = build_agent(
            settings,
            agent_mcp_tools,
            user_id=user_id,
            session_id=session_id,
            instructions=FULL_ASSISTANT_INSTRUCTIONS,
            extra_tools=[start_standup, resume_standup, prep_sprint],
        )
        reviewer = build_reviewer(settings)
        grader = build_grader(settings)

        print(f"Model: {settings.model_id}")
        print(f"Tools: {sorted(agent_mcp_tools.functions)} + standup pipeline + sprint planning")
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

            m = turn.metrics
            print(f"\n  Tokens: {m.input_tokens} in / {m.output_tokens} out / {m.total_tokens} total")
            print(f"  Review: {turn.review_verdict}")

            grade = await grade_reply(grader, user_message=message, reply=turn.reply, tool_trace=turn.tool_trace)
            print(f"  Grade:\n    {grade.raw_verdict.replace(chr(10), chr(10) + '    ')}")
            print()
    finally:
        await agent_mcp_tools.close()
        await pipeline_mcp_tools.close()
        await sprint_mcp_tools.close()


if __name__ == "__main__":
    asyncio.run(main())
