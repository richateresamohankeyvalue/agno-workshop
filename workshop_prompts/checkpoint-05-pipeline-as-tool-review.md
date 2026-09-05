# Prompt: checkpoint-4 → checkpoint-5 (Pipeline-as-tool + mandatory review)

Paste everything below this line into your AI coding assistant.

---

You are helping me build **checkpoint-5** of an Agno workshop project. I already have:
- checkpoint-2 memory agent (`main.py`)
- checkpoint-4 standup pipeline with approval (`standup_with_approval.py` / `resume_standup.py`)

Keep those. **Compose** them: expose the pipeline as agent tools, and force a review step the model cannot skip.

## HARD RULES

1. Workshop code: smallest clear change. No tests, no CI, no mock MCP server.
2. Do not delete earlier entrypoints.
3. Review must be a **plain unconditional function call** after `agent.arun` — **not** a tool the agent can choose to skip.
4. Memory from checkpoint-2 carries forward: `LearningMachine(db=db, user_memory=True)` as `learning=` on the agent.
5. Reviewer model must be **configurable and different** from the agent model (`REVIEWER_MODEL_ID`).
6. LiteLLM: `litellm.drop_params = True`, `temperature=None`, `top_p=None`.
7. Extend `build_agent` with optional `instructions=` and `extra_tools=` rather than duplicating the agent builder.

## Goal (two compositions)

### A) Pipeline as tools

Wrap `build_standup_pipeline_with_approval` as two async Python callables the agent can call like normal tools:

- `start_standup_pipeline()` → runs pipeline; if paused, return a dict with  
  `status`, `run_id`, `session_id`, `decision_needed`, and instructions telling the agent  
  **not** to claim the post already happened.
- `resume_standup_pipeline(run_id, session_id, decision)` → `decision` is `"approve"` or `"deny"` only after a real human said so.

### B) Mandatory review

Outer turn sequence in code:

```
agent.arun(message) → build tool_trace from response.tools
→ review_reply(reviewer, user_message, draft, tool_trace)   # ALWAYS
→ return reply + review verdict
```

Reviewer instructions: check **grounding only** (every factual claim traces to a tool result). Respond exactly:
- `APPROVED — no ungrounded claims.` or
- `NEEDS CORRECTION — <claims>`

## Files to change / add

1. **`src/daily_dev_assistant/config.py`** — add `reviewer_model_id` / `REVIEWER_MODEL_ID`,  
   default something smaller than the agent model (e.g. `claude-haiku-4-5-20251001`).
2. **`.env.example`** — document `REVIEWER_MODEL_ID`.
3. **`src/daily_dev_assistant/agent.py`** — optional `instructions` and `extra_tools` on `build_agent`.
4. **`src/daily_dev_assistant/agent_pipeline.py`** (new):
   - `build_standup_tools(settings, pipeline_mcp_tools, db)`
   - `build_reviewer(settings)`, `review_reply(...)`, `run_turn(agent, reviewer, message)`
   - `TurnResult(reply, review_verdict, tool_trace)`
5. **`assistant.py`** (new root entrypoint): memory agent + standup tools + reviewer;  
   every stdin turn goes through `run_turn`; print reply, tool calls, and **Review:** line.
6. **`README.md`** — explain the composition; demo: ask to prep standup; mention that commenting  
   out the `review_reply` line silently removes the check (teaching moment).

## Do NOT

- Do not make review a tool / “ask the agent to self-check.”
- Do not remove `standup_with_approval.py` / `resume_standup.py`.
- Do not add grading or token printing yet (checkpoint-6).

## Done when

```bash
docker compose up -d
# MCP up
uv run python assistant.py --user alice
> Can you prep my standup?
# agent calls start_standup_pipeline, relays pause honestly
# prints Review: APPROVED … (or NEEDS CORRECTION …)
```

After editing, list changed files and the commands above.
