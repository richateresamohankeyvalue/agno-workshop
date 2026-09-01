# agno-workshop

A developer daily-assistant agent built on [Agno](https://github.com/agno-agi/agno), for the
Agent SDK Bake-off workshop.

This branch: **`checkpoint-3` — A deterministic pipeline.** A fixed, multi-step standup
procedure that runs the same way every time — because a `Workflow`'s step list decides what
runs next, not a model. No agent is involved yet: `standup.py` calls the pipeline directly.

Checkpoint-2's memory-backed agent (`main.py`) is still here, unchanged.

## The pipeline

```
fetch profile -> fetch open tickets -> fetch today's calendar -> synthesize
```

- The first three steps each call one MCP tool directly (`get_user_profile`,
  `get_jira_tickets`, `get_calendar_events`) — no LLM, no decision, just data.
- `fetch_tickets` reads the previous step's output (`step_input.get_step_output(...)`) to
  filter tickets by the profile's username — steps can depend on each other's results even
  though the *order* is fixed by the workflow definition, not by any step.
- The last step, `synthesize`, is the only one with a model in it: a plain LiteLLM call that
  turns the three gathered facts into standup prose. It has no tools and cannot go fetch
  anything itself — it only writes up what already arrived.

## Architecture

- `src/daily_dev_assistant/pipeline.py` — the `Workflow` and its four `Step`s.
- `standup.py` — the runnable entrypoint: connects to MCP, builds the pipeline, runs it once,
  prints the result. Compare with `main.py` — no agent, no chat loop, no tool-choice at all.
- `src/daily_dev_assistant/agent.py`, `main.py`, `docker-compose.yml` — unchanged from
  checkpoint-2.

## Setup

```bash
# 1. Start PostgreSQL (only needed for main.py / checkpoint-2's agent)
docker compose up -d

# 2. Install deps
uv venv .venv
uv pip install -e .

# 3. Configure
cp .env.example .env   # fill in LITELLM_API_KEY
```

The MCP mock server must be running separately (see checkpoint-1 README).

## Running

```bash
uv run python standup.py
```

## Demo script

```bash
# 1. Run it — narrate each step firing in the fixed order as it streams
uv run python standup.py

# 2. Open src/daily_dev_assistant/pipeline.py, swap the order of two steps in
#    build_standup_pipeline (e.g. fetch_calendar before fetch_tickets), run again —
#    the order actually changes. No prompt anywhere told it to.
```

## Hands-on

Add a step that fetches detail for every item found in `fetch_tickets` — one call to
`get_jira_ticket_detail(ticket_id)` per ticket — and thread that richer detail into the
`synthesize` step's prompt.
