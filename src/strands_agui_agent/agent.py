"""
Strands AG-UI Agent Bridge - Fixed Implementation.

This module provides the corrected bridge class that properly connects Strands Agents
with the AG-UI protocol, using native Strands tool execution and event streaming.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from dataclasses import dataclass

from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands.types._events import TypedEvent, ModelStreamChunkEvent, ToolStreamEvent, ToolResultEvent
from strands.types.content import ContentBlock
from strands.types.tools import ToolResult

from ag_ui.core import (
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

from .config import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Ensure DEBUG level is enabled

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
        agent_name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the Strands AG-UI Agent.

        Args:
            strands_agent: Optional pre-configured Strands Agent
            agent_name: Name for the agent (uses config if not provided)
            **kwargs: Additional configuration options
        """
        self.agent_name = agent_name or config.agent.name
        self.execution_states: Dict[str, ExecutionState] = {}

        if strands_agent is None:
            model = BedrockModel(
                model_id=config.agent.model_id,
                temperature=config.agent.temperature,
                streaming=config.agent.streaming,
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
                        "status": "success" if not hasattr(message, 'error') or not message.error else "error"
                    }
                }]
            }
        else:
                return {"role": message.role, "content": [{"text": message.content or ""}]}

    def _register_agui_tools_with_strands(self, agui_tools: List) -> None:
        """Register AG-UI tools as proper Strands tools."""
        if not agui_tools:
            return

        strands_tools = []
        for agui_tool in agui_tools:
            strands_tool = self._create_strands_tool_from_agui(agui_tool)
            strands_tools.append(strands_tool)

        if strands_tools:
            model = BedrockModel(
                model_id=config.agent.model_id,
                temperature=config.agent.temperature,
                streaming=config.agent.streaming,
            )
            self.strands_agent = Agent(model=model, tools=strands_tools)

    def _create_strands_tool_from_agui(self, agui_tool):
        """Create a proper Strands tool from AG-UI tool specification."""

        properties = agui_tool.parameters.get('properties', {}) if hasattr(agui_tool, 'parameters') and agui_tool.parameters else {}
        param_names = list(properties.keys())

        def create_frontend_tool():
            if param_names:
                param_str = ', '.join(f'{param}: str = None' for param in param_names)
                func_code = f"""
async def frontend_tool({param_str}) -> str:
    \"\"\"Tool that will be executed by the frontend - this should never be called directly.\"\"\"
    raise RuntimeError(f"Frontend tool {agui_tool.name} was executed in backend - this indicates improper AG-UI integration")
"""
            else:
                func_code = f"""
async def frontend_tool(**kwargs) -> str:
    \"\"\"Tool that will be executed by the frontend - this should never be called directly.\"\"\"
    raise RuntimeError(f"Frontend tool {agui_tool.name} was executed in backend - this indicates improper AG-UI integration")
"""

            local_vars = {'agui_tool': agui_tool}
            exec(func_code, globals(), local_vars)
            return local_vars['frontend_tool']

        frontend_tool = create_frontend_tool()

        frontend_tool.__name__ = agui_tool.name
        frontend_tool.__doc__ = agui_tool.description

        return tool(frontend_tool)

    def _convert_strands_to_agui_events(
        self,
        strands_event: Union[TypedEvent, Dict[str, Any]],
        execution_state: ExecutionState
    ) -> List[Event]:
        """Convert Strands events to AG-UI events."""
        events = []

        if isinstance(strands_event, dict):
            if 'event' in strands_event:
                event_data = strands_event['event']

                if 'messageStart' in event_data:
                    if not execution_state.current_message_id:
                        execution_state.current_message_id = str(uuid.uuid4())
                        events.append(TextMessageStartEvent(
                            message_id=execution_state.current_message_id,
                            role="assistant"
                        ))

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

                    # Emit args event only once when tool starts, with complete input
                    tool_input = tool_use.get('input', {})
                    events.append(ToolCallArgsEvent(
                        tool_call_id=tool_call_id,
                        delta=json.dumps(tool_input) if tool_input else '{}'
                    ))
                else:
                    # Update the input for existing tool, but don't emit args again
                    execution_state.pending_tools[tool_call_id]['input'] = tool_use.get('input', {})

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

                            # Emit tool args event with complete input
                            tool_input = tool_use.get('input', {})
                            events.append(ToolCallArgsEvent(
                                tool_call_id=tool_call_id,
                                delta=json.dumps(tool_input) if tool_input else '{}'
                            ))

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
        execution_state = ExecutionState(
            thread_id=input_data.thread_id,
            run_id=input_data.run_id,
            pending_tools={},
            tool_results={}
        )
        self.execution_states[f"{input_data.thread_id}:{input_data.run_id}"] = execution_state

        yield RunStartedEvent(
            thread_id=input_data.thread_id,
            run_id=input_data.run_id
        )

        try:
            if input_data.tools:
                self._register_agui_tools_with_strands(input_data.tools)

            has_tool_results = any(isinstance(msg, ToolMessage) for msg in input_data.messages)

            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Processing {len(input_data.messages)} messages, has_tool_results: {has_tool_results}")

            if has_tool_results:
                tool_results_info = []
                for msg in input_data.messages:
                    if isinstance(msg, ToolMessage):
                        tool_results_info.append({
                            'message': msg,
                            'tool_call_id': msg.tool_call_id,
                            'content': msg.content
                        })

                strands_messages = []
                for msg in input_data.messages:
                    if not isinstance(msg, ToolMessage) and not isinstance(msg, SystemMessage):
                        strands_msg = self._convert_agui_message_to_strands(msg)
                        strands_messages.append(strands_msg)

                has_existing_tooluse = False
                for msg in strands_messages:
                    if msg.get("role") == "assistant" and isinstance(msg.get("content"), list):
                        for content_item in msg["content"]:
                            if "toolUse" in content_item:
                                has_existing_tooluse = True
                                break
                        if has_existing_tooluse:
                            break

                if tool_results_info and (not has_existing_tooluse or len(strands_messages) == 0):
                    tool_use_content = []

                    for tool_info in tool_results_info:
                        tool_name = "execute_ppl_query"
                        if input_data.tools:
                            tool_name = input_data.tools[0].name

                        tool_use_content.append({
                            "toolUse": {
                                "toolUseId": tool_info['tool_call_id'],
                                "name": tool_name,
                                "input": {"query": "inferred_from_context"}
                            }
                        })

                    strands_messages.append({
                        "role": "assistant",
                        "content": tool_use_content
                    })

                if tool_results_info:
                    tool_result_content = []
                    for tool_info in tool_results_info:
                        tool_result_content.append({
                            "toolResult": {
                                "toolUseId": tool_info['tool_call_id'],
                                "content": [{"text": str(tool_info['content'])}]
                            }
                        })

                    strands_messages.append({
                        "role": "user",
                        "content": tool_result_content
                    })

                self.strands_agent.messages = strands_messages
                logger.debug(f"Reconstructed conversation with {len(strands_messages)} messages for Bedrock")
                async for strands_event in self.strands_agent.stream_async():
                    agui_events = self._convert_strands_to_agui_events(strands_event, execution_state)
                    for agui_event in agui_events:
                        yield agui_event

            else:
                strands_messages = []
                for msg in input_data.messages:
                    if not isinstance(msg, SystemMessage):
                        strands_msg = self._convert_agui_message_to_strands(msg)
                        strands_messages.append(strands_msg)

                self.strands_agent.messages = strands_messages
                user_message = None
                for msg in reversed(input_data.messages):
                    if isinstance(msg, UserMessage):
                        user_message = msg.content
                        break

                if user_message:
                    async for strands_event in self.strands_agent.stream_async(user_message):
                        agui_events = self._convert_strands_to_agui_events(strands_event, execution_state)

                        for agui_event in agui_events:
                            yield agui_event
                else:
                    # No user message found - let Strands handle the conversation without additional prompting
                    async for strands_event in self.strands_agent.stream_async():
                        agui_events = self._convert_strands_to_agui_events(strands_event, execution_state)

                        for agui_event in agui_events:
                            yield agui_event

            # Close any open text message
            if execution_state.current_message_id:
                yield TextMessageEndEvent(message_id=execution_state.current_message_id)

            # Always complete successfully - frontend tools are handled by frontend
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