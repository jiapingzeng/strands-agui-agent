"""
Test client for the Strands AG-UI Agent.

This script demonstrates how to interact with the agent's HTTP endpoints
using both streaming and non-streaming requests.
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator

import httpx


async def test_streaming_endpoint():
    """Test the streaming endpoint with Server-Sent Events."""
    print("Testing streaming endpoint...")

    # Prepare test data
    test_input = {
        "threadId": str(uuid.uuid4()),
        "runId": str(uuid.uuid4()),
        "state": {},
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": "Hello! Can you calculate 15 + 27 for me?"
            }
        ],
        "tools": [],
        "context": [],
        "forwardedProps": {}
    }

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "POST",
                "http://localhost:8000/stream",
                json=test_input,
                headers={"Accept": "text/event-stream"},
                timeout=30.0
            ) as response:
                if response.status_code != 200:
                    print(f"Error: {response.status_code} - {response.text}")
                    return

                print("Streaming response:")
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        try:
                            event = json.loads(data)
                            print(f"  Event: {event.get('type')} - {event}")
                        except json.JSONDecodeError:
                            print(f"  Raw data: {data}")

        except Exception as e:
            print(f"Streaming test failed: {e}")


async def test_non_streaming_endpoint():
    """Test the non-streaming endpoint."""
    print("\nTesting non-streaming endpoint...")

    # Prepare test data
    test_input = {
        "threadId": str(uuid.uuid4()),
        "runId": str(uuid.uuid4()),
        "state": {},
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": "Count the words in this sentence: 'Hello world, this is a test message.'"
            }
        ],
        "tools": [],
        "context": [],
        "forwardedProps": {}
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/chat",
                json=test_input,
                timeout=30.0
            )

            if response.status_code == 200:
                result = response.json()
                print("Non-streaming response:")
                print(json.dumps(result, indent=2))
            else:
                print(f"Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Non-streaming test failed: {e}")


async def test_health_endpoint():
    """Test the health endpoint."""
    print("\nTesting health endpoint...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/health", timeout=10.0)

            if response.status_code == 200:
                result = response.json()
                print(f"Health check: {result}")
            else:
                print(f"Health check failed: {response.status_code}")

        except Exception as e:
            print(f"Health check failed: {e}")


async def test_tools_endpoint():
    """Test the tools endpoint."""
    print("\nTesting tools endpoint...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/tools", timeout=10.0)

            if response.status_code == 200:
                result = response.json()
                print("Available tools:")
                print(json.dumps(result, indent=2))
            else:
                print(f"Tools endpoint error: {response.status_code}")

        except Exception as e:
            print(f"Tools endpoint failed: {e}")


async def main():
    """Run all tests."""
    print("Strands AG-UI Agent Test Client")
    print("=" * 40)

    # Wait a moment for the server to be ready
    await asyncio.sleep(1)

    # Test all endpoints
    await test_health_endpoint()
    await test_tools_endpoint()
    await test_non_streaming_endpoint()
    await test_streaming_endpoint()

    print("\nAll tests completed!")


if __name__ == "__main__":
    print("Make sure the server is running on http://localhost:8000")
    print("You can start it with: python -m strands_agui_agent")
    print("Or run the example: python examples/simple_agent.py")
    print()

    asyncio.run(main())