# Strands AG-UI Agent

A streamlined Strands Agent implementation with AG-UI Protocol support. Provides a single `/stream` endpoint that handles both regular conversations and tool result responses.

## Installation & Setup

```bash
cd src/strands-agui-agent
uv venv
source .venv/bin/activate
uv sync
```

## Quick Start

```bash
# Start the server
uv run strands-agui-agent serve --reload

# Server runs on http://localhost:8000/stream
```

## Sample Requests & Responses

### 1. Normal User Message

**Request:**
```bash
curl -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{
    "threadId": "thread-123",
    "runId": "run-456",
    "messages": [{"id": "1", "role": "user", "content": "Hello! How are you?"}],
    "tools": [],
    "state": {},
    "context": [],
    "forwardedProps": {}
  }'
```

**Response:**
```
data: {"type":"RUN_STARTED","threadId":"thread-123","runId":"run-456"}
data: {"type":"TEXT_MESSAGE_START","messageId":"xxx","role":"assistant"}
data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"xxx","delta":"I'm doing well, thank you for asking!"}
data: {"type":"TEXT_MESSAGE_END","messageId":"xxx"}
data: {"type":"RUN_FINISHED","threadId":"thread-123","runId":"run-456","result":{"status":"completed"}}
```

### 2. Tool Result Message

**Request:**
```bash
curl -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{
    "threadId": "thread-123",
    "runId": "run-789",
    "messages": [
      {
        "id": "tool-msg-1",
        "role": "tool",
        "content": "{\"success\":true,\"result\":\"Operation completed\"}",
        "toolCallId": "tool-call-123"
      }
    ],
    "tools": [],
    "state": {},
    "context": [],
    "forwardedProps": {}
  }'
```

**Response:**
```
data: {"type":"RUN_STARTED","threadId":"thread-123","runId":"run-789"}
data: {"type":"TEXT_MESSAGE_START","messageId":"yyy","role":"assistant"}
data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"yyy","delta":"Great! The operation completed successfully."}
data: {"type":"TEXT_MESSAGE_END","messageId":"yyy"}
data: {"type":"RUN_FINISHED","threadId":"thread-123","runId":"run-789","result":{"status":"completed"}}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Basic server information |
| `/stream` | POST | Stream AG-UI events for both regular messages and tool results |

The `/stream` endpoint handles:
- **User messages**: Regular conversation with Claude via Bedrock
- **Tool result messages**: Direct acknowledgment without Bedrock (avoids validation errors)

## Configuration

Configure via environment variables:

```bash
# Server settings
export HOST="0.0.0.0"
export PORT="8000"
export LOG_LEVEL="info"
export RELOAD="false"
export WORKERS="1"

# Agent settings
export AGENT_NAME="Strands AG-UI Agent"
export MODEL_ID="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
export TEMPERATURE="0.7"
export STREAMING="true"
export MAX_TOKENS=""  # Optional
```
