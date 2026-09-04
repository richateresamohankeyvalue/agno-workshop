#!/usr/bin/env python3
"""Checkpoint 6: Agno eval suite (development / CI style).

Uses Agno's Case + acli — the same evaluation surface documented at:
  https://docs.agno.com/features/evaluation

Two check types in one suite:
  - Agent-as-judge (`criteria=...`) — quality of the reply
  - Reliability (`expected_tool_calls=...`) — did it call the right tool?

Requires: Postgres up, MCP server at MCP_SERVER_URL, LiteLLM credentials in .env.

Usage:
    uv run python evals.py
    uv run python evals.py --list
    uv run python evals.py --name calendar_uses_tool
    uv run python evals.py --json-output /tmp/evals.json
"""

from __future__ import annotations

import asyncio
import sys

from agno.eval.suite import Case, JudgeMode, acli
from agno.models.litellm import LiteLLM

from daily_dev_assistant.agent import build_agent, build_mcp_tools
from daily_dev_assistant.config import load_settings


async def main(argv: list[str] | None = None) -> int:
    settings = load_settings()
    mcp_tools = build_mcp_tools(settings)
    await mcp_tools.connect()
    if not mcp_tools.functions:
        print(f"Could not reach MCP server at {settings.mcp_server_url} — is it running?", file=sys.stderr)
        return 2

    try:
        agent = build_agent(
            settings,
            mcp_tools,
            user_id="eval-user",
            session_id="eval-session",
        )

        judge_model = LiteLLM(
            id=settings.grader_model_id,
            api_key=settings.litellm_api_key,
            api_base=settings.litellm_base_url,
            temperature=None,
            top_p=None,
        )

        cases = (
            Case(
                name="greeting_quality",
                agent=agent,
                input="hi",
                tags=("judge",),
                criteria=(
                    "Reply is a brief, friendly greeting as a developer assistant. "
                    "It does not invent calendar events, tickets, or PRs."
                ),
                judge_model=judge_model,
                judge_mode=JudgeMode.NUMERIC,
                judge_threshold=7,
            ),
            Case(
                name="calendar_uses_tool",
                agent=agent,
                input="What's on my calendar today?",
                tags=("reliability", "judge"),
                expected_tool_calls=("get_calendar_events",),
                allow_additional_tool_calls=True,
                criteria=(
                    "Reply describes calendar events using information that could only "
                    "come from a tool call; it does not invent meetings."
                ),
                judge_model=judge_model,
                judge_mode=JudgeMode.NUMERIC,
                judge_threshold=7,
            ),
        )

        return await acli(cases, judge_model=judge_model, argv=argv)
    finally:
        await mcp_tools.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
