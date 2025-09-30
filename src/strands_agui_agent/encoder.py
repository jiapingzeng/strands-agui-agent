"""
AG-UI Event Encoder.

This module provides event encoding functionality for AG-UI protocol compatibility.
"""

from .agui_types import BaseEvent

AGUI_MEDIA_TYPE = "application/vnd.ag-ui.event+proto"


class EventEncoder:
    """
    Encodes Agent User Interaction events for transmission.
    """

    def __init__(self, accept: str = None):
        """
        Initialize the event encoder.

        Args:
            accept: Accept header content type (optional)
        """
        self.accept = accept

    def get_content_type(self) -> str:
        """
        Returns the content type of the encoder.

        Returns:
            Content type string for server-sent events
        """
        return "text/event-stream"

    def encode(self, event: BaseEvent) -> str:
        """
        Encodes an event for transmission.

        Args:
            event: The AG-UI event to encode

        Returns:
            Encoded event string
        """
        return self._encode_sse(event)

    def _encode_sse(self, event: BaseEvent) -> str:
        """
        Encodes an event into Server-Sent Events format.

        Args:
            event: The event to encode

        Returns:
            SSE formatted string
        """
        # Convert to JSON with camelCase keys and exclude None values
        json_data = event.model_dump_json(by_alias=True, exclude_none=True)
        return f"data: {json_data}\n\n"