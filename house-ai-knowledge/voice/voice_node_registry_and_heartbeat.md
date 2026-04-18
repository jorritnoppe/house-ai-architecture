# Voice Node Registry and Heartbeat

## Purpose
Track configured house voice nodes separately from live heartbeat state, while persisting live heartbeat data in SQLite so all Gunicorn workers see the same voice-node state.

## Implemented state model
Voice nodes can now be reported as:
- `online`
- `stale`
- `offline`
- `unknown`

## Meaning
- `online`: heartbeat seen within online freshness threshold
- `stale`: heartbeat exists but is older than online threshold
- `offline`: heartbeat is too old
- `unknown`: node is configured in registry but no heartbeat has been received yet

## Worker-sharing fix
The original live registry behavior kept heartbeat state in process memory.
That worked incorrectly under Gunicorn because each worker had its own isolated in-memory copy.

This is now fixed by persisting live heartbeat state in SQLite:
- heartbeat writes go into `data/voice_node_state.db`
- all Gunicorn workers read the same shared heartbeat state
- `/nodes/status` now stays truthful across multi-worker requests
- configured node metadata from `voice_nodes.json` is merged with live SQLite heartbeat state at read time

## Current routing behavior
The interpreted `/ai/house_state` path now answers:
- which voice nodes are online
- which voice nodes are stale
- which voice nodes are offline
- registered voice nodes
- desk mic online questions

These resolve through safe read routing instead of fallback model output.

## Current known configured node
- `deskmic`
- room: `deskroom`
- output target: `desk`

## Validated SQLite-backed runtime result
Validation confirmed:
- SQLite DB created successfully
- `voice_node_heartbeats` table exists
- repeated `/nodes/status` calls across Gunicorn workers return truthful shared state
- DeskPi heartbeat updates are visible through the shared DB-backed registry
- configured metadata and live heartbeat data merge correctly

## Latest validated runtime state
Latest validation showed:
- configured nodes: 1
- heartbeat seen: 1
- online: 1
- stale: 0
- offline: 0
- unknown: 0

Validated spoken/truthful interpretation now corresponds to:
- `The desk mic is online in the deskroom.`
- `There is 1 voice node online.`
- `The registered voice node deskmic has reported heartbeat and is online.`

## SQLite schema
Live heartbeat state is stored in:
- `data/voice_node_state.db`

Main table:
- `voice_node_heartbeats`

Stored fields include:
- `node_id`
- `room_id`
- `node_type`
- `ip`
- `version`
- `uptime_seconds`
- `first_seen`
- `last_seen`
- `updated_at`
- JSON blobs for capabilities, health, audio, mic, and errors

## Relevant files
- `house-agent/services/voice_node_state_store.py`
- `house-agent/services/voice_node_registry_service.py`
- `house-agent/routes/voice_node_routes.py`
- `house-agent/services/house_state_service.py`
- `house-agent/services/node_capability_service.py`
- `house-agent/house-ai-knowledge/devices/voice_nodes.json`

## Result
Voice-node heartbeat state is now truthful across Gunicorn workers.
The earlier worker-local memory issue is resolved.
Remaining future work is feature expansion, not worker-sharing repair.
