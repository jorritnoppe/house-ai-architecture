# 07_2 Safe Audio Aliases

## Purpose
This file documents the natural-language aliases currently recognized by the safe audio router.

It exists so future edits to `services/ai_safe_action_router.py` and `routes/agent_routes.py` can be made without guessing which phrases already work.

This file should be updated whenever:
- new room names are added
- new start/stop wording is supported
- new status queries are supported
- regression coverage is expanded

---

## Main components

### Router file
- `services/ai_safe_action_router.py`

### Agent route entry
- `routes/agent_routes.py`

### Runtime/state endpoints
- `/tools/safe/state`
- `/tools/safe/active`
- `/tools/safe/status`

### Regression script
- `~/house-agent/test_safe_audio_router.sh`

---

## Supported safe audio action names

### Living room
- `music_living_start`
- `music_living_stop`

### Bathroom
- `music_bathroom_start`
- `music_bathroom_stop`

### WC / toilet
- `music_wc_start`
- `music_wc_stop`
- `music_wc_night_start`

### Party mode
- `music_party_start`
- `music_party_stop`

---

## Room key mapping

### living
Recognized room aliases:
- `living room`
- `livingroom`
- `woonkamer`
- `downstairs`

Mapped start action:
- `music_living_start`

### bathroom
Recognized room aliases:
- `bathroom`
- `badkamer`
- `bath`

Mapped start action:
- `music_bathroom_start`

### wc
Recognized room aliases:
- `toilet`
- `wc`
- `wcroom`
- `toilet speaker`
- `wc speaker`

Mapped start action:
- `music_wc_start`

### party
Recognized room aliases:
- `party mode`
- `party music`
- `party`
- `feest`

Mapped start action:
- `music_party_start`

---

## Recognized start intent aliases

The router currently treats the following as start-style requests when combined with a valid room or party target:

- `start`
- `play`
- `enable`
- `switch on`
- `turn on`
- `put on`

Examples:
- `play some music in the living room`
- `put music on in the bathroom`
- `play music in the toilet`
- `start the party music`

---

## Recognized stop intent aliases

The router currently treats the following as stop-style requests when combined with a valid room or party target:

- `stop`
- `disable`
- `switch off`
- `turn off`
- `put off`

Examples:
- `turn the living room music off`
- `turn the bathroom music off`
- `turn the toilet music off`
- `stop the party music`

Note:
Natural-language phrases using split verbs like `turn ... off` or `put ... on` must remain supported even when words are not adjacent.

---

## Recognized audio keywords

These words help the router decide that a sentence is about safe audio instead of falling back to generic agent logic:

- `music`
- `audio`
- `party`
- `party mode`
- `party music`
- `scene`

---

## Recognized global status queries

These do not execute actions.
They inspect runtime state and report active safe audio actions.

Supported phrases include:
- `what is active`
- `what is running`
- `what music is playing`
- `what is playing`
- `is music playing`
- `status of music`
- `active actions`
- `what audio is active`

Expected behavior:
- if no safe audio actions are active, answer that none are active
- if one or more actions are active, list friendly names such as `Living room music`, `Bathroom music`, `WC music`, or `Party mode`

---

## Recognized room-specific status queries

These do not execute actions.
They inspect runtime state for the matching room start action.

### Living room examples
- `is living room music on`

Expected action check:
- `music_living_start`

### Bathroom examples
- `is bathroom music on`

Expected action check:
- `music_bathroom_start`

### WC examples
- `is toilet music on`

Expected action check:
- `music_wc_start`

### Party examples
- `is party mode on`

Expected action check:
- `music_party_start`

Expected behavior:
- if matching start action is active, answer `<friendly name> is active`
- if matching start action is not active, answer `<friendly name> is not active`

---

## Explicit request rule

Some actions are category-limited.

### cat1
`ai_can_use_when_needed`
These are safe to execute directly when matched.

### cat2
`ai_can_use_when_requested`
These require an explicit user request.
Current example:
- `music_wc_start`

This means status-style questions must not accidentally trigger WC start.
Only real request phrases should execute WC music start.

### cat3
`verification_required`
These require confirmation.
Current example:
- `music_party_start`

The route must only execute when:
- the phrase matches party start
- `confirmed=true` is present

---

## Confirmed working regression phrases

These were confirmed working in `test_safe_audio_router.sh`.

### Living
- `play some music in the living room`
- `is living room music on`
- `turn the living room music off`

### Bathroom
- `put music on in the bathroom`
- `is bathroom music on`
- `turn the bathroom music off`

### WC
- `play music in the toilet`
- `is toilet music on`
- `turn the toilet music off`

### Party
- `start the party music` with `confirmed=true`
- `is party mode on`
- `stop the party music`

---

## Runtime behavior expectations

### Start actions
A successful start action should:
- execute the configured safe action steps
- mark the matching `*_start` action as active in runtime state
- make the action visible through `/tools/safe/active`
- make the action visible through `/tools/safe/status`

### Stop actions
A successful stop action should:
- execute the stop action steps
- clear the matching `*_start` action active flag
- run cleanup steps if configured
- remove the action from `/tools/safe/active`
- remove the action from `/tools/safe/status`

### End of regression
After the full regression script finishes, expected state is:
- `/tools/safe/state` contains tracked actions with `active: false`
- `/tools/safe/active` returns empty active list
- `/tools/safe/status` returns empty active list

---

## Guardrails for future edits

Before changing alias logic:

1. update this file first with the new phrase you want to support
2. add the phrase to `test_safe_audio_router.sh`
3. then edit router logic
4. run compile checks
5. restart service
6. run the regression script
7. only keep the code change if all previous phrases still pass

---

## Known lesson from this work

The biggest failure mode was confusing:
- action requests
- room status checks
- generic model fallback

The safe fix is:
- first detect real action requests
- then detect global status questions
- then detect room status questions
- only fall back to normal agent logic when none of those match

This order should be preserved unless a future redesign replaces the current matching model.

---

## Current stable snapshot

At the time of this note, the following are true:
- `services/ai_safe_action_router.py` compiles
- `routes/agent_routes.py` compiles
- `services/safe_action_service.py` compiles
- `routes/safe_action_routes.py` compiles
- house-agent service starts successfully
- safe state endpoints respond successfully
- regression test passes for living, bathroom, toilet, and party flows

This file represents the stable alias snapshot for the safe audio router after that regression pass.
