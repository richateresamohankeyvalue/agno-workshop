# agno-workshop

A developer daily-assistant agent built on [Agno](https://github.com/agno-agi/agno), for the
Agent SDK Bake-off workshop.

This branch: **`checkpoint-7` — The full assistant.** Every earlier checkpoint is a
load-bearing piece of this one system: tool use, memory, a fixed pipeline, human approval,
a mandatory review, evaluation, cost accounting, model portability — all composed into a
single agent that handles three request shapes from one instructions block, deciding for
itself which kind of request it's looking at.

## The three request shapes

| Request | What happens | Example |
|---|---|---|
| Quick lookup | 1–2 tool calls, direct answer | "Any PRs waiting for my review?" |
| Standup prep | Fixed pipeline → pauses for approval | "Can you prep my standup?" |
| Sprint planning | Fixed pipeline → ranked brief | "Prep me for sprint planning" |

No external "mode" flag — the agent infers scope from the message alone.

## Architecture

```
assistant.py
    │
    ├── agent (checkpoint-1/2: tools + memory)
    │     ├── MCP tools: calendar, PRs, tickets
    │     ├── start/resume_standup_pipeline (checkpoint-3/4/5)
    │     └── prep_sprint_planning (checkpoint-7: new)
    │
    ├── reviewer (checkpoint-5: grounding check, unconditional)
    ├── grader (checkpoint-6: quality rubric)
    └── token metrics (checkpoint-6: usage accounting)
```

**What's new in checkpoint-7:**
- `src/daily_dev_assistant/pipeline.py` — `build_sprint_planning_pipeline`: fetches profile,
  tickets, calendar, PRs, then synthesizes into a structured sprint brief.
- `src/daily_dev_assistant/agent_pipeline.py` — `build_sprint_planning_tool`: wraps the pipeline
  as a single tool the agent can call.
- `assistant.py` — one instructions block covering all three shapes. The agent decides which
  pipeline (or direct tool call) to use based on the message.

Everything from checkpoints 1–6 is still here, unchanged: `main.py`, `standup.py`,
`standup_with_approval.py`, `resume_standup.py`.

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
1. "Any PRs waiting for my review?"     — quick lookup, 1-2 tool calls
2. "Can you prep my standup?"           — fixed procedure, pauses for approval
3. "Prep me for sprint planning"        — open-ended, ranked options back
```

## Hands-on

Ask the agent something ambiguous — "help me get ready for tomorrow" — and see which shape it
picks. Was it right? Could the instructions be improved?
