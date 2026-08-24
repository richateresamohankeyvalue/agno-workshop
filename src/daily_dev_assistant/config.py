"""Environment-driven settings: where the MCP server lives, and which model to use."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_MODEL_ID = "claude-sonnet-5"


@dataclass(frozen=True)
class Settings:
    mcp_server_url: str
    mcp_transport: str
    model_id: str
    litellm_api_key: str | None
    litellm_base_url: str | None


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        mcp_server_url=os.getenv("MCP_SERVER_URL", "http://localhost:8081/sse"),
        mcp_transport=os.getenv("MCP_TRANSPORT", "sse"),
        model_id=os.getenv("AGENT_MODEL_ID", DEFAULT_MODEL_ID),
        litellm_api_key=os.getenv("LITELLM_API_KEY"),
        litellm_base_url=os.getenv("LITELLM_BASE_URL"),
    )
