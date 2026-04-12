# Roadmap Master

Last updated: 2026-04-12

## Purpose

This is the top-level roadmap anchor for the house AI project.

It summarizes where the project is now, what major milestones are already complete, what the current phase is, and what comes next.

It should be read together with:

- `house-ai-knowledge/12_roadmap.md`
- `house-ai-knowledge/roadmap/07_next_phase_roadmap.md`
- `house-ai-knowledge/roadmap/15-ai-evolution-roadmap.md`
- `ROADMAP_VOICE.md`
- `house-ai-knowledge/automation/13-future-scheduling-roadmap.md`

## Project mission

Build a local-first, safe, room-aware house AI that can:

- understand house state
- summarize activity
- observe energy, device, and service conditions
- support voice and announcements
- interact with automations only through safe APIs and approval-aware mechanisms
- evolve toward a practical house butler experience

## Architectural direction

The architectural direction is now clear and should remain stable:

- local AI inference
- Flask `house-agent` as safe orchestration layer
- structured read routes for house state
- guarded action routes for control
- no unrestricted raw AI control over Loxone or house infrastructure
- documentation and policy files kept in sync with implementation

## What is already complete

### Foundation and infrastructure
Completed:

- local AI server foundation on Ubuntu with RTX 3060
- Ollama and Open WebUI integration direction established
- Flask `house-agent` as central orchestration service
- multiple local integrations across Loxone, Pi nodes, and device services

### Safe execution and action model
Completed:

- safe route execution model
- safe action allowlisting
- approval-aware execution groundwork
- policy and registry structure

### Audio and room output infrastructure
Completed:

- multi-room audio routing foundation
- safe speaker handling
- relay/playback-aware living-room behavior
- announcement and audio control groundwork

### Energy and house state understanding
Completed:

- interpreted house energy flow improvements
- energy summary integration into house state
- better human-readable house overview phrasing

### House sensor intelligence
Completed:

- `/ai/house_sensors` structured room intelligence path
- room occupancy and activity state summaries
- activity reason enrichment
- ranked room intelligence
- background automation classification
- routing fix for room-state queries through `/agent/query`

### Documentation base
Completed:

- substantial knowledge pack structure
- architecture repo sync workflow
- markdown knowledge inventory already present across services, architecture, devices, voice, policy, ops, and roadmap areas

## Current phase

Current phase: **House Intelligence Layer Stabilization**

Focus:

- improve room-level reasoning
- protect routing correctness
- document current state
- validate query behavior
- tune edge cases before broader expansion

## What is happening right now

Immediate current work:

- refresh and align documentation
- formalize validation notes and watch items
- stabilize room intelligence behavior
- prepare for next-step reasoning and assistant capabilities

## Next major milestone

Next major milestone:

**Transition from room-state intelligence to contextual house assistant behavior**

This means moving from:

- “What is happening in X?”
- “Which rooms are in use?”

toward:

- richer house briefings
- context-aware spoken summaries
- routine/scheduling support
- safer, more contextual automation recommendations
- later, selective action execution through the safe layer

## Near-term roadmap

### Stage 1: stabilize current intelligence layer
Tasks:

- complete docs refresh
- validate routing behavior
- tune transitional rooms
- refine confidence wording

### Stage 2: deepen house reasoning
Tasks:

- connect more house-state concepts together
- combine room intelligence with history and energy context
- produce richer summaries and explanations

### Stage 3: expand voice and room awareness
Tasks:

- continue voice-node architecture evolution
- keep room-aware output model
- later expand to more mic nodes and multi-node arbitration when needed

### Stage 4: scheduling and household assistance
Tasks:

- recurring chores
- reminders
- verification from house signals
- daily and weekly household intelligence

### Stage 5: broader house butler experience
Tasks:

- contextual briefings
- household storyline / narration features
- children/family interaction features
- safe orchestration across multiple house systems

## Strategic priorities that should remain fixed

These should remain constant regardless of feature growth:

1. safety over convenience
2. structured APIs over direct uncontrolled automation
3. local-first where practical
4. explainable summaries over opaque behavior
5. documentation kept current with implementation
6. modular services over tangled monolith logic

## What should not be compromised

The following should not be sacrificed as the system grows:

- safe action boundaries
- approval model for sensitive operations
- room/resource ownership rules such as shared speaker control
- maintainable documentation
- route clarity between read intelligence and control execution

## Roadmap confidence

Confidence in current direction: **high**

Reason:

The project has moved beyond raw experimentation and now has real architectural shape:

- safe control path
- room intelligence path
- audio infrastructure
- policy model
- validated recent fixes
- repo/doc structure to carry it forward

The next gains now come from disciplined refinement rather than architectural reinvention.
