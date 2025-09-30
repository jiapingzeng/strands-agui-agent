"""
Simple example of a Strands AG-UI Agent with custom tools.

This example demonstrates how to create an agent with custom tools
and serve it with AG-UI protocol compatibility.
"""

import asyncio
from strands import Agent, tool
from strands.models.bedrock import BedrockModel

from strands_agui_agent import StrandsAGUIAgent, create_app


@tool
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression.

    Args:
        expression: A mathematical expression to evaluate (e.g., "2 + 2", "10 * 5")

    Returns:
        The result of the mathematical expression
    """
    try:
        # Simple safe evaluation for basic math
        # In production, use a proper math expression parser
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in expression):
            return "Error: Only basic math operations are allowed"

        result = eval(expression)
        return f"The result is: {result}"
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"


@tool
def word_counter(text: str) -> str:
    """
    Count the number of words in a given text.

    Args:
        text: The text to count words in

    Returns:
        The number of words in the text
    """
    word_count = len(text.split())
    return f"The text contains {word_count} words."


@tool
def text_reverser(text: str) -> str:
    """
    Reverse the given text.

    Args:
        text: The text to reverse

    Returns:
        The reversed text
    """
    return f"Reversed text: {text[::-1]}"


def create_example_agent() -> StrandsAGUIAgent:
    """Create an example agent with custom tools."""

    # Create Strands agent with tools
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        temperature=0.7,
        streaming=True,
    )

    strands_agent = Agent(
        model=model,
        tools=[calculator, word_counter, text_reverser],
        name="Example Calculator Agent"
    )

    # Wrap with AG-UI bridge
    agui_agent = StrandsAGUIAgent(
        strands_agent=strands_agent,
        agent_name="Example Calculator Agent with AG-UI"
    )

    return agui_agent


async def main():
    """Run the example agent server."""
    # Create the example agent
    agent = create_example_agent()

    # Create the FastAPI app
    app = create_app(agent)

    # Run the server
    import uvicorn

    print("Starting Example Strands AG-UI Agent Server...")
    print("Available tools: calculator, word_counter, text_reverser")
    print("Endpoints:")
    print("  - Streaming: http://localhost:8000/stream")
    print("  - Non-streaming: http://localhost:8000/chat")
    print("  - Health: http://localhost:8000/health")
    print("  - Tools: http://localhost:8000/tools")

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())