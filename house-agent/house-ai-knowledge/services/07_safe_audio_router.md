# Safe Audio Router Service

## Purpose
Document the working safe-audio routing layer that intercepts natural-language music requests in `/agent/query` and routes them to safe actions instead of the fallback LLM or generic room lookup tools.

This service is now the stable path for:
- living room music start / stop / status
- bathroom music start / stop / status
- toilet / WC music start / stop / status
- party mode start / stop / status

## Main Components

### `routes/agent_routes.py`
This is the first gate for `/agent/query`.

It contains:
- `_normalize_safe_text(text)`
- `_has_words(text, words)`
- `_looks_like_safe_action_text(text)`
- `agent_query()`

Behavior:
1. Normalize incoming question text.
2. Detect whether the text looks like a safe audio action or safe audio status question.
3. If yes, send it to `route_ai_safe_action(...)`.
4. If the safe router returns a non-error result, return that directly.
5. Only fall back to `run_agent_query(question)` if no safe route matched.

This is important because earlier versions incorrectly fell through to:
- generic Loxone room lookup
- fallback model responses
- unrelated tool paths

### `services/ai_safe_action_router.py`
This is the natural-language matcher for safe audio requests.

It contains working handling for:
- action requests
- status questions
- room-specific status checks
- confirmation-required actions

Important helper functions:
- `_normalize(text)`
- `_contains_any(text, words)`
- `_has_words(text, words)`
- `_has_turn_on_pattern(text)`
- `_has_turn_off_pattern(text)`
- `_has_put_on_pattern(text)`
- `_has_put_off_pattern(text)`
- `_has_switch_on_pattern(text)`
- `_has_switch_off_pattern(text)`
- `_detect_room_key(text)`
- `_is_explicit_user_request(text)`
- `_is_start_request(text)`
- `_is_stop_request(text)`
- `_looks_like_music_or_audio_request(text)`
- `_is_global_status_question(text)`
- `_is_room_status_question(text)`
- `_match_action_name(text)`
- `_build_global_status_summary()`
- `_build_room_status_summary(text)`
- `route_ai_safe_action(text, confirmed=False)`

### `services/safe_action_service.py`
This is the execution layer.

It provides:
- safe action lookup from registry
- allowlist validation
- execution of steps
- runtime active-state tracking
- active action summary endpoints
- cleanup step execution on stop actions

Important behavior:
- `_start` actions mark runtime state active
- `_stop` actions mark paired `_start` action inactive
- stop actions may run `cleanup_steps`
- runtime state is persisted in `action_runtime_state.json`

## Stable Working Actions

### Living room
- `music_living_start`
- `music_living_stop`

Start flow:
1. verify living PiCore host is online
2. enable living route switch
3. press start scene

Stop flow:
1. press stop scene
2. cleanup: disable living route switch

### Bathroom
- `music_bathroom_start`
- `music_bathroom_stop`

Start flow:
1. verify bathroom PiCore host is online
2. press bathroom start scene

Stop flow:
1. press bathroom stop scene

### WC / Toilet
- `music_wc_start`
- `music_wc_stop`

Start flow:
1. verify toilet PiCore host is online
2. enable WC route switch
3. press WC start scene

Stop flow:
1. press WC stop scene
2. cleanup: disable WC route switch

### Party mode
- `music_party_start`
- `music_party_stop`

Start flow:
1. verify living PiCore host is online
2. verify bass/storageroom PiCore host is online
3. enable living route switch
4. enable storageroom route switch
5. press party start scene

Stop flow:
1. press party stop scene
2. cleanup: disable living route switch
3. cleanup: disable storageroom route switch

## Confirmation Rules
Party mode start is a confirmation-required action.

This means:
- request without confirmation should return confirmation required
- request with `"confirmed": true` should execute

## Status Tracking
Runtime endpoints now work and are important for debugging:

- `GET /tools/safe/state`
- `GET /tools/safe/active`
- `GET /tools/safe/status`

These expose:
- raw runtime state
- currently active safe actions
- summary status for active safe actions

## Natural Language Phrases Confirmed Working

### Living room
- `play some music in the living room`
- `is living room music on`
- `turn the living room music off`

### Bathroom
- `put music on in the bathroom`
- `is bathroom music on`
- `turn the bathroom music off`

### WC / Toilet
- `play music in the toilet`
- `is toilet music on`
- `turn the toilet music off`

### Party mode
- `start the party music`
- `is party mode on`
- `stop the party music`

## Important Fixes Made In This Iteration

### 1. Registry file corruption was found
At one point, `action_registry.json` accidentally contained Python code instead of JSON.
That caused:
- registry parse failure
- unknown action errors
- safe action routing failure

Fix:
- restore valid JSON in `house-ai-knowledge/policy/action_registry.json`

### 2. Runtime state endpoints were added
Safe runtime inspection endpoints were added and confirmed working:
- `/tools/safe/state`
- `/tools/safe/active`
- `/tools/safe/status`

### 3. Circular import mistakes occurred during development
A repeated failure mode was accidentally replacing router code with route blueprint code or creating self-import loops.

Fix:
- keep `services/ai_safe_action_router.py` strictly as router logic
- keep `routes/safe_action_routes.py` strictly as Flask route endpoints
- never import `safe_action_service` from itself

### 4. Status questions were separated from action requests
Earlier logic sometimes misread action requests as room-status questions.

Fix:
- `route_ai_safe_action(...)` now checks in this order:
  1. explicit action match
  2. global status question
  3. room status question
  4. no-match error

### 5. Bathroom phrasing needed stronger split-word handling
Earlier, phrases like:
- `put music on in the bathroom`
- `turn the bathroom music off`

sometimes fell through to fallback paths.

Fix:
- detect split action patterns:
  - turn + on
  - turn + off
  - put + on
  - put + off
  - switch + on
  - switch + off

## Operational Rule
Do not keep tweaking this router unless a real spoken or typed phrase fails.

The safe rule now is:
1. freeze working code
2. run regression script after edits
3. only add new phrase support when a real missed phrase appears

## Regression Script
A stable regression script was created:

`~/house-agent/test_safe_audio_router.sh`

This should be run after changes to:
- `routes/agent_routes.py`
- `services/ai_safe_action_router.py`
- `services/safe_action_service.py`
- action registry / runtime logic

## Result
The safe audio router is now working as intended and should be treated as the canonical path for house audio control requests through `/agent/query`.
