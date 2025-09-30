"""
FastAPI Server for Strands AG-UI Agent.

This module provides HTTP endpoints for both streaming and non-streaming
AG-UI protocol interactions with Strands Agents.
"""

import asyncio
import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ag_ui.core import RunAgentInput, RunErrorEvent
from ag_ui.encoder import EventEncoder

from .agent import StrandsAGUIAgent


class ToolResultsInput(BaseModel):
    """Input for providing tool execution results from frontend."""
    thread_id: str
    run_id: str
    tool_results: Dict[str, str]  # tool_call_id -> result


class ContinueExecutionInput(BaseModel):
    """Input for continuing execution after tool results."""
    thread_id: str
    run_id: str

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(agent: StrandsAGUIAgent = None) -> FastAPI:
    """
    Create a FastAPI application with AG-UI endpoints.

    Args:
        agent: Optional pre-configured Strands AG-UI Agent

    Returns:
        Configured FastAPI application
    """
    # Initialize agent if not provided
    if agent is None:
        agent = StrandsAGUIAgent()

    # Create FastAPI app
    app = FastAPI(
        title="Strands AG-UI Agent Server",
        description="HTTP server providing AG-UI protocol endpoints for Strands Agents",
        version="0.1.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize event encoder
    encoder = EventEncoder()

    @app.get("/")
    async def root():
        """Root endpoint providing basic information."""
        return {
            "name": "Strands AG-UI Agent Server",
            "version": "0.1.0",
            "description": "HTTP server providing AG-UI protocol endpoints for Strands Agents",
            "endpoints": {
                "streaming": "/stream",
                "non_streaming": "/chat"
            }
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

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
                # Send error event
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
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
            }
        )

    @app.post("/chat")
    async def chat_endpoint(input_data: RunAgentInput) -> Dict[str, Any]:
        """
        Non-streaming endpoint that returns a complete response.

        Args:
            input_data: AG-UI compatible input data

        Returns:
            Complete response with messages and state
        """
        logger.info(f"Chat request received for thread {input_data.thread_id}")

        try:
            result = await agent.run_non_streaming(input_data)
            logger.info(f"Chat request completed for thread {input_data.thread_id}")
            return result
        except Exception as e:
            logger.error(f"Error in chat endpoint: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/tools")
    async def get_tools():
        """Get available tools from the agent."""
        try:
            tools = agent.get_available_tools()
            return {"tools": tools}
        except Exception as e:
            logger.error(f"Error getting tools: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/execution-state/{thread_id}/{run_id}")
    async def get_execution_state(thread_id: str, run_id: str):
        """Get current execution state for a thread/run."""
        try:
            state = agent.get_execution_state(thread_id, run_id)
            if state:
                return state
            else:
                raise HTTPException(status_code=404, detail="Execution state not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting execution state: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tool-results")
    async def submit_tool_results(tool_results_input: ToolResultsInput):
        """
        Endpoint for frontend to submit tool execution results.

        Args:
            tool_results_input: Tool results from frontend execution

        Returns:
            Confirmation that results were received
        """
        logger.info(
            f"Tool results received for thread {tool_results_input.thread_id}, "
            f"run {tool_results_input.run_id}: {list(tool_results_input.tool_results.keys())}"
        )

        try:
            # Store the tool results (in a real implementation, you'd use a proper store)
            # For now, we'll just acknowledge receipt
            return {
                "status": "received",
                "thread_id": tool_results_input.thread_id,
                "run_id": tool_results_input.run_id,
                "tool_results_count": len(tool_results_input.tool_results),
                "message": "Tool results received. Use a proper state management system for production."
            }

        except Exception as e:
            logger.error(f"Error processing tool results: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/continue")
    async def continue_execution(continue_input: ContinueExecutionInput):
        """
        Endpoint to continue execution after tool results are provided.

        Args:
            continue_input: Thread and run identifiers

        Returns:
            Streaming response with remaining events
        """
        logger.info(
            f"Continue execution requested for thread {continue_input.thread_id}, "
            f"run {continue_input.run_id}"
        )

        # Get execution state to retrieve tool results
        execution_state = agent.get_execution_state(continue_input.thread_id, continue_input.run_id)
        if not execution_state:
            raise HTTPException(status_code=404, detail="Execution state not found")

        if not execution_state.get("waiting_for_tools", False):
            raise HTTPException(status_code=400, detail="Not waiting for tool results")

        async def continuation_generator():
            """Generate remaining AG-UI events after tool execution."""
            try:
                # For this demo, we'll simulate tool results
                # In a real implementation, these would come from the frontend
                simulated_tool_results = {}
                for tool_id, tool_data in execution_state.get("pending_tools", {}).items():
                    if tool_data.get("name") == "calculator":
                        # Simulate calculator execution
                        expression = tool_data.get("input", {}).get("expression", "0")
                        try:
                            result = str(eval(expression))  # In production, use a proper math parser
                            simulated_tool_results[tool_id] = f"The result is: {result}"
                        except:
                            simulated_tool_results[tool_id] = "Error: Invalid expression"
                    else:
                        simulated_tool_results[tool_id] = f"Tool {tool_data.get('name')} executed successfully"

                # Continue execution with tool results
                async for event in agent.continue_after_tools(
                    continue_input.thread_id,
                    continue_input.run_id,
                    simulated_tool_results
                ):
                    encoded_event = encoder.encode(event)
                    logger.debug(f"Continuation event: {event.type}")
                    yield encoded_event

            except Exception as e:
                logger.error(f"Error in continuation: {e}")
                error_event = RunErrorEvent(
                    message=str(e),
                    code="CONTINUATION_ERROR"
                )
                yield encoder.encode(error_event)

        return StreamingResponse(
            continuation_generator(),
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

    # Create the agent and app
    agent = StrandsAGUIAgent(agent_name=config.agent.name)
    app = create_app(agent)

    logger.info(f"Starting Strands AG-UI Agent server on {config.server.host}:{config.server.port}")
    logger.info(f"Agent: {config.agent.name}")
    logger.info(f"Model: {config.agent.model_id}")
    logger.info("Frontend Tool Execution Pattern Enabled")
    logger.info("Available endpoints:")
    logger.info(f"  - Root: http://{config.server.host}:{config.server.port}/")
    logger.info(f"  - Streaming: http://{config.server.host}:{config.server.port}/stream")
    logger.info(f"  - Tool Results: http://{config.server.host}:{config.server.port}/tool-results")
    logger.info(f"  - Continue: http://{config.server.host}:{config.server.port}/continue")
    logger.info(f"  - Non-streaming: http://{config.server.host}:{config.server.port}/chat")
    logger.info(f"  - Health: http://{config.server.host}:{config.server.port}/health")
    logger.info(f"  - Tools: http://{config.server.host}:{config.server.port}/tools")

    # Run the server
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