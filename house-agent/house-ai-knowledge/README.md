# House AI Knowledge Pack

This folder contains the structured knowledge pack for the local house-agent project.

## Primary Reading Order
Future AI sessions and maintainers should start with:

1. `INDEX.md`
2. `00_overview.md`
3. `01_architecture.md`
4. `02_services.md`
5. `03_routes.md`
6. `04_tools.md`
7. `05_devices.md`
8. `06_data_sources.md`
9. `07_voice_audio.md`
10. `08_automation_rules.md`
11. `09_safety.md`
12. `10_deployment.md`
13. `11_known_issues.md`
14. `12_roadmap.md`
15. `ai_capabilities.md`
16. `ai_prompt_contract.md`

## Folder Roles

- root numbered files: canonical summaries
- topic folders: deeper supporting documentation
- `generated/`: machine-generated maps
- `agent/` and `policy/`: structured control and safety data
- `_snapshots/`: archival reference only

## Maintenance Rule
When the project changes:
- keep root numbered docs updated
- update topic docs where relevant
- keep generated maps in sync when possible
- avoid conflicting duplicate explanations



# House AI Knowledge Pack

Last updated: 2026-04-12

## What this is

This directory contains the working knowledge pack for the local House AI project.

It documents:

- current architecture
- services and routes
- devices and integrations
- policy and safety model
- roadmap direction
- operational notes
- validation status
- current project phase and priorities

This documentation exists so the project can keep moving without losing architectural clarity between sessions, refactors, and feature expansions.

## Project summary

The House AI project is a local-first home intelligence system built around:

- Ubuntu AI server
- RTX 3060
- Ollama
- Open WebUI
- Flask `house-agent`
- InfluxDB
- Loxone / Raspberry Pi / PLC integrations

The goal is to create a safe, useful house AI that can:

- understand house state
- summarize room activity
- analyze energy and environmental signals
- support announcements and room-aware voice behavior
- safely trigger approved automations through structured APIs

## Current status

The project is now beyond basic integration work.

It already has:

- safe execution architecture
- safe action routing direction
- room-aware audio foundation
- interpreted house state summaries
- room intelligence based on structured sensor interpretation
- compact house-query answers through `/agent/query`
- active roadmap and documentation structure

A recent important milestone was fixing query routing so room-state questions are no longer incorrectly intercepted by the safe-action router.

## Current phase

Current phase: **House Intelligence Layer Stabilization**

This phase is focused on:

- making room-state answers trustworthy
- improving explanation quality
- validating query routing behavior
- documenting the actual current system state
- preparing for the next evolution toward contextual house assistant behavior

## Where to start

Read these first:

1. `INDEX.md`
2. `services/00-current-project-state.md`
3. `services/01-phase-status.md`
4. `services/02-next-priorities.md`
5. `roadmap/00-roadmap-master.md`
6. `architecture/01-system-architecture.md`

## Important current docs

### Current-state and roadmap
- `services/00-current-project-state.md`
- `services/01-phase-status.md`
- `services/02-next-priorities.md`
- `roadmap/00-roadmap-master.md`

### Intelligence and routing
- `services/04-agent-and-routing.md`
- `services/22-room-intelligence-query-routing.md`
- `services/23-house-sensor-reasoning-model.md`
- `services/24-room-intelligence-validation-notes.md`

### Ops and validation
- `ops/15-validation-checklist.md`
- `ops/16-known-issues-watchlist.md`

### Architecture
- `architecture/01-system-architecture.md`

## Documentation structure

The knowledge pack is organized by concern.

Examples:

- `services/` for implementation behavior, current state, and service-level logic
- `architecture/` for system-level design
- `roadmap/` for strategic planning and next phases
- `ops/` for validation, watch items, and operations
- `devices/` for system/device integrations
- `voice/` for voice architecture
- `policy/` and `security/` for guardrails and execution policy

## Current implementation themes

The most important current implementation themes are:

- safe read vs safe action separation
- room intelligence derived from `/ai/house_sensors`
- routing of house-state questions through the intelligence path
- compact explainable summaries instead of raw dumps
- preserving a local-first and safety-first system design

## Design rule

The project should continue to follow this rule:

**Use structured safe APIs and explicit trigger functions, not direct uncontrolled automation access.**

That rule is central to the long-term success of the house assistant.

## Maintenance note

This knowledge pack should be updated whenever:

- a major feature lands
- routing behavior changes
- system architecture shifts
- validation reveals a new issue
- roadmap priorities change

Keeping these docs current is part of the project, not an optional extra.



