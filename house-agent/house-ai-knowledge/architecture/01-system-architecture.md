# System Architecture

Last updated: 2026-04-12

## High-level overview

The house AI system is a local-first orchestration platform designed to observe, summarize, and safely control selected parts of the house.

The architecture is intentionally layered so that:

- raw device integrations stay separated from AI-facing logic
- AI reads happen through structured safe interfaces
- AI actions happen only through controlled and approved pathways
- room intelligence is derived from structured sensor interpretation rather than direct uncontrolled tool use

## Core stack

Main components:

- Ubuntu AI server
- RTX 3060
- Ollama
- Open WebUI
- Flask `house-agent`
- InfluxDB
- Loxone / Raspberry Pi / PLC integrations
- auxiliary service nodes and audio/voice nodes

## Core architectural principle

The core principle is:

**The AI should not directly control the house. It should interact through safe, structured, intentionally designed APIs.**

That means:

- read paths are separate from write/control paths
- action execution is allowlisted and policy-aware
- future autonomy must stay bounded by the safe layer
- the intelligence layer is primarily interpretive first, then selectively actionable

## Main layers

## 1. Device and integration layer

This is the physical and service integration layer.

Examples include:

- Loxone sensors and controls
- Raspberry Pi nodes
- audio nodes and PiCore players
- UniFi/network collectors
- energy sources and device collectors
- InfluxDB-backed telemetry sources
- local bridge services like ElectricPi

This layer is noisy and device-specific. It should not be the layer exposed directly to AI reasoning.

## 2. Service normalization layer

This layer lives largely inside `house-agent/services/`.

Its job is to:

- collect device data
- normalize values
- expose reusable service logic
- convert raw source states into stable internal structures

Examples include:

- house state services
- house sensors services
- energy summary services
- audio services
- approval/auth services
- network/service health services

## 3. Safe read and safe execution layer

This is one of the most important architecture layers.

It provides:

- internal route execution for safe reads
- allowlisted safe actions
- approval-aware execution for sensitive operations
- policy documents and action registries

This layer ensures the AI can ask the system for trustworthy information and perform only bounded operations.

## 4. Intelligence and routing layer

This layer turns system state into useful answers.

Important components include:

- agent query handling
- routing between safe action requests and house-state questions
- room intelligence interpretation
- summary generation for house and room activity
- intent-like handling for observation questions

Recent work in this layer added:

- room activity reasoning enrichment
- ranked room intelligence
- query routing fix so room questions are not hijacked by safe-action matching

## 5. Voice and output layer

This layer handles:

- speech generation
- room/speaker targeting
- playback-aware handling
- announcements
- conversation/session-related voice flow

The architecture already supports room-aware output behavior and is designed to expand later toward multi-node spoken interaction.

## Core data flow patterns

## Read / observe flow

Typical observation flow:

1. user asks a house question
2. `/agent/query` receives the question
3. routing logic decides this is a house-state query, not an action query
4. general agent query path executes safe internal read routes
5. room/house intelligence is built from structured data
6. compact explanation is returned

Example routes involved:

- `/agent/query`
- `/ai/house_sensors`
- `/ai/house_state`

## Action / control flow

Typical action flow:

1. user asks for an allowed action
2. `/agent/query` or related action path recognizes action intent
3. safe action router checks allowlisted action handling
4. approval/auth policy is applied if needed
5. action is executed through the safe controlled layer
6. downstream device-specific services perform the actual change

This flow is intentionally more guarded than the read path.

## Room intelligence architecture

A major current architecture feature is the room intelligence layer.

It is built around structured sensor summaries and reasoning rather than raw state dumps.

Important functions currently include:

- `_summarize_house_sensors(...)`
- `_enrich_house_sensor_payload_with_activity_reasons(...)`
- `_build_ranked_room_intelligence(...)`
- `handle_house_or_ai_question(...)`

The room intelligence model supports:

- occupied / idle / active-no-presence / unknown classification
- room reasoning and confidence
- human activity scoring
- background automation identification
- ranked likely-used room lists

## Query routing architecture

A recent architectural correction was made in query routing.

Problem that existed:

- broad safe-action phrase matching could intercept room-state questions

Fix:

- room-state wording is now allowed to reach the intelligence layer rather than being incorrectly treated as safe-action status

This separation is architecture-critical because it preserves the boundary between:

- observation of the house
- action/state of controllable tools

## Audio architecture

The audio path is a major already-complete foundational subsystem.

Current direction:

AI / logic  
→ `house-agent` safe wrapper  
→ ElectricPi / bridge  
→ Loxone / relay / scene control  
→ voice/audio service  
→ PiCore player / room output  
→ playback monitor  
→ auto release/reset

Important design note:

Some room speakers, especially living room, are treated as controlled shared resources and must be released/reset after use so normal systems can continue using them.

## Documentation and knowledge architecture

The project also has a documentation architecture.

Knowledge is organized under:

- `house-ai-knowledge/services/`
- `house-ai-knowledge/architecture/`
- `house-ai-knowledge/roadmap/`
- `house-ai-knowledge/ops/`
- plus related categories for devices, policy, voice, automation, data, and agent behavior

This structure is meant to keep implementation and system understanding aligned.

## Current strengths of the architecture

The architecture is currently strongest in these areas:

- safe orchestration direction
- room-aware audio foundation
- structured room intelligence
- service modularity
- local-first control philosophy
- policy-driven action boundaries

## Current weak spots / active watch areas

Active weak spots or watch areas:

- UniFi collector rate-limit behavior
- continued tuning of transitional room reasoning
- long-term validation discipline to avoid route regressions
- documentation needing refresh after rapid implementation changes

## Future architecture direction

The next architectural evolution should build on the existing model rather than replacing it.

Likely next direction:

- richer contextual house briefings
- more integrated reasoning across state, schedule, and history
- further voice/room awareness
- later scheduling and household assistant layers
- eventually broader but still bounded safe AI assistance

## Architecture rule to preserve

The most important rule to preserve is:

**Never shortcut around the safe layer just because the AI could technically do so.**

That rule is what keeps the system maintainable, trustworthy, and scalable as it evolves.
