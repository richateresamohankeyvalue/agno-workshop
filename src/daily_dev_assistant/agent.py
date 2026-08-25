"""Checkpoint 2: the same agent from checkpoint-1, now with memory.

Two kinds of memory, two different scopes:

  Short-term (session history)
    → What was said *in this conversation*. Scoped to a session_id.
    → Enabled by `add_history_to_context=True`.

  Long-term (user memories)
    → Facts the agent decides are worth retaining about a person.
    → Scoped to a user_id — survives across sessions.
    → Enabled by `enable_user_memories=True`.

Both are backed by PostgreSQL via Agno's built-in `PostgresDb`.
"""

from __future__ import annotations

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.litellm import LiteLLM
from agno.tools.mcp import MCPTools

from daily_dev_assistant.config import Settings

TOOL_NAMES = ["get_calendar_events", "get_github_prs"]

INSTRUCTIONS = """You are a developer's daily assistant. You have tools backed
by a shared mock data server: calendar events and GitHub pull requests.
Answer the user's question using those tools. Never state a fact you didn't
get from a tool call, and if a tool genuinely returns nothing, say so plainly.

You also have memory. If the user tells you something worth remembering
(their name, username, preferences), retain it for future conversations."""


def build_mcp_tools(settings: Settings) -> MCPTools:
    return MCPTools(
        url=settings.mcp_server_url,
        transport=settings.mcp_transport,
        include_tools=TOOL_NAMES,
    )


def build_agent(
    settings: Settings,
    mcp_tools: MCPTools,
    *,
    user_id: str,
    session_id: str,
) -> Agent:
    db = PostgresDb(db_url=settings.db_url)

    return Agent(
        model=LiteLLM(id=settings.model_id, api_key=settings.litellm_api_key, api_base=settings.litellm_base_url),
        instructions=INSTRUCTIONS,
        tools=[mcp_tools],
        # --- Storage (session persistence) ---
        db=db,
        # --- Short-term: include recent turns in context ---
        add_history_to_context=True,
        num_history_runs=5,
        # --- Long-term: extract and recall user-scoped facts ---
        enable_user_memories=True,
        # --- Identity ---
        user_id=user_id,
        session_id=session_id,
    )
