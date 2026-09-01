# agno-workshop

A developer daily-assistant agent built on [Agno](https://github.com/agno-agi/agno), for the
Agent SDK Bake-off workshop.

This branch: **`checkpoint-5` — Pipeline-as-tool, and a review step that can't be skipped.**
Two things get composed: the checkpoint-4 standup pipeline becomes an ordinary start/resume tool
pair on the checkpoint-2 memory agent, and every turn now runs through a code-enforced sequence
— agent responds, then a second, smaller model reviews the reply against its own tool-call
trace, unconditionally, before anything is shown as final.

Checkpoints 1–4 are all still here, unchanged (aside from two pre-existing bugs fixed below):
`main.py` (memory agent alone), `standup.py` (read-only pipeline alone), `standup_with_approval.py`
+ `resume_standup.py` (pipeline with the approval gate, driven directly, no agent).

## The composition

```
agent.arun(message)              <- may call start_standup_pipeline / resume_standup_pipeline,
                                     which run checkpoint-4's Workflow underneath. The agent
                                     only ever sees two ordinary functions.
      |
      v
review_reply(...)                <- forced, unconditional. A second model (small, different
                                     from the agent's) checks every claim in the draft reply
                                     against the trace of tool calls that produced it.
      |
      v
reply + review verdict printed
```

- `start_standup_pipeline` / `resume_standup_pipeline` (in `agent_pipeline.py`) wrap
  `build_standup_pipeline_with_approval` from checkpoint-4. The agent never sees a paused
  `Workflow` object — just two async functions with docstrings, like any other tool. When the
  pipeline pauses, the tool returns a dict describing the decision, and the agent's instructions
  tell it to relay that honestly rather than claim the post already went out.
- The review step lives in `run_turn()`, not as a tool. It's a plain `await review_reply(...)`
  call that always executes after `agent.arun(...)` — the first model was never offered a choice
  about whether to be checked. Comment that one line out and the review result just silently
  stops appearing; nothing crashes. That's the actual regression this project hit once.
- The reviewer is a separate, smaller model (`REVIEWER_MODEL_ID`, defaults to
  `claude-haiku-4-5-20251001`) — a different model from the agent's own, so it isn't checking
  the agent's work with the agent's own blind spots.

## Architecture

- `src/daily_dev_assistant/agent_pipeline.py` — `build_standup_tools` (the tool pair),
  `build_reviewer` + `review_reply` (the mandatory check), `run_turn` (the outer sequence).
- `assistant.py` — the runnable entrypoint: memory agent + pipeline tools + reviewer, one chat
  loop, every turn going through `run_turn`.
- `src/daily_dev_assistant/agent.py` — `build_agent` now takes optional `instructions` and
  `extra_tools` params so checkpoint-2's agent can be extended without copying it.
- `src/daily_dev_assistant/pipeline.py`, `standup.py`, `standup_with_approval.py`,
  `resume_standup.py` — unchanged from checkpoint-4.

**Two pre-existing bugs fixed** (found while building this checkpoint, present since
checkpoint-2/3 but never actually exercised until an agent was constructed here):
- `agent.py` called `Agent(..., enable_user_memories=True)` — that kwarg doesn't exist on the
  installed `agno>=3.0.0`; it's `update_memory_on_run=True` + `add_memories_to_context=True`
  now. Long-term memory would have raised on construction the first time anyone actually ran
  `main.py`.
- `agent.py` never set `litellm.drop_params = True` (pipeline.py did, from checkpoint-3) — the
  shared proxy rejects default `temperature`/`top_p` on Claude models, so the memory agent's own
  calls would have failed the same way checkpoint-3's synthesis step originally did.

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

The MCP mock server ([agent-sdk-bakeoff-mcp-server](https://github.com/richateresamohankeyvalue/agent-sdk-bakeoff-mcp-server))
must be running separately (`docker compose up --build` in that repo) and reachable at
`MCP_SERVER_URL` (default `http://localhost:8081/sse`).

## Running

```bash
uv run python assistant.py --user alice
```

## Demo script

```
1. run "Can you prep my standup?"
   — show the review verdict printed after the reply: approved, clean

2. Comment out the `verdict = await review_reply(...)` line in run_turn()
   (src/daily_dev_assistant/agent_pipeline.py), re-run the same prompt —
   the review result is now missing entirely. Put it back.
```

## Hands-on

Ask something the model is likely to over-answer (summarize something with an opinion baked
in, for instance) and read the reviewer's correction request together.
