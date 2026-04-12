# House AI Knowledge Index

## Purpose
This file tells future AI sessions and maintainers how to read and trust this knowledge pack.

The knowledge pack has multiple layers:
- canonical root summaries
- detailed topic documentation
- generated reference maps
- policy and agent control files
- archived snapshots

Future AI should follow the reading order below instead of treating all files as equally important.

---

## Reading Order

### 1. Start Here: Canonical Root Files
These are the primary overview files and should be treated as the main trusted summaries of the project:

1. `00_overview.md`
2. `01_architecture.md`
3. `02_services.md`
4. `03_routes.md`
5. `04_tools.md`
6. `05_devices.md`
7. `06_data_sources.md`
8. `07_voice_audio.md`
9. `08_automation_rules.md`
10. `09_safety.md`
11. `10_deployment.md`
12. `11_known_issues.md`
13. `12_roadmap.md`
14. `ai_capabilities.md`
15. `ai_prompt_contract.md`

These files are the preferred first source for project understanding.

---

## 2. Detailed Topic Folders
Use these when deeper detail is needed after reading the root files:

- `api/` for route and config detail
- `architecture/` for architecture-specific detail
- `devices/` for device-specific notes
- `services/` for service-specific notes
- `voice/` for audio/voice detail
- `automation/` for future automation direction
- `ops/` for operational notes
- `security/` for safety and guardrails
- `scheduling/` for scheduling ideas and backlog
- `roadmap/` for long-term roadmap detail
- `data/` for runtime state and data notes

These are supporting references, not the first-read layer.

---

## 3. Generated Files
The `generated/` folder contains machine-generated maps such as:
- route maps
- service maps
- tool maps

These are useful references but should not automatically override hand-written documentation.

Generated files may lag behind real code or lack operational nuance.

---

## 4. Agent and Policy Files
The `agent/` and `policy/` folders contain structured machine-readable control information.

Examples:
- allowlists
- blocked lists
- action policies
- tool registries
- intent maps

These files are important operational artifacts and should be treated as enforcement/support data rather than narrative documentation.

---

## 5. Snapshot Files
The `_snapshots/` folder contains historical captures such as:
- file lists
- project trees

These are archival references only and should not be treated as the current source of truth.

---

## Priority Rule for Future AI
When multiple files overlap, prefer this order:

1. current code behavior
2. root canonical numbered docs
3. detailed topic docs
4. policy/agent structured control files
5. generated maps
6. snapshots

If documentation conflicts with code, code wins and the docs should be updated.

---

## Maintenance Rule
When new features are added:
1. update the relevant code
2. update the relevant root numbered doc
3. update any detailed topic doc if needed
4. regenerate machine-generated maps if applicable
5. keep this index accurate

This keeps the knowledge pack usable for future AI retrieval.



# House AI Knowledge Index

Last updated: 2026-04-12

## Purpose

This index is the top-level navigation file for the `house-ai-knowledge` documentation set.

It is intended to help future work quickly locate:

- current project state
- architecture docs
- service and route docs
- roadmap files
- validation docs
- policy files
- device and voice information

## Start here

For the fastest current understanding, read these first:

1. `README.md`
2. `services/00-current-project-state.md`
3. `services/01-phase-status.md`
4. `services/02-next-priorities.md`
5. `roadmap/00-roadmap-master.md`
6. `architecture/01-system-architecture.md`

## Current-state and phase documents

- `services/00-current-project-state.md`
- `services/01-phase-status.md`
- `services/02-next-priorities.md`

These describe where the project stands right now and what should happen next.

## Architecture

- `architecture/01-system-architecture.md`
- `01_architecture.md`

These explain the high-level design and system structure.

## Core services and room intelligence

Key service-level docs:

- `services/04-agent-and-routing.md`
- `services/06-house-state-pipeline.md`
- `services/11_house_ai_current_status.md`
- `services/22-room-intelligence-query-routing.md`
- `services/23-house-sensor-reasoning-model.md`
- `services/24-room-intelligence-validation-notes.md`

These are the most important documents for the current intelligence-layer work.

## Operations and validation

- `ops/11-health-monitoring.md`
- `ops/14-repo-notes-and-exclusions.md`
- `ops/15-validation-checklist.md`
- `ops/16-known-issues-watchlist.md`

These cover operational and validation concerns.

## Roadmaps

Primary roadmap files:

- `roadmap/00-roadmap-master.md`
- `12_roadmap.md`
- `roadmap/07_next_phase_roadmap.md`
- `roadmap/15-ai-evolution-roadmap.md`
- `automation/13-future-scheduling-roadmap.md`

Also see project root:

- `../ROADMAP_VOICE.md`

## Devices, voice, and data

Important supporting docs:

- `devices/06-loxone-and-audio.md`
- `devices/07-energy-and-sensors.md`
- `voice/08-voice-system.md`
- `data/09-runtime-data-and-state.md`

## Policy and safety

Important safety/policy files:

- `policy/executor_policy.md`
- `policy/action_registry.json`
- `policy/safe_route_allowlist.json`
- `policy/safe_tool_allowlist.json`
- `security/12-safety-guardrails.md`
- `09_safety.md`

## Generated and support docs

Generated or support-oriented docs include:

- `generated/tool_map.md`
- `generated/tool_map.json`
- `services/17-generated-tool-map.md`

## Current most important implementation context

Recent important implementation areas include:

- room intelligence via `services/agent_router_bridge.py`
- query routing behavior via `routes/agent_routes.py`
- compact room-intelligence answer behavior
- safe separation between action queries and house-state queries

These are reflected in the new service and ops docs listed above.

## Documentation organization rule

New docs should be stored with their matching family:

- project/current-state and room-intelligence docs → `services/`
- validation and issue watch docs → `ops/`
- roadmap docs → `roadmap/`
- architecture updates → `architecture/`

Avoid creating parallel top-level doc folders unless there is a strong reason.
