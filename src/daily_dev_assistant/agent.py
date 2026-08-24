"""Checkpoint 1: one agent, a couple of MCP tools, nothing else — no memory,
no pipeline, no reviewer. The agent decides for itself when to call a tool;
everything it knows about *how* to use one comes from the MCP server's own
tool descriptions, not from `INSTRUCTIONS`.
"""

from __future__ import annotations

from agno.agent import Agent
from agno.models.litellm import LiteLLM
from agno.tools.mcp import MCPTools

from daily_dev_assistant.config import Settings

# The slice of the MCP server's full tool catalog this agent gets. Add a name
# here to give the agent a new capability — nothing else needs to change.
TOOL_NAMES = ["get_calendar_events", "get_github_prs"]

INSTRUCTIONS = """You are a developer's daily assistant. You have tools backed
by a shared mock data server: calendar events and GitHub pull requests.
Answer the user's question using those tools. Never state a fact you didn't
get from a tool call, and if a tool genuinely returns nothing, say so plainly."""


def build_mcp_tools(settings: Settings) -> MCPTools:
    return MCPTools(
        url=settings.mcp_server_url,
        transport=settings.mcp_transport,
        include_tools=TOOL_NAMES,
    )


def build_agent(settings: Settings, mcp_tools: MCPTools) -> Agent:
    return Agent(
        model=LiteLLM(id=settings.model_id, api_key=settings.litellm_api_key, api_base=settings.litellm_base_url),
        instructions=INSTRUCTIONS,
        tools=[mcp_tools],
    )
