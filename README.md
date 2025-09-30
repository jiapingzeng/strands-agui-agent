# Strands AG-UI Agent

A Strands Agent implementation with AG-UI Protocol support for frontend tool execution.

## Installation & Setup

```bash
cd strands-agui-agent
uv venv
source .venv/bin/activate
uv sync
```

## Quick Start

```bash
# Option 1: Using CLI (recommended)
uv run strands-agui-agent serve

# Option 2: Direct module execution
uv run python -m strands_agui_agent.server

# Server runs on http://localhost:8000
```

## Sample Request & Response

**Request:**
```bash
curl -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "threadId": "test-123",
    "runId": "run-456",
    "messages": [{"id": "1", "role": "user", "content": "Calculate 25 * 8"}],
    "tools": [
      {
        "name": "calculator",
        "description": "Perform calculations",
        "parameters": {
          "type": "object",
          "properties": {
            "expression": {"type": "string"}
          },
          "required": ["expression"]
        }
      }
    ],
    "state": {},
    "context": [],
    "forwardedProps": {}
  }'
```

**Response:**
```
data: {"type":"RUN_STARTED","threadId":"test-123","runId":"run-456"}
data: {"type":"TEXT_MESSAGE_START","messageId":"xxx","role":"assistant"}
data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"xxx","delta":"I'll calculate that for you."}
data: {"type":"TOOL_CALL_START","toolCallId":"yyy","toolCallName":"calculator"}
data: {"type":"TOOL_CALL_ARGS","toolCallId":"yyy","delta":"{\"expression\":\"25 * 8\"}"}
data: {"type":"TOOL_CALL_END","toolCallId":"yyy"}
data: {"type":"TEXT_MESSAGE_END","messageId":"xxx"}
data: {"type":"RUN_FINISHED","threadId":"test-123","runId":"run-456","result":{"status":"waiting_for_tools","tool_calls":[{"id":"yyy","name":"calculator"}]}}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stream` | POST | Start streaming execution with AG-UI events |
| `/tool-results` | POST | Submit tool execution results |
| `/continue` | POST | Continue execution after tool results |
| `/execution-state/{thread_id}/{run_id}` | GET | Get execution state |
| `/health` | GET | Health check |
| `/tools` | GET | Get available tools |

## Configuration

Set environment variables:
```bash
export HOST="0.0.0.0"
export PORT="8000"
export MODEL_ID="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
```

## License

MIT