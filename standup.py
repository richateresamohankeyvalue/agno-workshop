#!/usr/bin/env python3
"""Checkpoint 3: run the standup pipeline directly — no agent involved.

The pipeline decides the step order (fetch profile -> fetch tickets ->
fetch calendar -> synthesize), not a model. Run it and watch each step
fire in that fixed sequence.

Usage:
    uv run python standup.py
"""

from __future__ import annotations

import asyncio

from daily_dev_assistant.config import load_settings
from daily_dev_assistant.pipeline import build_mcp_tools, build_standup_pipeline


async def main() -> None:
    settings = load_settings()

    mcp_tools = build_mcp_tools(settings)
    await mcp_tools.connect()
    if not mcp_tools.functions:
        raise SystemExit(f"Could not reach MCP server at {settings.mcp_server_url} — is it running?")

    try:
        pipeline = build_standup_pipeline(settings, mcp_tools)
        result = await pipeline.arun(input="Prep today's standup update.")

        print("\n--- Standup update ---\n")
        print(result.content)
    finally:
        await mcp_tools.close()


if __name__ == "__main__":
    asyncio.run(main())
