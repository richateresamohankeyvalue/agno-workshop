#!/usr/bin/env python3
"""Checkpoint 6: evaluation, cost, and model portability.

Same agent + reviewer as checkpoint-5, plus:
  - Token usage printed after every turn (input, output, total)
  - An automated grader scoring each reply on grounding, completeness, conciseness
  - Model swappable via AGENT_MODEL_ID in .env — same script, different model

Usage:
    uv run python assistant.py --user alice
    AGENT_MODEL_ID=gpt-4o uv run python assistant.py --user alice   # swap model
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
from daily_dev_assistant.grader import build_grader, grade_reply
from daily_dev_assistant.pipeline import build_mcp_tools_with_approval

STANDUP_TOOL_INSTRUCTIONS = BASE_INSTRUCTIONS + """

You also have start_standup_pipeline and resume_standup_pipeline tools. Use
start_standup_pipeline when asked to prep or post a standup update. It will
pause for human approval before anything is actually posted — relay that
pause to the user honestly, and only call resume_standup_pipeline once they
have actually told you their decision."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Checkpoint-6: eval, cost, model portability")
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
        grader = build_grader(settings)

        print(f"Model: {settings.model_id}")
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

            # Token usage — straight off the response, zero extra setup
            m = turn.metrics
            print(f"\n  Tokens: {m.input_tokens} in / {m.output_tokens} out / {m.total_tokens} total")

            # Review (checkpoint-5's grounding check)
            print(f"  Review: {turn.review_verdict}")

            # Grade (checkpoint-6's quality rubric)
            grade = await grade_reply(grader, user_message=message, reply=turn.reply, tool_trace=turn.tool_trace)
            print(f"  Grade:\n    {grade.raw_verdict.replace(chr(10), chr(10) + '    ')}")
            print()
    finally:
        await agent_mcp_tools.close()
        await pipeline_mcp_tools.close()


if __name__ == "__main__":
    asyncio.run(main())
