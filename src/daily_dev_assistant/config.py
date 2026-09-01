"""Environment-driven settings: where the MCP server lives, which model to use, and where to store memory."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_MODEL_ID = "claude-sonnet-5"
# Reviewer and grader use a different, smaller model — they shouldn't share
# the agent's own blind spots.
DEFAULT_REVIEWER_MODEL_ID = "claude-haiku-4-5-20251001"
DEFAULT_GRADER_MODEL_ID = "claude-haiku-4-5-20251001"
DEFAULT_DB_URL = "postgresql+psycopg://ai:ai@localhost:5532/ai"


@dataclass(frozen=True)
class Settings:
    mcp_server_url: str
    mcp_transport: str
    model_id: str
    reviewer_model_id: str
    grader_model_id: str
    litellm_api_key: str | None
    litellm_base_url: str | None
    db_url: str


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        mcp_server_url=os.getenv("MCP_SERVER_URL", "http://localhost:8081/sse"),
        mcp_transport=os.getenv("MCP_TRANSPORT", "sse"),
        model_id=os.getenv("AGENT_MODEL_ID", DEFAULT_MODEL_ID),
        reviewer_model_id=os.getenv("REVIEWER_MODEL_ID", DEFAULT_REVIEWER_MODEL_ID),
        grader_model_id=os.getenv("GRADER_MODEL_ID", DEFAULT_GRADER_MODEL_ID),
        litellm_api_key=os.getenv("LITELLM_API_KEY"),
        litellm_base_url=os.getenv("LITELLM_BASE_URL"),
        db_url=os.getenv("AGENT_DB_URL", DEFAULT_DB_URL),
    )
