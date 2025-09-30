"""
AG-UI Protocol types and events for Strands Agent integration.

This module contains the core AG-UI types and events needed for the integration.
Based on the AG-UI Protocol Python SDK.
"""

from enum import Enum
from typing import Annotated, Any, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ConfiguredBaseModel(BaseModel):
    """A configurable base model."""
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        populate_by_name=True,
    )


class EventType(str, Enum):
    """The type of event."""
    TEXT_MESSAGE_START = "TEXT_MESSAGE_START"
    TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
    TEXT_MESSAGE_END = "TEXT_MESSAGE_END"
    TEXT_MESSAGE_CHUNK = "TEXT_MESSAGE_CHUNK"
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_ARGS = "TOOL_CALL_ARGS"
    TOOL_CALL_END = "TOOL_CALL_END"
    TOOL_CALL_CHUNK = "TOOL_CALL_CHUNK"
    TOOL_CALL_RESULT = "TOOL_CALL_RESULT"
    STATE_SNAPSHOT = "STATE_SNAPSHOT"
    STATE_DELTA = "STATE_DELTA"
    MESSAGES_SNAPSHOT = "MESSAGES_SNAPSHOT"
    RUN_STARTED = "RUN_STARTED"
    RUN_FINISHED = "RUN_FINISHED"
    RUN_ERROR = "RUN_ERROR"


class BaseEvent(ConfiguredBaseModel):
    """Base event for all events in the Agent User Interaction Protocol."""
    type: EventType
    timestamp: Optional[int] = None
    raw_event: Optional[Any] = None


class TextMessageStartEvent(BaseEvent):
    """Event indicating the start of a text message."""
    type: Literal[EventType.TEXT_MESSAGE_START] = EventType.TEXT_MESSAGE_START
    message_id: str
    role: Literal["assistant", "user", "system", "developer"] = "assistant"


class TextMessageContentEvent(BaseEvent):
    """Event containing a piece of text message content."""
    type: Literal[EventType.TEXT_MESSAGE_CONTENT] = EventType.TEXT_MESSAGE_CONTENT
    message_id: str
    delta: str = Field(min_length=1)


class TextMessageEndEvent(BaseEvent):
    """Event indicating the end of a text message."""
    type: Literal[EventType.TEXT_MESSAGE_END] = EventType.TEXT_MESSAGE_END
    message_id: str


class ToolCallStartEvent(BaseEvent):
    """Event indicating the start of a tool call."""
    type: Literal[EventType.TOOL_CALL_START] = EventType.TOOL_CALL_START
    tool_call_id: str
    tool_call_name: str
    parent_message_id: Optional[str] = None


class ToolCallArgsEvent(BaseEvent):
    """Event containing tool call arguments."""
    type: Literal[EventType.TOOL_CALL_ARGS] = EventType.TOOL_CALL_ARGS
    tool_call_id: str
    delta: str


class ToolCallEndEvent(BaseEvent):
    """Event indicating the end of a tool call."""
    type: Literal[EventType.TOOL_CALL_END] = EventType.TOOL_CALL_END
    tool_call_id: str


class ToolCallResultEvent(BaseEvent):
    """Event containing the result of a tool call."""
    type: Literal[EventType.TOOL_CALL_RESULT] = EventType.TOOL_CALL_RESULT
    message_id: str
    tool_call_id: str
    content: str
    role: Optional[Literal["tool"]] = "tool"


class RunStartedEvent(BaseEvent):
    """Event indicating that a run has started."""
    type: Literal[EventType.RUN_STARTED] = EventType.RUN_STARTED
    thread_id: str
    run_id: str


class RunFinishedEvent(BaseEvent):
    """Event indicating that a run has finished."""
    type: Literal[EventType.RUN_FINISHED] = EventType.RUN_FINISHED
    thread_id: str
    run_id: str
    result: Optional[Any] = None


class RunErrorEvent(BaseEvent):
    """Event indicating that a run has encountered an error."""
    type: Literal[EventType.RUN_ERROR] = EventType.RUN_ERROR
    message: str
    code: Optional[str] = None


# Union type for all events
Event = Annotated[
    Union[
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
    ],
    Field(discriminator="type")
]


# AG-UI Message Types
class FunctionCall(ConfiguredBaseModel):
    """Name and arguments of a function call."""
    name: str
    arguments: str


class ToolCall(ConfiguredBaseModel):
    """A tool call, modelled after OpenAI tool calls."""
    id: str
    type: Literal["function"] = "function"
    function: FunctionCall


class BaseMessage(ConfiguredBaseModel):
    """A base message, modelled after OpenAI messages."""
    id: str
    role: str
    content: Optional[str] = None
    name: Optional[str] = None


class UserMessage(BaseMessage):
    """A user message."""
    role: Literal["user"] = "user"
    content: str


class AssistantMessage(BaseMessage):
    """An assistant message."""
    role: Literal["assistant"] = "assistant"
    tool_calls: Optional[List[ToolCall]] = None


class ToolMessage(BaseMessage):
    """A tool result message."""
    role: Literal["tool"] = "tool"
    content: str
    tool_call_id: str
    error: Optional[str] = None


class SystemMessage(BaseMessage):
    """A system message."""
    role: Literal["system"] = "system"
    content: str


Message = Annotated[
    Union[UserMessage, AssistantMessage, ToolMessage, SystemMessage],
    Field(discriminator="role")
]


class Context(ConfiguredBaseModel):
    """Additional context for the agent."""
    description: str
    value: str


class Tool(ConfiguredBaseModel):
    """A tool definition."""
    name: str
    description: str
    parameters: Any  # JSON Schema for the tool parameters


class RunAgentInput(ConfiguredBaseModel):
    """Input for running an agent."""
    thread_id: str
    run_id: str
    state: Any
    messages: List[Message]
    tools: List[Tool]
    context: List[Context]
    forwarded_props: Any


# State can be any type
State = Any