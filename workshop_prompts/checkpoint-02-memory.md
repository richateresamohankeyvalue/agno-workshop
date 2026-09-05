# Prompt: checkpoint-1 → checkpoint-2 (Memory)

Paste everything below this line into your AI coding assistant.

---

You are helping me build **checkpoint-2** of an Agno workshop project. I already have **checkpoint-1** working (one agent + MCP tools, no memory).

## HARD RULES

1. Workshop code: smallest clear change. No extra frameworks, no tests, no CI, no mock MCP server in this repo.
2. Do not rename packages or delete `main.py`.
3. Use Agno ≥ 3 APIs:
   - `from agno.db.postgres import PostgresDb`
   - `from agno.learn import LearningMachine`
   - Short-term: `add_history_to_context=True`, `num_history_runs=5`
   - Long-term: `LearningMachine(db=db, user_memory=True)` passed as `learning=` on the Agent  
     (**NOT** `enable_user_memories` — invalid on Agno 3)
4. Model: `agno.models.litellm.LiteLLM` with `temperature=None`, `top_p=None`.
5. Module top wherever LiteLLM is used: `import litellm` and `litellm.drop_params = True`.
6. MCP stays external at `MCP_SERVER_URL` (default `http://localhost:8081/sse`).

## Goal

Add **two scopes of memory**, both backed by PostgreSQL:

| Kind | What it stores | Scope | Agno flags |
|---|---|---|---|
| Short-term | Recent conversation turns | `session_id` | `add_history_to_context=True` |
| Long-term | Facts about the person | `user_id` (across sessions) | `LearningMachine(db=db, user_memory=True)` via `learning=` |

## Files to change / add

1. **`docker-compose.yml`** — Postgres only (image `agnohq/pgvector:18`, user/pass/db `ai`, host port **5532**, volume mount **`/var/lib/postgresql`** not `/var/lib/postgresql/data`).
2. **`pyproject.toml`** — add deps: `sqlalchemy>=2.0.0`, `psycopg[binary]>=3.2.0`.
3. **`src/daily_dev_assistant/config.py`** — add `db_url` / `AGENT_DB_URL`, default  
   `postgresql+psycopg://ai:ai@localhost:5532/ai`.
4. **`.env.example`** — document `AGENT_DB_URL`.
5. **`src/daily_dev_assistant/agent.py`** — wire `PostgresDb`, `LearningMachine(db=db, user_memory=True)` as `learning=`, short-term flags, `user_id` + `session_id` into `Agent(...)`. Keep existing MCP tools (`get_calendar_events`, `get_github_prs`). Mention memory briefly in instructions.
6. **`main.py`** — CLI flags `--user` (default `dev`) and `--session` (default new UUID). Pass both into `build_agent`. Print user + session at startup. Still print tool calls after each reply.
7. **`README.md`** — retitle to checkpoint-2; document `docker compose up -d`, the three-step memory demo.

## Do NOT

- Do not add pipelines, reviewers, graders, or Slack posting.
- Do not implement an MCP server in this repo.
- Do not switch to SQLite “for simplicity” — use Postgres as above.

## Done when

```bash
docker compose up -d
uv pip install -e .
uv run python main.py --user alice
# turn 1: "Hi, remember that my GitHub username is alice-dev"
# turn 2: "What's my GitHub username?"   → remembers (same session)
# exit, then:
uv run python main.py --user alice
# "What's my GitHub username?"           → still remembers (new session, same user)
```

After editing, list changed files and the exact commands above.
