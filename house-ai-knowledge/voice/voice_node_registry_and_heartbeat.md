# Voice Node Registry and Heartbeat

## Purpose
Track configured house voice nodes separately from live heartbeat state, so spoken answers remain truthful.

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

## Current routing behavior
The interpreted `/ai/house_state` path now answers:
- which voice nodes are online
- which voice nodes are stale
- which voice nodes are offline
- registered voice nodes
- desk mic online questions

These now resolve through safe read routing instead of fallback model output.

## Current known configured node
- `deskmic`
- room: `deskroom`
- output target: `desk`

## Current validated runtime state on latest check
- configured nodes: 1
- heartbeat seen: 0
- online: 0
- stale: 0
- offline: 0
- unknown: 1

The validated spoken result at this moment is:
- `There are no voice nodes online. 1 registered voice nodes have not reported heartbeat yet.`

## Relevant files
- `house-agent/services/agent_router_bridge.py`
- `house-agent/services/voice_node_registry_service.py`
- `house-agent/services/house_state_service.py`

## Note
Routing truthfulness is now correct. The remaining issue is runtime heartbeat delivery from DeskPi, which should be debugged separately.
