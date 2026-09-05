# Prompt: checkpoint-6 → checkpoint-7 (The full assistant)

Paste everything below this line into your AI coding assistant.

---

You are helping me build **checkpoint-7** of an Agno workshop project. I already have **checkpoint-6** (assistant with memory, standup pipeline tools, review, tokens, grader). Keep all of that. **Add** a second pipeline (sprint planning) and unify instructions so **one agent** handles three request shapes with **no mode flag**.

## HARD RULES

1. Workshop code: smallest clear change. No tests, no CI, no mock MCP server.
2. Do not remove review, grader, or token printing.
3. No CLI `--mode`, no separate “sprint script” as the main demo — `assistant.py` is the entrypoint.
4. Memory from checkpoint-2 carries forward: `LearningMachine(db=db, user_memory=True)` as `learning=` on the agent.
5. The agent must **infer** request shape from the user message alone.
6. LiteLLM: `litellm.drop_params = True`, `temperature=None`, `top_p=None`.
7. MCP tool names for sprint gathering (exact):  
   `get_user_profile`, `get_jira_tickets`, `get_calendar_events`, `get_github_prs`.

## Goal — three request shapes, one agent

| Shape | Behavior | Mechanism |
|---|---|---|
| Quick lookup | 1–2 MCP tool calls | existing calendar/PR tools |
| Standup prep | fixed pipeline, pauses for approval | existing `start_` / `resume_standup_pipeline` |
| Sprint planning | fixed pipeline → structured brief | **new** `prep_sprint_planning` tool |

### Sprint planning pipeline (fixed order)

```
fetch_profile → fetch_tickets → fetch_calendar → fetch_prs → sprint_synthesize
```

Synthesis headings (no invented facts):
- Carry-over
- In review
- Upcoming meetings
- Suggested priorities

Wrap as one async tool `prep_sprint_planning()` that runs the workflow and returns  
`{"status": "completed", "content": ...}` (no approval gate for sprint — standup keeps approval).

### Instructions

Replace the assistant’s instructions with **one block** that describes all three shapes and tells the model to pick from the message alone (never ask which mode). Keep memory guidance and “never invent facts.”

## Files to change / add

1. **`src/daily_dev_assistant/pipeline.py`** — add:
   - `SPRINT_MCP_TOOL_NAMES`, `build_sprint_mcp_tools`
   - `make_fetch_prs_step`, `make_sprint_synthesize_step`
   - `build_sprint_planning_pipeline(settings, mcp_tools)`
2. **`src/daily_dev_assistant/agent_pipeline.py`** — add `build_sprint_planning_tool(...)`.
3. **`assistant.py`** — connect sprint MCP tools; attach `prep_sprint_planning` alongside standup tools;  
   use the unified instructions; keep review + tokens + grade printing.
4. **`README.md`** — checkpoint-7 demo script with the three example prompts below.

## Do NOT

- Do not add a fourth pipeline or more product features.
- Do not require the user to pass a mode / intent enum.
- Do not remove checkpoint-3/4 standalone scripts.

## Done when

```bash
uv run python assistant.py --user alice

> Any PRs waiting for my review?
# quick lookup — get_github_prs (or similar), short answer

> Can you prep my standup?
# start_standup_pipeline — pauses for approval; Review + Grade still print

> Prep me for sprint planning
# prep_sprint_planning — structured brief with the four headings
```

After editing, list changed files and the commands above.
