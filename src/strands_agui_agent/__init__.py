"""
Strands AG-UI Agent: A Python AI agent that integrates Strands Agents with AG-UI Protocol.

This package provides a bridge between Strands Agents and the AG-UI protocol,
enabling AI agents to be used in AG-UI compatible applications with proper
frontend tool execution support.

Features:
- Correct AG-UI tool execution pattern (frontend tools)
- Streaming and non-streaming endpoints
- Event translation between Strands and AG-UI protocols
- Full AG-UI protocol compliance
- Single clean server implementation
"""

from .agent import StrandsAGUIAgent
from .server import create_app

__version__ = "0.2.0"
__all__ = [
    "StrandsAGUIAgent",
    "create_app"
]