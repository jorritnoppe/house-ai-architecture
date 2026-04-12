# Current Project State

Last updated: 2026-04-12

## Project summary

This project is a local house AI platform running on an Ubuntu AI server with an RTX 3060 and centered around:

- Ollama for local LLM inference
- Open WebUI for user interaction
- Flask-based `house-agent` as the main safe orchestration layer
- InfluxDB for time-series and operational data
- Loxone, Raspberry Pi nodes, PLC-connected devices, and related local integrations

The system goal is not just home automation, but a safe house intelligence layer that can:

- observe the home state
- summarize current activity
- trigger only approved/safe actions
- evolve toward room-aware voice interaction, scheduling, and contextual household assistance

## Current architecture state

The architecture is now strongly centered around a safe execution model:

- user and AI requests are routed through `house-agent`
- reads are performed through safe internal routes
- actions are routed through a guarded safe-action layer
- no broad direct AI-to-Loxone control is intended
- room-aware summaries are derived from structured house sensor data rather than raw signal dumps

Core pieces currently in place:

- safe execution layer
- route-driven house state and house sensors aggregation
- room-level activity interpretation
- safe audio and speaker routing foundation
- approval and NFC-related approval flow groundwork
- voice-node and playback-aware infrastructure
- knowledge pack / markdown documentation repo structure
- sanitized GitHub architecture repo

## Major completed milestones

### 1. Safe action and execution foundation

The system has moved away from uncontrolled automation patterns and now prefers:

- safe allowlisted internal route execution
- safe allowlisted action execution
- approval-aware execution for sensitive actions
- explicit action registry / policy documents

This is the core design principle that enables future AI control without giving unrestricted authority to the model.

### 2. Stable multi-room audio control foundation

A major foundation has already been built for room-aware audio control:

- speaker routing by room
- Loxone/ElectricPi bridge-based execution
- playback-aware speaker release/reset
- living-room special handling as a controlled shared resource
- groundwork for later announcements, storytelling, and room-specific voice output

This remains one of the most important completed infrastructure layers.

### 3. House state pipeline cleanup

The house state pipeline was improved so that energy summaries now rely on interpreted energy flow rather than awkward raw signed values.

This improved:

- readability of summaries
- house import/export phrasing
- solar and house load understanding
- consistency between internal data and human-readable AI explanations

### 4. Unified house sensor intelligence path

A major recent milestone is the room intelligence layer built around `/ai/house_sensors` and `services/agent_router_bridge.py`.

This now includes:

- occupancy / idle / active-no-presence / unknown room classification
- room-level reasoning summaries
- prioritization of stronger human signals
- room ranking by likely usage
- background-automation detection
- room-specific explanation queries

The core functions identified in the current implementation include:

- `_summarize_house_sensors(...)`
- `handle_house_or_ai_question(...)`
- `_enrich_house_sensor_payload_with_activity_reasons(...)`
- `_build_ranked_room_intelligence(...)`

### 5. Query routing fix for house questions

A major bug was recently fixed in query routing.

Previously, broad text like:

- "What is active in deskroom?"
- "Why is deskroom active?"

could be incorrectly intercepted by the safe-action music/action router because phrases like "what is active" matched generic action-status wording.

This produced incorrect answers such as safe audio status instead of room intelligence.

This was corrected by tightening routing in `routes/agent_routes.py`, so room-state questions now fall through to the proper house intelligence path rather than being hijacked by safe action routing.

### 6. Compact room intelligence answers

Recent work also improved result formatting so responses now return compact intelligence summaries instead of dumping massive raw payloads in normal query responses.

Examples now work as intended:

- "What is active in deskroom?"
- "Why is deskroom active?"
- "Which rooms are likely being used?"
- "Which rooms look like background automation?"
- "What is happening in livingroom?"

## What is working well right now

### House room intelligence

Working well:

- room activity interpretation
- room occupancy identification
- likely human activity ranking
- background automation classification
- room-specific explanation summaries

Example behavior currently observed:

- `deskroom` correctly reported as occupied via presence
- `livingroom` correctly reported as occupied via presence
- "likely being used" queries return ranked occupied rooms
- "background automation" queries return lower-confidence/system-behavior rooms

### Safe routing direction

Working well:

- direct safe-action queries still have their own route
- house intelligence queries can now bypass false action matching
- compact structured answers are returned rather than giant dumps in normal paths

### Repo and architecture sync

Working well:

- `house-agent` live code is being synced into `house-ai-architecture`
- recent commits have been pushed
- repo state appears clean after sync
- important room-intelligence routing fixes are present in local live code
- latest pushed commit relevant to route fix:
  - `457f282 Fix house query routing and compact room intelligence answers`

## Known limitations right now

### 1. Presence can still reflect recent movement elsewhere

If the user recently moved through the house, occupied room results can legitimately reflect recent detected presence in multiple rooms.

This is not necessarily a bug. It is expected for:

- transitional movement
- lingering presence hold times
- simultaneous recent occupancy in multiple rooms

### 2. Transitional rooms still need tuning

Rooms like:

- entranceroom
- hallwayroom
- kitchenroom in certain cases

may still appear in activity/background classifications due to:

- access triggers
- decaying presence memory
- transitional sensor behavior

The current model already handles this better than before, but further tuning is still warranted.

### 3. UniFi collector rate-limit issue

Observed in logs:

- UniFi refresh/login can hit HTTP 429 rate limits

This does not block room intelligence itself, but it is an active operational issue that should be tracked and hardened.

### 4. Validation/doc structure still catching up

The implementation has moved faster than the documentation in some areas. The knowledge pack exists and is substantial, but some project-state and validation docs need to be refreshed to reflect the latest room intelligence work and roadmap state.

## Current development posture

The project is in a strong infrastructure-plus-intelligence phase.

You are no longer building only raw integrations. You now have enough safe plumbing to begin shaping real house reasoning behavior.

Current emphasis is:

- better interpretation of sensor state
- safer routing between read-style questions and action-style questions
- cleaner summaries
- documentation consolidation
- roadmap alignment before the next major expansion

## Near-term direction

The immediate next direction should be:

- finish documentation refresh
- validate room intelligence behavior across more real-life examples
- tune transitional-room decay and background-vs-human classification
- keep safe execution boundaries strict
- then proceed toward richer house reasoning and later context-aware scheduling/voice evolution
