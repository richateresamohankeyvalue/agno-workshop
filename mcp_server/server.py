"""Workshop mock MCP server — fake calendar / Jira / GitHub / Slack data.

Run locally:
    uv run python mcp_server/server.py

Or via docker compose (service: mcp) on http://localhost:8081/sse
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "bakeoff-mock",
    host="0.0.0.0",
    port=8081,
    instructions="Mock data server for the Agno workshop. Tools return fixed demo data.",
)

# In-memory store for the draft → confirm write pattern (checkpoint-4+)
_pending_actions: Dict[str, Dict[str, Any]] = {}


@mcp.tool()
def get_user_profile() -> Dict[str, Any]:
    """Return the current developer's profile (name, username, team)."""
    return {
        "name": "Alice Chen",
        "username": "alice-dev",
        "email": "alice@example.com",
        "team": "Platform",
    }


@mcp.tool()
def get_calendar_events(start_date: str = "today", end_date: str = "today") -> List[Dict[str, Any]]:
    """Return calendar events between start_date and end_date (use 'today' or ISO dates)."""
    today = date.today().isoformat()
    return [
        {
            "id": "evt-1",
            "title": "Standup",
            "start": f"{today}T09:30:00",
            "end": f"{today}T09:45:00",
            "attendees": ["alice-dev", "bob"],
        },
        {
            "id": "evt-2",
            "title": "Sprint planning",
            "start": f"{today}T14:00:00",
            "end": f"{today}T15:00:00",
            "attendees": ["Platform"],
        },
        {
            "id": "evt-3",
            "title": "1:1 with manager",
            "start": f"{(date.today() + timedelta(days=1)).isoformat()}T11:00:00",
            "end": f"{(date.today() + timedelta(days=1)).isoformat()}T11:30:00",
            "attendees": ["alice-dev", "manager"],
        },
    ]


@mcp.tool()
def get_jira_tickets(assignee: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return open Jira tickets, optionally filtered by assignee username."""
    tickets = [
        {
            "id": "PLAT-101",
            "title": "Add health check endpoint",
            "status": "In Progress",
            "assignee": "alice-dev",
            "priority": "Medium",
        },
        {
            "id": "PLAT-98",
            "title": "Fix flaky auth test",
            "status": "In Review",
            "assignee": "alice-dev",
            "priority": "High",
        },
        {
            "id": "PLAT-90",
            "title": "Migrate config to env vars",
            "status": "Blocked",
            "assignee": "alice-dev",
            "priority": "Low",
            "blocked_by": "Waiting on infra for secrets store",
        },
        {
            "id": "PLAT-77",
            "title": "Docs for onboarding",
            "status": "To Do",
            "assignee": "bob",
            "priority": "Low",
        },
    ]
    if assignee:
        return [t for t in tickets if t["assignee"] == assignee]
    return tickets


@mcp.tool()
def get_jira_ticket_detail(ticket_id: str) -> Dict[str, Any]:
    """Return detail for one Jira ticket by id (e.g. PLAT-101)."""
    for ticket in get_jira_tickets():
        if ticket["id"] == ticket_id:
            return {
                **ticket,
                "description": f"Details for {ticket_id}: implement and ship.",
                "comments": ["Looks good so far", "Needs one more test"],
            }
    return {"error": f"Ticket {ticket_id} not found"}


@mcp.tool()
def get_github_prs(state: str = "open") -> List[Dict[str, Any]]:
    """Return GitHub pull requests. state is usually 'open'."""
    return [
        {
            "number": 42,
            "title": "Add health check endpoint",
            "author": "alice-dev",
            "state": "open",
            "reviewers": ["bob"],
            "url": "https://github.com/example/platform/pull/42",
        },
        {
            "number": 41,
            "title": "Fix flaky auth test",
            "author": "alice-dev",
            "state": "open",
            "reviewers": ["carol"],
            "url": "https://github.com/example/platform/pull/41",
        },
        {
            "number": 40,
            "title": "Bump dependency versions",
            "author": "bob",
            "state": "open",
            "reviewers": ["alice-dev"],
            "url": "https://github.com/example/platform/pull/40",
            "needs_review_from": "alice-dev",
        },
    ]


@mcp.tool()
def post_slack_message(channel: str, message: str) -> Dict[str, Any]:
    """Draft a Slack message. Does NOT post yet — returns a pending_action_id to confirm."""
    pending_action_id = f"pending-{uuid.uuid4()}"
    draft = {
        "pending_action_id": pending_action_id,
        "channel": channel,
        "message": message,
        "status": "pending",
    }
    _pending_actions[pending_action_id] = draft
    return draft


@mcp.tool()
def confirm_action(pending_action_id: str) -> Dict[str, Any]:
    """Confirm a previously drafted write (e.g. Slack post). This is the irreversible step."""
    draft = _pending_actions.get(pending_action_id)
    if draft is None:
        return {"status": "error", "message": f"Unknown pending_action_id: {pending_action_id}"}
    draft = {**draft, "status": "posted"}
    _pending_actions.pop(pending_action_id, None)
    return draft


if __name__ == "__main__":
    print("Mock MCP server listening on http://0.0.0.0:8081/sse")
    mcp.run(transport="sse")
