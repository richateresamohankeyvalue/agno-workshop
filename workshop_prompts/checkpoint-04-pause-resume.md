# Prompt: checkpoint-3 → checkpoint-4 (Pause and resume / human approval)

Paste everything below this line into your AI coding assistant.

---

You are helping me build **checkpoint-4** of an Agno workshop project. I already have **checkpoint-3** (deterministic standup pipeline, no write). Keep it. **Add** a durable human approval gate before the one irreversible write.

## HARD RULES

1. Workshop code: smallest clear change. No tests, no CI, no mock MCP server.
2. Keep `standup.py` (read-only pipeline) working.
3. Agno ≥ 3 workflow APIs:  
   `HumanReview`, `OnReject`, `Workflow(db=...)`, pause via `requires_confirmation=True`.
4. Memory from checkpoint-2 carries forward: `LearningMachine(db=db, user_memory=True)` as `learning=` on the agent.
5. Persistence uses the **same Postgres** as checkpoint-2: `PostgresDb(db_url=settings.db_url)`.
6. LiteLLM: `litellm.drop_params = True`, `temperature=None`, `top_p=None`.
7. MCP write tools (exact names): `post_slack_message`, `confirm_action`.

## Goal

Extend the standup pipeline with two more steps:

```
… → synthesize → draft_standup_post → publish_standup_post (PAUSES here)
```

1. **`draft_standup_post`**: call `post_slack_message(channel="standup-updates", message=<standup text>)`.  
   This only **drafts**. Return value includes `pending_action_id`.
2. **`publish_standup_post`**: call `confirm_action(pending_action_id=...)`.  
   This step must use:
   ```python
   human_review=HumanReview(
       requires_confirmation=True,
       confirmation_message="Approve posting today's standup to #standup-updates?",
       on_reject=OnReject.skip,
   )
   ```
   So the workflow **pauses before** this step runs. State is stored in Postgres. A **separate process** resumes it.

## Files to change / add

1. **`src/daily_dev_assistant/pipeline.py`** — add:
   - `APPROVAL_MCP_TOOL_NAMES` = previous tools + `post_slack_message`, `confirm_action`
   - `build_mcp_tools_with_approval(settings)`
   - `make_draft_post_step`, `make_publish_post_step`
   - `build_standup_pipeline_with_approval(settings, mcp_tools, db) -> Workflow`  
     (pass `db=` into `Workflow`)
2. **`standup_with_approval.py`** (new): run the approval pipeline with a fresh `session_id`.  
   If `result.is_paused`, print `run_id`, `session_id`, confirmation message, and the exact  
   `resume_standup.py` commands for approve/deny.
3. **`resume_standup.py`** (new): CLI `--run-id`, `--session-id`, `--decision {approve,deny}`.  
   Load with `pipeline.aget_run_output(...)`, call `requirement.confirm()` or `.reject()`,  
   then `pipeline.acontinue_run(run_output)`. Print posted vs denied clearly.
4. **`README.md`** — checkpoint-4 demo: run → pause → resume deny → run again → resume approve.

## Do NOT

- Do not auto-approve in the same process.
- Do not hold the pause only in memory — it must survive a new process via Postgres.
- Do not wire this into the chat agent yet (checkpoint-5).

## Done when

```bash
docker compose up -d   # Postgres
# MCP server up
uv run python standup_with_approval.py
# → prints run_id + session_id and pause message

uv run python resume_standup.py --run-id <id> --session-id <id> --decision deny
# → nothing posted

# run again, then:
uv run python resume_standup.py --run-id <id> --session-id <id> --decision approve
# → confirm_action runs / standup posted
```

After editing, list changed files and the commands above.
