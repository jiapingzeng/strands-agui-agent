"""
Configuration management for Strands AG-UI Agent.

This module provides configuration options for the agent and server.
"""

import os
from typing import Optional
from pydantic import BaseModel


class ServerConfig(BaseModel):
    """Server configuration settings."""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    reload: bool = False
    workers: int = 1


class AgentConfig(BaseModel):
    """Agent configuration settings."""
    name: str = "Strands AG-UI Agent"
    model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    temperature: float = 0.7
    streaming: bool = True
    max_tokens: Optional[int] = None


class Config(BaseModel):
    """Main configuration class."""
    server: ServerConfig = ServerConfig()
    agent: AgentConfig = AgentConfig()

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            server=ServerConfig(
                host=os.getenv("HOST", "0.0.0.0"),
                port=int(os.getenv("PORT", "8000")),
                log_level=os.getenv("LOG_LEVEL", "info"),
                reload=os.getenv("RELOAD", "false").lower() == "true",
                workers=int(os.getenv("WORKERS", "1")),
            ),
            agent=AgentConfig(
                name=os.getenv("AGENT_NAME", "Strands AG-UI Agent"),
                model_id=os.getenv("MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"),
                temperature=float(os.getenv("TEMPERATURE", "0.7")),
                streaming=os.getenv("STREAMING", "true").lower() == "true",
                max_tokens=int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None,
            )
        )


# Global configuration instance
config = Config.from_env()