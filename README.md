# agno-workshop

A developer daily-assistant agent built on [Agno](https://github.com/agno-agi/agno), for the
Agent SDK Bake-off workshop.

This branch: **`checkpoint-6` — Evaluation, cost, and swapping models.** Three things that
matter most in a real adoption decision, added to the checkpoint-5 assistant:

| Feature | What it shows |
|---|---|
| **Token usage** | `input / output / total` printed after every turn — zero extra setup, straight off the response |
| **Agno evals** | [AgentAsJudgeEval](https://docs.agno.com/evals/agent-as-judge/overview) on every turn + a `Case` suite in `evals.py` ([evaluation](https://docs.agno.com/features/evaluation)) |
| **Model portability** | Change `AGENT_MODEL_ID` in `.env`, re-run the same script — zero code changes |

## Architecture (what's new)

- `src/daily_dev_assistant/grader.py` — wraps Agno's `AgentAsJudgeEval` (numeric score, threshold,
  different `GRADER_MODEL_ID`). This is the framework eval surface, not a hand-rolled second agent.
- `evals.py` — offline/CI-style suite via `Case` + `acli`: agent-as-judge **and** reliability
  (`expected_tool_calls`). Nonzero exit code on failure.
- `src/daily_dev_assistant/agent_pipeline.py` — `TurnMetrics` on `TurnResult` from `response.metrics`.
- `assistant.py` — prints Tokens, Review (cp5), and Eval (judge) after every turn.
- `src/daily_dev_assistant/config.py` — adds `GRADER_MODEL_ID`.

Everything from checkpoints 1–5 is unchanged: `main.py`, `standup.py`, `standup_with_approval.py`,
`resume_standup.py`.

## Setup

```bash
# 1. Start Postgres
docker compose up -d

# 2. Start the shared MCP mock server (separate repo / terminal)
#    https://github.com/richateresamohankeyvalue/agent-sdk-bakeoff-mcp-server
#    docker compose up --build
#    → http://localhost:8081/sse

# 3. Install deps
uv venv .venv
uv pip install -e .

# 4. Configure
cp .env.example .env   # fill in LITELLM_API_KEY
```

## Running

```bash
# Live assistant (per-turn judge + tokens)
uv run python assistant.py --user alice

# Offline eval suite (judge + reliability Cases)
uv run python evals.py
uv run python evals.py --list
uv run python evals.py --name calendar_uses_tool
```

## Demo script

```
1. run "hi"
   — point at Tokens + Eval (score/passed)

2. uv run python evals.py
   — show Case pass/fail (including expected get_calendar_events)

3. Change AGENT_MODEL_ID in .env, re-run assistant.py —
   same script, different model, zero other changes
```

## Hands-on

Add one more `Case` in `evals.py` for a failure mode you care about (tone, a required tool,
a compliance rule) and run `uv run python evals.py --name <your-case>`.
