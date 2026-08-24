# agno-workshop

A developer daily-assistant agent built on [Agno](https://github.com/agno-agi/agno), for the
Agent SDK Bake-off workshop. Each checkpoint in the workshop's arc (tool use → memory →
deterministic pipeline → human approval → mandatory review → evaluation/cost → model
portability) lives on its own `checkpoint-N` branch, building additively on the last.

This branch: **`checkpoint-1` — the agent primitive.** An LLM loop with tools, nothing else —
no memory, no pipeline, no review step. Just the smallest thing that proves a model can reach
real data over MCP and decide for itself when to use it.

## Architecture

- `src/daily_dev_assistant/config.py` — env-driven settings (MCP server location, model id).
- `src/daily_dev_assistant/agent.py` — builds the MCP tool connection and the agent. `TOOL_NAMES`
  is the (deliberately small) slice of the MCP server's full catalog this checkpoint's agent
  gets; `INSTRUCTIONS` only sets scope, not tool-specific guidance.
- `main.py` — the runnable entrypoint: connects, prints the tools available to the agent, then
  loops on stdin, printing each reply and the tool call(s) that produced it.

The agent has no fixed identity for "the user" yet, and no tool to look one up — a question
like "PRs waiting for my review?" will make the model guess. That's expected here; it's fixed
in a later checkpoint, not this one.

## Setup

```bash
uv venv .venv
uv pip install -e .
cp .env.example .env   # fill in LITELLM_API_KEY (and LITELLM_BASE_URL if you're on a proxy)
```

The MCP mock server ([agent-sdk-bakeoff-mcp-server](https://github.com/richateresamohankeyvalue/agent-sdk-bakeoff-mcp-server))
must be running separately (`docker compose up --build` in that repo) and reachable at
`MCP_SERVER_URL` (default `http://localhost:8081/sse`).

## Running

```bash
uv run python main.py
```

Try:
```
> What's on my calendar today?
> Any PRs waiting for my review?
```

The first should work cleanly. The second will likely misfire or guess at who "my" refers to —
point that out, don't fix it here.

## Hands-on

Add a third tool of your choice to `TOOL_NAMES` in `src/daily_dev_assistant/agent.py` (see the
MCP server's README for the full tool catalog), then ask a question only that tool can answer.
