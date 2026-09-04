"""Checkpoint 6: Agno evaluation (agent-as-judge).

Uses Agno's built-in AgentAsJudgeEval — not a hand-rolled second agent loop.
Docs: https://docs.agno.com/features/evaluation
     https://docs.agno.com/evals/agent-as-judge/overview

The judge model should differ from the agent under test so it doesn't share
the same blind spots.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agno.db.base import BaseDb
from agno.eval.agent_as_judge import AgentAsJudgeEval
from agno.models.litellm import LiteLLM

from daily_dev_assistant.config import Settings

# Rubric the judge scores against (numeric 1-10, pass if >= threshold).
JUDGE_CRITERIA = (
    "The reply must be grounded in tool results (no invented facts), "
    "answer what the user actually asked, and stay concise without filler."
)


@dataclass
class GradeResult:
    score: Optional[float]
    passed: Optional[bool]
    reason: str
    raw_verdict: str


def build_judge_eval(settings: Settings, db: Optional[BaseDb] = None) -> AgentAsJudgeEval:
    return AgentAsJudgeEval(
        name="reply_quality",
        criteria=JUDGE_CRITERIA,
        scoring_strategy="numeric",
        threshold=7,
        model=LiteLLM(
            id=settings.grader_model_id,
            api_key=settings.litellm_api_key,
            api_base=settings.litellm_base_url,
            temperature=None,
            top_p=None,
        ),
        db=db,
        show_spinner=False,
        print_results=False,
        print_summary=False,
    )


async def grade_reply(
    evaluation: AgentAsJudgeEval,
    *,
    user_message: str,
    reply: str,
    tool_trace: List[Dict[str, Any]] | None = None,
) -> GradeResult:
    """Run Agno AgentAsJudgeEval on one turn's input/output."""
    # Tool trace is context for humans/logs; the judge scores input vs output text.
    _ = tool_trace

    result = await evaluation.arun(input=user_message, output=reply)
    if result is None or not result.results:
        return GradeResult(score=None, passed=None, reason="no eval result", raw_verdict="no eval result")

    first = result.results[0]
    score = first.score
    passed = first.passed
    reason = first.reason or ""
    raw = f"score={score}/10 passed={passed} — {reason}"
    return GradeResult(score=score, passed=passed, reason=reason, raw_verdict=raw)
