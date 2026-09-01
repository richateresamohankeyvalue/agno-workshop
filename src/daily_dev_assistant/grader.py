"""Checkpoint 6: automated grading of agent responses.

The grader is a second, different model that scores each response against a
rubric. It runs after every turn — just like the reviewer from checkpoint-5,
but evaluating quality rather than just grounding.

The grading model should be a *different family* from the agent's own model,
so it isn't checking the agent's work with the agent's own blind spots.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List

from agno.agent import Agent
from agno.models.litellm import LiteLLM

from daily_dev_assistant.config import Settings

GRADING_RUBRIC = """You are a strict quality grader for an AI developer assistant.

You will receive: the user's message, the assistant's reply, and the tool calls made.

Score the reply on these criteria (1-5 each):

1. **Grounding** — Every factual claim traces to a tool result. No hallucinations.
2. **Completeness** — The reply addresses what the user actually asked.
3. **Conciseness** — No unnecessary filler or repetition.

Respond in EXACTLY this format (three lines, nothing else):
  Grounding: N/5 — <one sentence reason>
  Completeness: N/5 — <one sentence reason>
  Conciseness: N/5 — <one sentence reason>
"""


@dataclass
class GradeResult:
    raw_verdict: str
    tool_trace: List[Dict[str, Any]]


def build_grader(settings: Settings) -> Agent:
    return Agent(
        model=LiteLLM(
            id=settings.grader_model_id,
            api_key=settings.litellm_api_key,
            api_base=settings.litellm_base_url,
            temperature=None,
            top_p=None,
        ),
        instructions=GRADING_RUBRIC,
    )


async def grade_reply(
    grader: Agent,
    *,
    user_message: str,
    reply: str,
    tool_trace: List[Dict[str, Any]],
) -> GradeResult:
    prompt = (
        f"User message:\n{user_message}\n\n"
        f"Assistant reply:\n{reply}\n\n"
        f"Tool calls:\n{json.dumps(tool_trace, indent=2, default=str)}\n\n"
        "Grade the reply."
    )
    response = await grader.arun(prompt)
    return GradeResult(raw_verdict=response.content, tool_trace=tool_trace)
