# Prompt: checkpoint-2 → checkpoint-3 (Deterministic standup pipeline)

Paste everything below this line into your AI coding assistant.

---

You are helping me build **checkpoint-3** of an Agno workshop project. I already have **checkpoint-2** (agent + Postgres memory). Keep that working; **add** a deterministic pipeline next to it.

## HARD RULES

1. Workshop code: smallest clear change. No tests, no CI, no mock MCP server in this repo.
2. Do **not** delete or gut `main.py` / memory agent — checkpoint-2 stays runnable.
3. Agno ≥ 3: `from agno.workflow import Workflow, Step, StepInput, StepOutput`
4. Memory from checkpoint-2 carries forward: `LearningMachine(db=db, user_memory=True)` as `learning=` on the agent.
5. Model: `LiteLLM` with `litellm.drop_params = True` and `temperature=None, top_p=None`.
6. MCP is external. Tool names to use exactly:  
   `get_user_profile`, `get_jira_tickets`, `get_calendar_events`.

## Goal

A **fixed-order standup pipeline** — the workflow decides step order, not the model:

```
fetch_profile → fetch_tickets → fetch_calendar → synthesize
```

- First three steps: call MCP tools **directly** (no agent, no model choosing tools).
- `fetch_tickets` reads the profile step output and passes `assignee=<profile.username>`.
- Last step: one LLM call that turns already-gathered data into standup prose under  
  **What shipped / What's next / What's blocked**. Never invent facts.

## Files to change / add

1. **`src/daily_dev_assistant/pipeline.py`** (new) containing:
   - `build_mcp_tools(settings)` with the three tool names above
   - helper `_call_tool(mcp_tools, tool_name, **kwargs)` that:
     - awaits `mcp_tools.functions[tool_name].entrypoint(**kwargs)`
     - if `result.metadata` has `structured_content`, return  
       `structured_content.get("result", structured_content)`
     - else `json.loads(result.content)`
   - step factories: `make_fetch_profile_step`, `make_fetch_tickets_step`,  
     `make_fetch_calendar_step`, `make_synthesize_step`
   - `build_standup_pipeline(settings, mcp_tools) -> Workflow`
2. **`standup.py`** (new root entrypoint): connect MCP → build pipeline →  
   `await pipeline.arun(input="Prep today's standup update.")` → print `result.content`.
3. **`README.md`** — checkpoint-3: how to run `uv run python standup.py`, note that  
   reordering steps in `build_standup_pipeline` changes execution order.

## Do NOT

- Do not wrap this pipeline as an agent tool yet (that is checkpoint-5).
- Do not add human approval / Slack posting yet (that is checkpoint-4).
- Do not let the synthesis agent have tools.

## Done when

```bash
# MCP server running at localhost:8081/sse
uv run python standup.py
# prints a standup update assembled from profile + tickets + calendar
# main.py from checkpoint-2 still runs
```

After editing, list changed files and the commands above.
