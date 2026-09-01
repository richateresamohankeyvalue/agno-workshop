"""Checkpoint 5: pipeline-as-tool, and a review step the model can't skip.

Two things get composed here:

  1. Checkpoint-4's standup pipeline, wrapped as an ordinary start/resume tool
     pair on the checkpoint-2 memory agent. The agent never sees a paused
     `Workflow` — just two functions it can call like any other tool.

  2. An outer, code-enforced turn sequence: agent responds -> a review step
     checks the reply against the trace of tool calls that produced it ->
     final answer. The review step is a plain, unconditional function call
     to a second, smaller model — never something offered to the first model
     as a tool it could choose to skip.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from agno.agent import Agent
from agno.db.base import BaseDb
from agno.models.litellm import LiteLLM
from agno.tools.mcp import MCPTools

from daily_dev_assistant.config import Settings
from daily_dev_assistant.pipeline import build_standup_pipeline_with_approval

# --- The pipeline, wrapped as two tools ---


def build_standup_tools(settings: Settings, pipeline_mcp_tools: MCPTools, db: BaseDb):
    """Returns (start_standup_pipeline, resume_standup_pipeline), bound to this
    pipeline's MCP connection and db. Attach both to an Agent's `tools=[...]`."""

    async def start_standup_pipeline() -> Dict[str, Any]:
        """Start preparing and posting today's standup update. This pauses for
        human approval before the update is actually posted anywhere — it never
        completes the post on its own. Returns either a paused decision (with a
        run_id and session_id to pass to resume_standup_pipeline) or, if nothing
        needed approval, the completed result."""
        pipeline = build_standup_pipeline_with_approval(settings, pipeline_mcp_tools, db)
        session_id = str(uuid.uuid4())
        result = await pipeline.arun(input="Prep and post today's standup update.", session_id=session_id)

        if result.is_paused:
            requirement = result.active_step_requirements[0]
            return {
                "status": "paused",
                "run_id": result.run_id,
                "session_id": result.session_id,
                "decision_needed": requirement.confirmation_message,
                "instructions_for_you": (
                    "Tell the user what needs approval and that you'll post it once they say yes. "
                    "Do not tell them it's already posted — it isn't."
                ),
            }
        return {"status": "completed", "content": result.content}

    async def resume_standup_pipeline(run_id: str, session_id: str, decision: str) -> Dict[str, Any]:
        """Resume a paused standup pipeline run with the human's decision.
        `decision` must be "approve" or "deny". Only call this after a human has
        actually given that decision — never guess or assume approval."""
        pipeline = build_standup_pipeline_with_approval(settings, pipeline_mcp_tools, db)
        run_output = await pipeline.aget_run_output(run_id=run_id, session_id=session_id)
        if run_output is None or not run_output.is_paused:
            return {"status": "error", "message": "No paused run found for that run_id/session_id."}

        for requirement in run_output.active_step_requirements:
            if decision == "approve":
                requirement.confirm()
            else:
                requirement.reject()

        result = await pipeline.acontinue_run(run_output)
        if result.is_paused:
            return {"status": "paused", "run_id": result.run_id, "session_id": result.session_id}
        if decision == "approve":
            return {"status": "posted", "content": result.content}
        return {"status": "denied", "content": result.content}

    return start_standup_pipeline, resume_standup_pipeline


# --- The mandatory review step ---

REVIEW_INSTRUCTIONS = """You are a strict grounding reviewer. You will be given a
user's message, an assistant's draft reply, and the trace of tool calls (name,
arguments, result) the assistant made while producing that reply.

Check exactly one thing: does every factual claim in the draft reply trace back
to data actually present in one of those tool results? Do not evaluate tone,
completeness, or style — only grounding. A claim about something the pipeline
tools did (e.g. "I've drafted a post" or "waiting for your approval") is
grounded if a tool result actually says that.

Respond in this exact form:
    APPROVED — no ungrounded claims.
or:
    NEEDS CORRECTION — <the specific claim(s) not backed by any tool result>
"""


def build_reviewer(settings: Settings) -> Agent:
    return Agent(
        model=LiteLLM(
            id=settings.reviewer_model_id,
            api_key=settings.litellm_api_key,
            api_base=settings.litellm_base_url,
            # Anthropic rejects temperature+top_p sent together; agno always
            # sends both with non-None defaults, so drop both explicitly.
            temperature=None,
            top_p=None,
        ),
        instructions=REVIEW_INSTRUCTIONS,
    )


def _tool_trace_from_response(response: Any) -> List[Dict[str, Any]]:
    return [
        {"tool_name": t.tool_name, "tool_args": t.tool_args, "result": t.result}
        for t in (response.tools or [])
    ]


async def review_reply(reviewer: Agent, *, user_message: str, draft_reply: str, tool_trace: List[Dict[str, Any]]) -> str:
    prompt = (
        f"User message:\n{user_message}\n\n"
        f"Draft reply:\n{draft_reply}\n\n"
        f"Tool calls made:\n{json.dumps(tool_trace, indent=2, default=str)}\n\n"
        "Review the draft reply for grounding."
    )
    response = await reviewer.arun(prompt)
    return response.content


# --- The outer turn: agent -> mandatory review -> final answer ---


@dataclass
class TurnMetrics:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class TurnResult:
    reply: str
    review_verdict: str
    tool_trace: List[Dict[str, Any]] = field(default_factory=list)
    metrics: TurnMetrics = field(default_factory=TurnMetrics)


def _extract_metrics(response: Any) -> TurnMetrics:
    m = getattr(response, "metrics", None)
    if m is None:
        return TurnMetrics()
    return TurnMetrics(
        input_tokens=getattr(m, "input_tokens", 0) or 0,
        output_tokens=getattr(m, "output_tokens", 0) or 0,
        total_tokens=getattr(m, "total_tokens", 0) or 0,
    )


async def run_turn(agent: Agent, reviewer: Agent, message: str) -> TurnResult:
    response = await agent.arun(message)
    tool_trace = _tool_trace_from_response(response)
    metrics = _extract_metrics(response)

    # Forced, unconditional — not a tool call the first model could skip.
    verdict = await review_reply(reviewer, user_message=message, draft_reply=response.content, tool_trace=tool_trace)

    return TurnResult(reply=response.content, review_verdict=verdict, tool_trace=tool_trace, metrics=metrics)
