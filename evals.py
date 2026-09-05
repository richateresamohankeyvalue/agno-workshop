#!/usr/bin/env python3
"""Checkpoint 6: Agno eval suite — all four evaluation types.

Covers every Agno eval surface documented at:
  https://docs.agno.com/features/evaluation

  1. Agent-as-judge  (Case with `criteria`)       — quality of the reply
  2. Reliability     (Case with `expected_tool_calls`) — did the right tool fire?
  3. Accuracy        (AccuracyEval)                — response vs a gold-standard answer
  4. Performance     (PerformanceEval)             — latency and memory

Requires: Postgres up, MCP server at MCP_SERVER_URL, LiteLLM credentials in .env.

Usage:
    uv run python evals.py                            # Case suite (judge + reliability)
    uv run python evals.py --list                     # list cases without running
    uv run python evals.py --name pr_uses_tool        # run one case
    uv run python evals.py --tag smoke                # run tagged subset
    uv run python evals.py --json-output /tmp/evals.json
    uv run python evals.py --accuracy                 # AccuracyEval standalone
    uv run python evals.py --perf                     # PerformanceEval standalone
"""

from __future__ import annotations

import asyncio
import sys

from agno.eval.accuracy import AccuracyEval
from agno.eval.performance import PerformanceEval
from agno.eval.suite import Case, JudgeMode, acli
from agno.models.litellm import LiteLLM

from daily_dev_assistant.agent import build_agent, build_mcp_tools
from daily_dev_assistant.config import load_settings


def _build_judge_model(settings):
    """Shared judge model — uses the grader (typically a smaller/cheaper model)."""
    return LiteLLM(
        id=settings.grader_model_id,
        api_key=settings.litellm_api_key,
        api_base=settings.litellm_base_url,
        temperature=None,
        top_p=None,
    )


# ── 1 & 2: Case suite (agent-as-judge + reliability) ─────────────────────


async def run_suite(argv: list[str] | None = None) -> int:
    settings = load_settings()
    mcp_tools = build_mcp_tools(settings)
    await mcp_tools.connect()
    if not mcp_tools.functions:
        print(f"Could not reach MCP server at {settings.mcp_server_url} — is it running?", file=sys.stderr)
        return 2

    try:
        agent = build_agent(
            settings, mcp_tools,
            user_id="eval-user", session_id="eval-session",
        )
        judge_model = _build_judge_model(settings)

        cases = (
            # ── Judge-only ────────────────────────────────────────────
            Case(
                name="greeting_quality",
                agent=agent,
                input="hi",
                tags=("judge", "smoke"),
                criteria=(
                    "Reply is a brief, friendly greeting as a developer assistant. "
                    "It does not invent calendar events, tickets, or PRs."
                ),
                judge_model=judge_model,
                judge_mode=JudgeMode.NUMERIC,
                judge_threshold=7,
            ),
            Case(
                name="no_hallucination_on_unknown",
                agent=agent,
                input="What's the status of the Kubernetes migration?",
                tags=("judge", "smoke"),
                criteria=(
                    "The assistant does NOT invent details about a Kubernetes "
                    "migration. It either says it doesn't have that information, "
                    "asks for clarification, or checks its tools and reports "
                    "nothing relevant found. Any fabricated specifics = fail."
                ),
                judge_model=judge_model,
                judge_mode=JudgeMode.BINARY,
            ),

            # ── Reliability + judge ───────────────────────────────────
            Case(
                name="calendar_uses_tool",
                agent=agent,
                input="What's on my calendar today?",
                tags=("reliability", "judge", "smoke"),
                expected_tool_calls=("get_calendar_events",),
                allow_additional_tool_calls=True,
                criteria=(
                    "Reply describes calendar events using information that could "
                    "only come from a tool call; it does not invent meetings."
                ),
                judge_model=judge_model,
                judge_mode=JudgeMode.NUMERIC,
                judge_threshold=7,
            ),
            Case(
                name="pr_uses_tool",
                agent=agent,
                input="Show me my open pull requests.",
                tags=("reliability", "judge"),
                expected_tool_calls=("get_github_prs",),
                allow_additional_tool_calls=True,
                criteria=(
                    "Reply lists pull requests with details (title, repo, or "
                    "status) sourced from the tool call. No fabricated PR data."
                ),
                judge_model=judge_model,
                judge_mode=JudgeMode.NUMERIC,
                judge_threshold=7,
            ),
            Case(
                name="combined_daily_brief",
                agent=agent,
                input="Give me a quick daily brief — calendar and PRs.",
                tags=("reliability", "judge"),
                expected_tool_calls=("get_calendar_events", "get_github_prs"),
                allow_additional_tool_calls=True,
                criteria=(
                    "Reply covers both calendar events and pull requests using "
                    "data from tool calls. No invented items."
                ),
                judge_model=judge_model,
                judge_mode=JudgeMode.NUMERIC,
                judge_threshold=7,
            ),
        )

        return await acli(cases, judge_model=judge_model, argv=argv)
    finally:
        await mcp_tools.close()


# ── 3: Accuracy eval (response vs expected answer) ───────────────────────


async def run_accuracy() -> int:
    """AccuracyEval: does the agent correctly describe its own capabilities?"""
    settings = load_settings()
    mcp_tools = build_mcp_tools(settings)
    await mcp_tools.connect()
    if not mcp_tools.functions:
        print(f"Could not reach MCP server at {settings.mcp_server_url}", file=sys.stderr)
        return 2

    try:
        agent = build_agent(
            settings, mcp_tools,
            user_id="eval-user", session_id="eval-accuracy",
        )
        judge_model = _build_judge_model(settings)

        evaluation = AccuracyEval(
            name="capabilities_accuracy",
            model=judge_model,
            agent=agent,
            input="What can you help me with? Answer in one sentence.",
            expected_output=(
                "I can check your calendar events and show your GitHub pull requests."
            ),
            additional_guidelines=(
                "The response must mention both calendar events and GitHub pull "
                "requests as available capabilities. Exact wording is not required."
            ),
            num_iterations=1,
        )

        print("─── Accuracy Eval: capabilities_accuracy ───\n")
        result = await evaluation.arun(print_results=True)

        if result is None or result.avg_score < 7:
            print(f"\n✗ FAIL  avg_score={getattr(result, 'avg_score', None)}")
            return 1
        print(f"\n✓ PASS  avg_score={result.avg_score}")
        return 0
    finally:
        await mcp_tools.close()


# ── 4: Performance eval (latency + memory) ───────────────────────────────


async def run_perf() -> int:
    """PerformanceEval: how fast does the agent respond to a calendar query?"""
    settings = load_settings()
    mcp_tools = build_mcp_tools(settings)
    await mcp_tools.connect()
    if not mcp_tools.functions:
        print(f"Could not reach MCP server at {settings.mcp_server_url}", file=sys.stderr)
        return 2

    try:
        agent = build_agent(
            settings, mcp_tools,
            user_id="eval-user", session_id="eval-perf",
        )

        async def agent_calendar_query():
            return await agent.arun("What's on my calendar today?")

        perf_eval = PerformanceEval(
            name="calendar_query_latency",
            func=agent_calendar_query,
            num_iterations=3,
            warmup_runs=1,
        )

        print("─── Performance Eval: calendar_query_latency ───\n")
        await perf_eval.arun(print_results=True, print_summary=True)
        return 0
    finally:
        await mcp_tools.close()


# ── Dispatch ──────────────────────────────────────────────────────────────


async def main() -> int:
    if "--accuracy" in sys.argv:
        return await run_accuracy()
    if "--perf" in sys.argv:
        return await run_perf()
    return await run_suite()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
