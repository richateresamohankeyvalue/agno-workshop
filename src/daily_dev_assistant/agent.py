"""Checkpoint 2: the same agent from checkpoint-1, now with memory.

Two kinds of memory, two different scopes:

  Short-term (session history)
    → What was said *in this conversation*. Scoped to a session_id.
    → Enabled by `add_history_to_context=True`.

  Long-term (user memories)
    → Facts the agent decides are worth retaining about a person.
    → Scoped to a user_id — survives across sessions.
    → Enabled by `update_memory_on_run=True` + `add_memories_to_context=True`.

Both are backed by PostgreSQL via Agno's built-in `PostgresDb`.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

import litellm
from agno.agent import Agent
from agno.db.base import BaseDb
from agno.db.postgres import PostgresDb
from agno.models.litellm import LiteLLM
from agno.tools.mcp import MCPTools

from daily_dev_assistant.config import Settings

# The shared workshop LiteLLM proxy rejects sampling params (temperature,
# top_p, ...) that Anthropic models route through it don't support.
litellm.drop_params = True

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
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    instructions: str = INSTRUCTIONS,
    extra_tools: Optional[Sequence[Callable[..., Any]]] = None,
    db: Optional[BaseDb] = None,
) -> Agent:
    db = db or PostgresDb(db_url=settings.db_url)

    return Agent(
        model=LiteLLM(
            id=settings.model_id,
            api_key=settings.litellm_api_key,
            api_base=settings.litellm_base_url,
            # Anthropic rejects temperature+top_p sent together; agno always
            # sends both with non-None defaults, so drop both explicitly.
            temperature=None,
            top_p=None,
        ),
        instructions=instructions,
        tools=[mcp_tools, *(extra_tools or [])],
        # --- Storage (session persistence) ---
        db=db,
        # --- Short-term: include recent turns in context ---
        add_history_to_context=True,
        num_history_runs=5,
        # --- Long-term: extract and recall user-scoped facts ---
        # (`enable_user_memories` was renamed in the installed agno>=3.0.0)
        update_memory_on_run=True,
        add_memories_to_context=True,
        # --- Identity ---
        user_id=user_id,
        session_id=session_id,
    )
