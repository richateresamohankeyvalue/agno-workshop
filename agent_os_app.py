#!/usr/bin/env python3
"""AgentOS entry point for the checkpoint-7 assistant.

Serves the same agent as `assistant.py` — tools + memory + standup pipeline +
sprint planning, one instructions block deciding the request shape — over
REST/WebSocket/MCP instead of a terminal loop. One process, one agent
instance, many concurrent users/sessions: `user_id`/`session_id` now arrive
per-request (via the API call) instead of from CLI args.

Not carried over from the terminal loop: the checkpoint-6 reviewer/grader
wrapping in `assistant.py`'s `run_turn` is a manual outer loop around
`agent.arun()`, not something AgentOS's request path has a slot for. This
entry point serves the bare agent; the review/grade step would need to be
reattached as `post_hooks` on the `Agent` if wanted here too.

Usage:
    uv run python agent_os_app.py
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from agno.db.postgres import PostgresDb
from agno.os import AgentOS
from starlette.middleware.cors import CORSMiddleware

from assistant import FULL_ASSISTANT_INSTRUCTIONS
from daily_dev_assistant.agent import build_agent, build_mcp_tools
from daily_dev_assistant.agent_pipeline import build_sprint_planning_tool, build_standup_tools
from daily_dev_assistant.config import load_settings
from daily_dev_assistant.pipeline import build_mcp_tools_with_approval, build_sprint_mcp_tools

settings = load_settings()
db = PostgresDb(db_url=settings.db_url)

# Attached directly to the agent's tools=[...] below, so AgentOS discovers it
# and manages connect/close itself.
agent_mcp_tools = build_mcp_tools(settings)

# Only reachable through the start/resume/prep closures below — AgentOS can't
# see these from the outside, so their lifecycle is handled by `lifespan`.
pipeline_mcp_tools = build_mcp_tools_with_approval(settings)
sprint_mcp_tools = build_sprint_mcp_tools(settings)

start_standup, resume_standup = build_standup_tools(settings, pipeline_mcp_tools, db)
prep_sprint = build_sprint_planning_tool(settings, sprint_mcp_tools)

assistant = build_agent(
    settings,
    agent_mcp_tools,
    instructions=FULL_ASSISTANT_INSTRUCTIONS,
    extra_tools=[start_standup, resume_standup, prep_sprint],
    db=db,
)
# A stable id/name so API calls can target `/agents/daily-dev-assistant/...`
# instead of the random id AgentOS would otherwise generate.
assistant.id = "daily-dev-assistant"
assistant.name = "Daily Dev Assistant"


@asynccontextmanager
async def lifespan(_app):
    await pipeline_mcp_tools.connect()
    await sprint_mcp_tools.connect()
    try:
        yield
    finally:
        await pipeline_mcp_tools.close()
        await sprint_mcp_tools.close()


agent_os = AgentOS(
    agents=[assistant],
    db=db,
    tracing=True,
    mcp_server=True,
    lifespan=lifespan,
)
app = agent_os.get_app()

# AgentOS's own CORS setup doesn't set `allow_private_network`, so Chrome's
# Private Network Access check rejects the preflight the Control Plane
# (os.agno.com, a public origin) sends before it's allowed to reach this
# private localhost server — the browser reports it as a bare CORS error.
# Swap in an equivalent CORSMiddleware with that flag set.
app.user_middleware = [m for m in app.user_middleware if m.cls != CORSMiddleware]
app.middleware_stack = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=agent_os.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    allow_private_network=True,
)


if __name__ == "__main__":
    agent_os.serve(app="agent_os_app:app", reload=True)
