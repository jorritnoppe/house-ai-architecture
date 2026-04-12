# House Sensor Reasoning Update — 2026-04-12

## Summary

This update documents the new reasoning layer added around the live `house-agent` sensor interpretation flow.

Main goal:
improve room-state explanations so the agent can better distinguish between:

- real human occupancy
- likely recent human use
- access-triggered state changes
- climate/background automation noise
- the most relevant active room right now

## Runtime area affected

Live app file:

- `~/house-agent/services/agent_router_bridge.py`

Main logic added or expanded:

- `_analyze_room_activity_reason(...)`
- `_score_room_intelligence(...)`
- `_enrich_house_sensor_payload_with_activity_reasons(...)`
- `_build_ranked_room_intelligence(...)`
- `_filter_human_likely_rooms(...)`
- `_filter_background_like_rooms(...)`
- `_summarize_house_sensors(...)`

## Added room intelligence fields

The house sensor payload is now enriched with:

- `activity_reason`
- `activity_reason_primary`
- `activity_reason_secondary`
- `activity_reason_confidence`
- `human_activity_score`
- `occupancy_confidence`
- `automation_noise_likelihood`

## What this enables

The agent can now answer questions like:

- Which room is most active?
- Which rooms were recently used by a person?
- Which rooms are probably just background automation?
- Why is the kitchen active?
- What is happening in the living room?

## Observed validated outputs

Examples seen during validation:

- background automation:
  - living room
  - child room
  - IoT room
  - storage room
  - WC

- likely recent human activity:
  - attic room
  - bathroom
  - desk room
  - hallway

- most active room:
  - attic room
  - primary reason: presence

## Reasoning model

A room can look active for different reasons:

- presence
- motion
- access
- security
- lighting
- climate
- generic activity

The scoring layer tries to bias toward human evidence first and downgrade rooms that look more like climate churn or passive automation.

## Diagram

See:

- `diagrams/house_sensor_reasoning_layer.mmd`

## Next likely improvements

- add stronger recency decay for older transient room activity
- tune bathroom and hallway behavior
- reduce false positives from audio/music-related side effects
- add optional room-role weighting
- expose this reasoning layer visually in a dashboard later
