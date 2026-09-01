#!/usr/bin/env python3
"""Checkpoint 4: resume a paused standup-with-approval run.

A separate process from standup_with_approval.py on purpose — the run is
loaded from PostgreSQL by (run_id, session_id), not carried over in memory.
Kill the terminal that paused it, then run this in a brand-new one; it
still works.

Usage:
    uv run python resume_standup.py --run-id <id> --session-id <id> --decision approve
    uv run python resume_standup.py --run-id <id> --session-id <id> --decision deny
"""

from __future__ import annotations

import argparse
import asyncio

from agno.db.postgres import PostgresDb

from daily_dev_assistant.config import load_settings
from daily_dev_assistant.pipeline import build_mcp_tools_with_approval, build_standup_pipeline_with_approval


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume a paused checkpoint-4 standup run")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--decision", choices=["approve", "deny"], required=True)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    settings = load_settings()
    db = PostgresDb(db_url=settings.db_url)

    mcp_tools = build_mcp_tools_with_approval(settings)
    await mcp_tools.connect()
    if not mcp_tools.functions:
        raise SystemExit(f"Could not reach MCP server at {settings.mcp_server_url} — is it running?")

    try:
        pipeline = build_standup_pipeline_with_approval(settings, mcp_tools, db)

        run_output = await pipeline.aget_run_output(run_id=args.run_id, session_id=args.session_id)
        if run_output is None:
            raise SystemExit(f"No paused run found for run_id={args.run_id} session_id={args.session_id}")
        if not run_output.is_paused:
            raise SystemExit("This run isn't paused — nothing to resume.")

        for requirement in run_output.active_step_requirements:
            if args.decision == "approve":
                requirement.confirm()
            else:
                requirement.reject()

        result = await pipeline.acontinue_run(run_output)

        if result.is_paused:
            print("\n--- Still paused ---\n")
            for requirement in result.active_step_requirements:
                print(f"Step: {requirement.step_name} — {requirement.confirmation_message}")
        elif args.decision == "deny":
            print("\n--- Denied: nothing was posted ---\n")
            print(result.content)
        else:
            print("\n--- Standup posted ---\n")
            print(result.content)
    finally:
        await mcp_tools.close()


if __name__ == "__main__":
    asyncio.run(main())
