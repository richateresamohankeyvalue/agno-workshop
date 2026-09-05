# Shared constraints (included in every checkpoint prompt)

Copy this block into every student prompt so different models / IDEs behave the same.

---

## HARD RULES (always)

1. This is a **workshop**. Prefer the smallest clear change. No frameworks, no extra abstractions, no “production hardening,” no tests unless asked, no CI changes.
2. **Do not rename** existing modules, packages, or entrypoints unless the prompt says to.
3. **Do not delete** earlier checkpoint entrypoints (`main.py`, `standup.py`, etc.) — later checkpoints are additive.
4. Use **Agno ≥ 3.0** APIs only. Exact names that matter:
   - DB: `from agno.db.postgres import PostgresDb`
   - Short-term memory: `add_history_to_context=True`, `num_history_runs=5`
   - Long-term memory: `update_memory_on_run=True` and `add_memories_to_context=True`  
     (NOT `enable_user_memories` — that name does not exist on Agno 3)
   - Workflows: `from agno.workflow import Workflow, Step, StepInput, StepOutput, HumanReview, OnReject`
5. Model wrapper: always `agno.models.litellm.LiteLLM`.
6. Shared LiteLLM proxy quirks (apply everywhere you construct `LiteLLM`):
   - At module top: `import litellm` then `litellm.drop_params = True`
   - Pass `temperature=None, top_p=None` into `LiteLLM(...)`
7. MCP tools come from an **external** server at `MCP_SERVER_URL` (default `http://localhost:8081/sse`, transport `sse`). Do **not** implement a mock MCP server inside this repo.
8. Known MCP tool names (use exactly these strings when include-listing tools):
   - reads: `get_user_profile`, `get_jira_tickets`, `get_calendar_events`, `get_github_prs`
   - writes (gated): `post_slack_message`, `confirm_action`
9. Keep comments short and teaching-oriented. No long essays in code.
10. Update `README.md` for the new checkpoint only: what it is, how to run, 3–5 line demo script. Do not rewrite the whole docs history.
11. After coding, list the files you changed and how to run / verify. Do not claim you ran commands unless you actually did.

## Style

- Python 3.12+, `from __future__ import annotations`
- Package lives under `src/daily_dev_assistant/`
- Entrypoints stay at repo root (`main.py`, `standup.py`, …)
- Env via `python-dotenv` + `config.load_settings()`
- Prefer extending `build_agent(...)` with optional kwargs over copying the agent builder
