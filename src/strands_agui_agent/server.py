"""
FastAPI Server for Strands AG-UI Agent.

Provides a simplified AG-UI streaming endpoint for Strands Agents.
"""

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ag_ui.core import RunAgentInput, RunErrorEvent
from ag_ui.encoder import EventEncoder

from .agent import StrandsAGUIAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(agent: StrandsAGUIAgent = None) -> FastAPI:
    """
    Create a simplified FastAPI application with AG-UI streaming endpoint.

    Args:
        agent: Optional pre-configured Strands AG-UI Agent

    Returns:
        Configured FastAPI application
    """
    if agent is None:
        agent = StrandsAGUIAgent()

    app = FastAPI(
        title="Strands AG-UI Agent Server",
        description="AG-UI streaming endpoint for Strands Agents",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    encoder = EventEncoder()

    @app.get("/")
    async def root():
        """Root endpoint providing basic information."""
        return {
            "name": "Strands AG-UI Agent Server",
            "version": "0.1.0",
            "description": "AG-UI streaming endpoint for Strands Agents",
            "endpoint": "/stream"
        }

    @app.post("/stream")
    async def stream_endpoint(input_data: RunAgentInput):
        """
        Streaming endpoint that returns AG-UI events via Server-Sent Events.

        Args:
            input_data: AG-UI compatible input data

        Returns:
            StreamingResponse with AG-UI events
        """
        logger.info(f"Streaming request received for thread {input_data.thread_id}")

        async def event_generator():
            """Generate AG-UI events from the agent."""
            try:
                async for event in agent.run_streaming(input_data):
                    encoded_event = encoder.encode(event)
                    logger.debug(f"Streaming event: {event.type}")
                    yield encoded_event
            except Exception as e:
                logger.error(f"Error in streaming: {e}")
                error_event = RunErrorEvent(
                    message=str(e),
                    code="STREAMING_ERROR"
                )
                yield encoder.encode(error_event)

        return StreamingResponse(
            event_generator(),
            media_type=encoder.get_content_type(),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    return app


async def main():
    """Main entry point for running the server."""
    import uvicorn
    from .config import config

    agent = StrandsAGUIAgent(agent_name=config.agent.name)
    app = create_app(agent)

    logger.info(f"Starting Strands AG-UI Agent server on {config.server.host}:{config.server.port}")
    logger.info(f"Agent: {config.agent.name}")
    logger.info(f"Model: {config.agent.model_id}")
    logger.info("Available endpoint:")
    logger.info(f"  - Streaming: http://{config.server.host}:{config.server.port}/stream")

    uvicorn_config = uvicorn.Config(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level,
        access_log=True,
        reload=config.server.reload,
        workers=config.server.workers if not config.server.reload else 1,
    )
    server = uvicorn.Server(uvicorn_config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())