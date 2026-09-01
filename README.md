# agno-workshop

A developer daily-assistant agent built on [Agno](https://github.com/agno-agi/agno), for the
Agent SDK Bake-off workshop.

This branch: **`checkpoint-6` — Evaluation, cost, and swapping models.** Three things that
matter most in a real adoption decision, added to the checkpoint-5 assistant:

| Feature | What it shows |
|---|---|
| **Token usage** | `input / output / total` printed after every turn — zero extra setup, straight off the response |
| **Automated grader** | A second, different model scores each reply on grounding, completeness, conciseness |
| **Model portability** | Change `AGENT_MODEL_ID` in `.env`, re-run the same script — zero code changes |

## Architecture (what's new)

- `src/daily_dev_assistant/grader.py` — `build_grader` + `grade_reply`: a small model that
  scores each response against a three-criterion rubric. Deliberately a different model family
  from the agent's own.
- `src/daily_dev_assistant/agent_pipeline.py` — `TurnMetrics` added to `TurnResult`, extracted
  from the Agno response's built-in `metrics` field.
- `assistant.py` — prints token counts, review verdict (checkpoint-5), and grading result after
  every turn. Prints the model id at startup so model-swap is visible.
- `src/daily_dev_assistant/config.py` — adds `GRADER_MODEL_ID`.

Everything from checkpoints 1–5 is unchanged: `main.py`, `standup.py`, `standup_with_approval.py`,
`resume_standup.py`.

## Setup

```bash
# 1. Start Postgres + mock MCP server
docker compose up -d

# 2. Install deps
uv venv .venv
uv pip install -e .

# 3. Configure
cp .env.example .env   # fill in LITELLM_API_KEY
```

The mock MCP server lives in this repo (`mcp_server/`) and is started by
`docker compose up -d` as the `mcp` service on `http://localhost:8081/sse`.
You can also run it without Docker: `uv run python mcp_server/server.py`.

## Running

```bash
uv run python assistant.py --user alice
```

## Demo script

```
1. run "hi"
   — point at the token line: input / output / total

2. Change AGENT_MODEL_ID in .env to a different provider, re-run —
   same script, different model, zero other changes
```

## Hands-on

Write one grading check in `grader.py` for a failure mode you care about (tone, verbosity, a
compliance rule) and run it against a real transcript.
