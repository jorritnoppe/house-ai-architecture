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
