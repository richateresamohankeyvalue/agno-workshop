#!/usr/bin/env python3
"""Checkpoint 4: the standup pipeline, now with a durable human approval gate.

Same fixed step order as checkpoint 3, plus two more steps: draft a Slack
post, then pause for a real human decision before the one call that can't
be undone (`confirm_action`). The pause is backed by the same PostgreSQL
database checkpoint-2's memory uses — resuming is a separate process
invocation (see resume_standup.py), not something held in memory here.

Usage:
    uv run python standup_with_approval.py
"""

from __future__ import annotations

import asyncio
import uuid

from agno.db.postgres import PostgresDb

from daily_dev_assistant.config import load_settings
from daily_dev_assistant.pipeline import build_mcp_tools_with_approval, build_standup_pipeline_with_approval


async def main() -> None:
    settings = load_settings()
    db = PostgresDb(db_url=settings.db_url)

    mcp_tools = build_mcp_tools_with_approval(settings)
    await mcp_tools.connect()
    if not mcp_tools.functions:
        raise SystemExit(f"Could not reach MCP server at {settings.mcp_server_url} — is it running?")

    try:
        pipeline = build_standup_pipeline_with_approval(settings, mcp_tools, db)
        session_id = str(uuid.uuid4())
        result = await pipeline.arun(input="Prep and post today's standup update.", session_id=session_id)

        if result.is_paused:
            print("\n--- Paused for approval ---\n")
            for requirement in result.active_step_requirements:
                print(f"Step: {requirement.step_name}")
                print(f"Decision needed: {requirement.confirmation_message}")
            print(f"\nrun_id:     {result.run_id}")
            print(f"session_id: {result.session_id}")
            print(
                "\nResume with:\n"
                f"  uv run python resume_standup.py --run-id {result.run_id} "
                f"--session-id {result.session_id} --decision approve\n"
                f"  uv run python resume_standup.py --run-id {result.run_id} "
                f"--session-id {result.session_id} --decision deny"
            )
        else:
            print("\n--- Standup update ---\n")
            print(result.content)
    finally:
        await mcp_tools.close()


if __name__ == "__main__":
    asyncio.run(main())
