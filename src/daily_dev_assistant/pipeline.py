"""Checkpoint 3: a deterministic standup pipeline.

Every developer's standup covers the same shape every day — what shipped,
what's next, what's blocked — so it's a real procedure, not something an
agent should improvise turn to turn. This pipeline fixes the step order in
code:

    fetch profile -> fetch open tickets -> fetch today's calendar -> synthesize

No agent decides what runs next; the `Workflow`'s step list does. The last
step is the only one that calls an LLM at all, and only to turn already
-gathered facts into prose — it never decides what to fetch.
"""

from __future__ import annotations

import json

import litellm
from agno.agent import Agent
from agno.models.litellm import LiteLLM
from agno.tools.mcp import MCPTools
from agno.workflow import Step, StepInput, StepOutput, Workflow

from daily_dev_assistant.config import Settings

# The shared workshop LiteLLM proxy rejects sampling params (temperature,
# top_p, ...) that Anthropic models route through it don't support.
litellm.drop_params = True

MCP_TOOL_NAMES = ["get_user_profile", "get_jira_tickets", "get_calendar_events"]


def build_mcp_tools(settings: Settings) -> MCPTools:
    return MCPTools(
        url=settings.mcp_server_url,
        transport=settings.mcp_transport,
        include_tools=MCP_TOOL_NAMES,
    )


async def _call_tool(mcp_tools: MCPTools, tool_name: str, **kwargs) -> object:
    """Call one MCP tool directly, bypassing any agent/model decision.

    List-returning tools hand back their real structure under
    `metadata.structured_content.result`; `.content` for those is just a
    concatenation of pretty-printed JSON blocks, not one parseable
    document. Single-object tools (like the profile) have no metadata at
    all, so `.content` there is the one JSON document to decode.
    """
    fn = mcp_tools.functions[tool_name]
    result = await fn.entrypoint(**kwargs)
    if result.metadata and "structured_content" in result.metadata:
        structured = result.metadata["structured_content"]
        return structured.get("result", structured)
    return json.loads(result.content)


def make_fetch_profile_step(mcp_tools: MCPTools) -> Step:
    async def fetch_profile(step_input: StepInput) -> StepOutput:
        profile = await _call_tool(mcp_tools, "get_user_profile")
        return StepOutput(content=profile)

    return Step(name="fetch_profile", executor=fetch_profile)


def make_fetch_tickets_step(mcp_tools: MCPTools) -> Step:
    async def fetch_tickets(step_input: StepInput) -> StepOutput:
        profile_output = step_input.get_step_output("fetch_profile")
        profile = profile_output.content if profile_output else {}
        assignee = profile.get("username") if isinstance(profile, dict) else None
        tickets = await _call_tool(mcp_tools, "get_jira_tickets", assignee=assignee)
        return StepOutput(content=tickets)

    return Step(name="fetch_tickets", executor=fetch_tickets)


def make_fetch_calendar_step(mcp_tools: MCPTools) -> Step:
    async def fetch_calendar(step_input: StepInput) -> StepOutput:
        events = await _call_tool(mcp_tools, "get_calendar_events", start_date="today", end_date="today")
        return StepOutput(content=events)

    return Step(name="fetch_calendar", executor=fetch_calendar)


SYNTHESIS_INSTRUCTIONS = """You write a developer's standup update from data that has
already been gathered for you — a profile, a list of tickets, and today's calendar
events. Never invent a fact that isn't in that data. Structure the update under three
headings: What shipped, What's next, What's blocked. If a section has nothing to show,
say so plainly rather than omitting it."""


def make_synthesize_step(settings: Settings) -> Step:
    synthesis_agent = Agent(
        model=LiteLLM(id=settings.model_id, api_key=settings.litellm_api_key, api_base=settings.litellm_base_url),
        instructions=SYNTHESIS_INSTRUCTIONS,
    )

    async def synthesize(step_input: StepInput) -> StepOutput:
        profile = step_input.get_step_output("fetch_profile").content
        tickets = step_input.get_step_output("fetch_tickets").content
        calendar = step_input.get_step_output("fetch_calendar").content

        prompt = (
            f"Profile:\n{profile}\n\n"
            f"Open tickets:\n{tickets}\n\n"
            f"Today's calendar events:\n{calendar}\n\n"
            "Write today's standup update."
        )
        response = await synthesis_agent.arun(prompt)
        return StepOutput(content=response.content)

    return Step(name="synthesize", executor=synthesize)


def build_standup_pipeline(settings: Settings, mcp_tools: MCPTools) -> Workflow:
    return Workflow(
        name="standup_pipeline",
        steps=[
            make_fetch_profile_step(mcp_tools),
            make_fetch_tickets_step(mcp_tools),
            make_fetch_calendar_step(mcp_tools),
            make_synthesize_step(settings),
        ],
    )
