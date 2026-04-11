# 07 - Loxone WebSocket Unified Integration

## Summary
The Loxone WebSocket connection has been unified into the main `house-agent.service` process.

Previously:
- Separate service: `house-agent-loxone-ws.service`
- Duplicate websocket connections
- Conflicting cache/state behavior

Now:
- Single websocket connection inside Flask app
- Controlled via environment variable
- Shared cache used across all services

## Key File
services/loxone_ws_service.py

## Activation
Controlled by:
ENV: HOUSE_AGENT_RUN_LOXONE_WS=1

## Behavior
- Starts background thread on app startup
- Connects to:
  ws://<LOXONE_HOST>/ws/rfc6455
- Stores live values in:
  LOXONE_STATE_CACHE

## Result
- Stable real-time updates
- ~600+ state values cached
- Used for:
  - telemetry
  - presence
  - NFC approval signals

## Important Decision
DO NOT use separate websocket service anymore.
All logic runs inside main house-agent.
