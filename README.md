# agno-workshop

A developer daily-assistant agent built on [Agno](https://github.com/agno-agi/agno), for the
Agent SDK Bake-off workshop.

This branch: **`checkpoint-2` — Memory.** The same agent from checkpoint-1, now with two kinds
of memory backed by PostgreSQL:

| | Short-term (session history) | Long-term (user memories) |
|---|---|---|
| **Stores** | The messages in this conversation | Facts the agent learns about the user |
| **Scope** | One `session_id` | One `user_id`, across all sessions |
| **Answers** | "What did we just discuss?" | "What do I know about this person?" |

## Architecture

- `docker-compose.yml` — PostgreSQL (port 5532), the only infra checkpoint-2 adds.
- `src/daily_dev_assistant/config.py` — env-driven settings, now including `db_url`.
- `src/daily_dev_assistant/agent.py` — wires `PostgresDb` to the agent with
  `add_history_to_context=True` (short-term) and `enable_user_memories=True` (long-term).
- `main.py` — the runnable entrypoint, now accepting `--user` and `--session` flags.

## Setup

```bash
# 1. Start PostgreSQL
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
uv run python main.py --user alice
```

## Demo script (the three-step proof)

```bash
# Step 1: tell it something, in a new session
uv run python main.py --user alice
> Hi, remember that my GitHub username is alice-dev
> What's my GitHub username?
> exit

# Step 2: brand new session, SAME user — it still knows (long-term memory)
uv run python main.py --user alice
> What's my GitHub username?
> exit
```

Step 2 works because `enable_user_memories=True` extracts facts scoped to the *user*, not the
session. A new session starts with no history, but the agent recalls user-level facts from the
database.

## Hands-on

Run the three-step demo under your own identity. Before running step 2, predict: will it
remember? Why?
