"""
Strands AG-UI Agent Bridge - Fixed Implementation.

This module provides the corrected bridge class that properly connects Strands Agents
with the AG-UI protocol, using native Strands tool execution and event streaming.
"""

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from dataclasses import dataclass

from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands.types._events import TypedEvent, ModelStreamChunkEvent, ToolStreamEvent, ToolResultEvent
from strands.types.content import ContentBlock
from strands.types.tools import ToolResult

from .agui_types import (
    Event,
    Message,
    RunAgentInput,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    UserMessage,
    AssistantMessage,
    ToolMessage,
    SystemMessage,
    ToolCall,
    FunctionCall,
)


@dataclass
class ExecutionState:
    """State management for tool execution flow."""
    thread_id: str
    run_id: str
    pending_tools: Dict[str, Dict[str, Any]]
    tool_results: Dict[str, str]
    current_message_id: Optional[str] = None
    waiting_for_tools: bool = False

    def __post_init__(self):
        if not hasattr(self, 'pending_tools'):
            self.pending_tools = {}
        if not hasattr(self, 'tool_results'):
            self.tool_results = {}


class StrandsAGUIAgent:
    """
    Corrected Bridge class that properly connects Strands Agents with AG-UI Protocol.

    This implementation uses native Strands tool execution and event streaming
    instead of bypassing the Strands system.
    """

    def __init__(
        self,
        strands_agent: Optional[Agent] = None,
        agent_name: str = "Strands AG-UI Agent",
        **kwargs
    ):
        """
        Initialize the Strands AG-UI Agent.

        Args:
            strands_agent: Optional pre-configured Strands Agent
            agent_name: Name for the agent
            **kwargs: Additional configuration options
        """
        self.agent_name = agent_name
        self.execution_states: Dict[str, ExecutionState] = {}

        # Initialize Strands Agent if not provided
        if strands_agent is None:
            model = BedrockModel(
                model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                temperature=0.7,
                streaming=True,
            )
            self.strands_agent = Agent(model=model, **kwargs)
        else:
            self.strands_agent = strands_agent

    def _convert_agui_message_to_strands(self, message: Message) -> Dict[str, Any]:
        """Convert AG-UI message to Strands message format."""
        if isinstance(message, UserMessage):
            return {"role": "user", "content": [{"text": message.content}]}
        elif isinstance(message, AssistantMessage):
            content = []
            if message.content:
                content.append({"text": message.content})
            if message.tool_calls:
                # Convert tool calls to Strands format
                for tc in message.tool_calls:
                    content.append({
                        "toolUse": {
                            "toolUseId": tc.id,
                            "name": tc.function.name,
                            "input": json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                        }
                    })
            return {"role": "assistant", "content": content}
        elif isinstance(message, SystemMessage):
            return {"role": "system", "content": [{"text": message.content}]}
        elif isinstance(message, ToolMessage):
            return {
                "role": "user",
                "content": [{
                    "toolResult": {
                        "toolUseId": message.tool_call_id,
                        "content": [{"text": message.content}],
                        "status": "success" if not message.error else "error"
                    }
                }]
            }
        else:
            # Fallback
            return {"role": message.role, "content": [{"text": message.content or ""}]}

    def _register_agui_tools_with_strands(self, agui_tools: List) -> None:
        """Register AG-UI tools as proper Strands tools."""
        if not agui_tools:
            return

        # Create Strands tools for each AG-UI tool
        strands_tools = []
        for agui_tool in agui_tools:
            strands_tool = self._create_strands_tool_from_agui(agui_tool)
            strands_tools.append(strands_tool)

        # Re-create agent with tools if we have new ones
        if strands_tools:
            model = BedrockModel(
                model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                temperature=0.7,
                streaming=True,
            )
            self.strands_agent = Agent(model=model, tools=strands_tools)

    def _create_strands_tool_from_agui(self, agui_tool):
        """Create a proper Strands tool from AG-UI tool specification."""

        async def frontend_tool(**kwargs) -> str:
            """Tool that will be executed by the frontend - this should never be called directly."""
            # This should not be reached in proper AG-UI flow
            # Tools should be intercepted before execution
            raise RuntimeError(f"Frontend tool {agui_tool.name} was executed in backend - this indicates improper AG-UI integration")

        # Set function metadata
        frontend_tool.__name__ = agui_tool.name
        frontend_tool.__doc__ = agui_tool.description

        # Apply Strands tool decorator
        return tool(frontend_tool)

    def _convert_strands_to_agui_events(
        self,
        strands_event: Union[TypedEvent, Dict[str, Any]],
        execution_state: ExecutionState
    ) -> List[Event]:
        """Convert Strands events to AG-UI events."""
        events = []

        # Handle dictionary events (actual Strands format)
        if isinstance(strands_event, dict):
            # Handle text content streaming
            if 'event' in strands_event:
                event_data = strands_event['event']

                # Handle message start
                if 'messageStart' in event_data:
                    if not execution_state.current_message_id:
                        execution_state.current_message_id = str(uuid.uuid4())
                        events.append(TextMessageStartEvent(
                            message_id=execution_state.current_message_id,
                            role="assistant"
                        ))

                # Handle text content delta
                elif 'contentBlockDelta' in event_data:
                    delta_data = event_data['contentBlockDelta']
                    if 'delta' in delta_data and 'text' in delta_data['delta']:
                        if not execution_state.current_message_id:
                            execution_state.current_message_id = str(uuid.uuid4())
                            events.append(TextMessageStartEvent(
                                message_id=execution_state.current_message_id,
                                role="assistant"
                            ))

                        events.append(TextMessageContentEvent(
                            message_id=execution_state.current_message_id,
                            delta=delta_data['delta']['text']
                        ))

                # Handle tool use start
                elif 'contentBlockStart' in event_data:
                    start_data = event_data['contentBlockStart']
                    if 'start' in start_data and 'toolUse' in start_data['start']:
                        tool_use = start_data['start']['toolUse']
                        tool_call_id = tool_use.get('toolUseId', str(uuid.uuid4()))
                        tool_name = tool_use.get('name', 'unknown')

                        execution_state.pending_tools[tool_call_id] = {
                            'name': tool_name,
                            'input': tool_use.get('input', {})
                        }

                        events.append(ToolCallStartEvent(
                            tool_call_id=tool_call_id,
                            tool_call_name=tool_name
                        ))

            # Handle current_tool_use events (tool input streaming)
            elif 'current_tool_use' in strands_event:
                tool_use = strands_event['current_tool_use']
                tool_call_id = tool_use.get('toolUseId', str(uuid.uuid4()))

                # Check if this is a new tool or continuation
                if tool_call_id not in execution_state.pending_tools:
                    execution_state.pending_tools[tool_call_id] = {
                        'name': tool_use.get('name', 'unknown'),
                        'input': tool_use.get('input', {})
                    }

                    events.append(ToolCallStartEvent(
                        tool_call_id=tool_call_id,
                        tool_call_name=tool_use.get('name', 'unknown')
                    ))

                # Always emit args event for tool input
                events.append(ToolCallArgsEvent(
                    tool_call_id=tool_call_id,
                    delta=str(tool_use.get('input', ''))
                ))

            # Handle complete message with toolUse
            elif 'message' in strands_event:
                message = strands_event['message']
                if message.get('role') == 'assistant' and 'content' in message:
                    for content_item in message['content']:
                        if 'toolUse' in content_item:
                            tool_use = content_item['toolUse']
                            tool_call_id = tool_use.get('toolUseId', str(uuid.uuid4()))
                            tool_name = tool_use.get('name', 'unknown')

                            # Ensure we have the tool tracked
                            if tool_call_id not in execution_state.pending_tools:
                                execution_state.pending_tools[tool_call_id] = {
                                    'name': tool_name,
                                    'input': tool_use.get('input', {})
                                }

                            # Emit tool call end
                            events.append(ToolCallEndEvent(tool_call_id=tool_call_id))

        # Legacy handling for TypedEvent objects (if any)
        elif hasattr(strands_event, '__dict__'):
            # Handle model streaming events
            if isinstance(strands_event, ModelStreamChunkEvent):
                if hasattr(strands_event, 'chunk') and strands_event.chunk:
                    chunk_data = strands_event.chunk
                    if isinstance(chunk_data, dict) and 'contentBlockDelta' in chunk_data:
                        delta = chunk_data['contentBlockDelta'].get('delta', {})
                        if 'text' in delta:
                            if not execution_state.current_message_id:
                                execution_state.current_message_id = str(uuid.uuid4())
                                events.append(TextMessageStartEvent(
                                    message_id=execution_state.current_message_id,
                                    role="assistant"
                                ))

                            events.append(TextMessageContentEvent(
                                message_id=execution_state.current_message_id,
                                delta=delta['text']
                            ))

        return events

    async def run_streaming(self, input_data: RunAgentInput) -> AsyncGenerator[Event, None]:
        """
        Run the agent with proper Strands streaming integration.

        Args:
            input_data: AG-UI compatible input data

        Yields:
            AG-UI events from native Strands execution
        """
        # Create execution state
        execution_state = ExecutionState(
            thread_id=input_data.thread_id,
            run_id=input_data.run_id,
            pending_tools={},
            tool_results={}
        )
        self.execution_states[f"{input_data.thread_id}:{input_data.run_id}"] = execution_state

        # Emit run started event
        yield RunStartedEvent(
            thread_id=input_data.thread_id,
            run_id=input_data.run_id
        )

        try:
            # Register AG-UI tools with Strands
            if input_data.tools:
                self._register_agui_tools_with_strands(input_data.tools)

            # Convert AG-UI messages to Strands format
            strands_messages = []
            for msg in input_data.messages:
                strands_msg = self._convert_agui_message_to_strands(msg)
                strands_messages.append(strands_msg)

            # Set messages in agent
            self.strands_agent.messages = strands_messages

            # Get the latest user message for prompting
            user_message = None
            for msg in reversed(input_data.messages):
                if isinstance(msg, UserMessage):
                    user_message = msg.content
                    break

            if not user_message:
                user_message = "Hello"

            # Use native Strands streaming
            has_tool_calls = False
            should_pause_for_tools = False

            async for strands_event in self.strands_agent.stream_async(user_message):
                # Convert Strands events to AG-UI events
                agui_events = self._convert_strands_to_agui_events(strands_event, execution_state)

                for agui_event in agui_events:
                    if isinstance(agui_event, (ToolCallStartEvent, ToolCallArgsEvent, ToolCallEndEvent)):
                        has_tool_calls = True
                    yield agui_event

                # Check if we should pause for tool execution (when we see messageStop with tool_use)
                if isinstance(strands_event, dict) and 'event' in strands_event:
                    event_data = strands_event['event']
                    if 'messageStop' in event_data and event_data['messageStop'].get('stopReason') == 'tool_use':
                        should_pause_for_tools = True
                        break

                # Check if this is the final event
                if hasattr(strands_event, 'result') and strands_event.result:
                    break

            # If we detected tool calls and should pause, don't continue streaming
            if should_pause_for_tools and execution_state.pending_tools:
                has_tool_calls = True

            # Close any open text message
            if execution_state.current_message_id:
                yield TextMessageEndEvent(message_id=execution_state.current_message_id)

            # Determine final status
            if has_tool_calls and execution_state.pending_tools:
                execution_state.waiting_for_tools = True
                yield RunFinishedEvent(
                    thread_id=input_data.thread_id,
                    run_id=input_data.run_id,
                    result={
                        "status": "waiting_for_tools",
                        "tool_calls": [
                            {"id": tool_id, "name": tool_data["name"]}
                            for tool_id, tool_data in execution_state.pending_tools.items()
                        ]
                    }
                )
            else:
                yield RunFinishedEvent(
                    thread_id=input_data.thread_id,
                    run_id=input_data.run_id,
                    result={"status": "completed"}
                )

        except Exception as e:
            yield RunErrorEvent(
                message=str(e),
                code="AGENT_ERROR"
            )

    async def continue_after_tools(
        self,
        thread_id: str,
        run_id: str,
        tool_results: Dict[str, str]
    ) -> AsyncGenerator[Event, None]:
        """Continue execution after receiving tool results from frontend."""

        execution_key = f"{thread_id}:{run_id}"
        execution_state = self.execution_states.get(execution_key)

        if not execution_state:
            yield RunErrorEvent(
                message="Execution state not found",
                code="STATE_ERROR"
            )
            return

        try:
            # Update tool results
            execution_state.tool_results.update(tool_results)

            # Create tool result messages for Strands
            for tool_call_id, result in tool_results.items():
                tool_result_msg = {
                    "role": "user",
                    "content": [{
                        "toolResult": {
                            "toolUseId": tool_call_id,
                            "content": [{"text": result}],
                            "status": "success"
                        }
                    }]
                }
                self.strands_agent.messages.append(tool_result_msg)

            # Continue with Strands execution
            execution_state.current_message_id = str(uuid.uuid4())
            yield TextMessageStartEvent(
                message_id=execution_state.current_message_id,
                role="assistant"
            )

            # Run the agent again to process tool results
            async for strands_event in self.strands_agent.stream_async():
                agui_events = self._convert_strands_to_agui_events(strands_event, execution_state)
                for agui_event in agui_events:
                    yield agui_event

            # Close message and finish
            if execution_state.current_message_id:
                yield TextMessageEndEvent(message_id=execution_state.current_message_id)

            yield RunFinishedEvent(
                thread_id=thread_id,
                run_id=run_id,
                result={"status": "completed"}
            )

        except Exception as e:
            yield RunErrorEvent(
                message=str(e),
                code="CONTINUATION_ERROR"
            )

    async def run_non_streaming(self, input_data: RunAgentInput) -> Dict[str, Any]:
        """
        Run the agent without streaming, collecting all events.

        Args:
            input_data: AG-UI compatible input data

        Returns:
            Complete response with messages and state
        """
        try:
            messages = []
            final_status = "completed"

            # Collect all streaming events
            async for event in self.run_streaming(input_data):
                if hasattr(event, 'type'):
                    if event.type == "TEXT_MESSAGE_CONTENT":
                        # Collect text content
                        pass  # In a full implementation, you'd collect this
                    elif event.type == "RUN_FINISHED":
                        final_status = event.result.get("status", "completed")

            # Build response messages
            response_message = AssistantMessage(
                id=str(uuid.uuid4()),
                content="Response completed"  # In real implementation, collect actual content
            )

            all_messages = input_data.messages + [response_message]

            return {
                "thread_id": input_data.thread_id,
                "run_id": input_data.run_id,
                "messages": [msg.model_dump() for msg in all_messages],
                "state": input_data.state,
                "status": final_status
            }

        except Exception as e:
            return {
                "thread_id": input_data.thread_id,
                "run_id": input_data.run_id,
                "messages": [msg.model_dump() for msg in input_data.messages],
                "state": input_data.state,
                "status": "error",
                "error": str(e)
            }

    def get_execution_state(self, thread_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """Get current execution state for a thread/run."""
        execution_key = f"{thread_id}:{run_id}"
        state = self.execution_states.get(execution_key)

        if state:
            return {
                "thread_id": state.thread_id,
                "run_id": state.run_id,
                "waiting_for_tools": state.waiting_for_tools,
                "pending_tools": state.pending_tools,
                "tool_results_count": len(state.tool_results)
            }
        return None

    def add_tool(self, tool_func):
        """Add a tool to the underlying Strands agent."""
        # Re-create agent with additional tool
        current_tools = getattr(self.strands_agent, 'tools', [])
        current_tools.append(tool_func)

        model = BedrockModel(
            model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            temperature=0.7,
            streaming=True,
        )
        self.strands_agent = Agent(model=model, tools=current_tools)

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools in AG-UI format."""
        if hasattr(self.strands_agent, 'tool_registry') and self.strands_agent.tool_registry:
            tools = []
            for tool_name, tool_config in self.strands_agent.tool_registry.get_all_tools_config().items():
                tools.append({
                    "name": tool_name,
                    "description": tool_config.get("description", ""),
                    "parameters": tool_config.get("inputSchema", {})
                })
            return tools
        return []