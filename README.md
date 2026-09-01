# agno-workshop

A developer daily-assistant agent built on [Agno](https://github.com/agno-agi/agno), for the
Agent SDK Bake-off workshop.

This branch: **`checkpoint-4` — Pause and resume.** The checkpoint-3 standup pipeline, extended
with two more steps that draft a Slack post and then pause for a real human decision before the
one call that can't be undone. The pause is durable — resuming happens from a second, separate
process, loading the paused run by id from the same PostgreSQL database checkpoint-2's memory
already uses.

Checkpoint-3's read-only pipeline (`standup.py` / `build_standup_pipeline`) is still here,
unchanged. Checkpoint-2's memory-backed agent (`main.py`) is still here too.

## The pipeline

```
fetch profile -> fetch open tickets -> fetch today's calendar -> synthesize
    -> draft standup post -> [PAUSE for approval] -> publish standup post
```

- `draft_standup_post` calls `post_slack_message` — the mock server's own draft/confirm write
  pattern: this call has no side effect, it just returns a `pending_action_id`.
- `publish_standup_post` is where the pipeline stops. `Step(..., human_review=HumanReview(
  requires_confirmation=True, ...))` pauses execution *before* this step's body runs, and
  persists that paused state to the workflow's `db` — the same `PostgresDb` checkpoint-2 uses
  for memory. Only on approval does this step actually run and call `confirm_action` — the one
  call in the whole pipeline that posts anything for real.
- A denial (`OnReject.skip`) — or a run nobody ever resumes — leaves the draft sitting
  unconfirmed. Nothing gets posted either way.

## Architecture

- `src/daily_dev_assistant/pipeline.py` — checkpoint-3's four steps, unchanged, plus
  `make_draft_post_step`, `make_publish_post_step`, and `build_standup_pipeline_with_approval`
  (takes a `db` so pauses survive across processes).
- `standup_with_approval.py` — runs the pipeline once. If it pauses, prints the run id, session
  id, and the exact `resume_standup.py` commands to approve or deny.
- `resume_standup.py` — a **separate script invocation**: loads the paused run from Postgres by
  `(run_id, session_id)`, applies the decision, and continues it. Nothing about the paused state
  lives in memory between these two scripts.
- `standup.py`, `src/daily_dev_assistant/agent.py`, `main.py` — unchanged from checkpoint-3.
- `docker-compose.yml` — fixed a pre-existing bug: the `postgres:18`-based image needs its
  volume mounted at `/var/lib/postgresql`, not `/var/lib/postgresql/data`; the old mount point
  made every fresh `docker compose up` crash-loop the container.

## Setup

```bash
# 1. Start PostgreSQL — required this time, pauses are persisted there
docker compose up -d

# 2. Install deps
uv venv .venv
uv pip install -e .

# 3. Configure
cp .env.example .env   # fill in LITELLM_API_KEY
```

The MCP mock server ([agent-sdk-bakeoff-mcp-server](https://github.com/richateresamohankeyvalue/agent-sdk-bakeoff-mcp-server))
must be running separately (`docker compose up --build` in that repo) and reachable at
`MCP_SERVER_URL` (default `http://localhost:8081/sse`).

## Running

```bash
uv run python standup_with_approval.py
```

## Demo script

```bash
# 1. Run it — it pauses; note the printed run id and session id
uv run python standup_with_approval.py

# 2. Resume that run id with "deny" — confirm nothing was posted
uv run python resume_standup.py --run-id <id> --session-id <id> --decision deny

# 3. Run it again, then resume with "approve" — check the mock Slack data for the write
uv run python standup_with_approval.py
uv run python resume_standup.py --run-id <id> --session-id <id> --decision approve
```

## Hands-on

Kill the terminal between step 1 and resuming — then resume anyway from a brand-new terminal.
Same run id, same session id, same result: the state was never in memory to lose.
