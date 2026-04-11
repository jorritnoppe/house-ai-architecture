# Safe Audio Query Routing

## Goal
Ensure that natural-language audio control requests sent to `/agent/query` are intercepted early and routed to safe house actions, instead of reaching generic house queries or fallback LLM responses.

## Current Routing Model

### Entry point
`POST /agent/query`

Handled by:
- `routes/agent_routes.py`

### Routing decision
`agent_query()` first evaluates:

- `_looks_like_safe_action_text(question)`

If this returns `True`, then:
- `route_ai_safe_action(text=question, confirmed=confirmed)` is called

If the safe router returns a non-error result:
- response mode is `safe_action_router`
- the request does not fall through to generic agent tooling

If the safe router returns error:
- request falls back to `run_agent_query(question)`

## Why This Exists
Without this interception layer, natural-language requests such as:
- start music in living room
- turn the bathroom music off
- is party mode on

may incorrectly route to:
- Loxone room listing tools
- generic house Q&A
- fallback model responses

This was a real failure mode during development.

## Safe Match Detection Rules
`_looks_like_safe_action_text(...)` should return true for:

### Action phrasing
Examples:
- start music in living room
- play some music in the living room
- turn the living room music off
- put music on in the bathroom
- play music in the toilet
- stop the party music

### Status phrasing
Examples:
- what music is playing
- is music playing
- is living room music on
- is bathroom music on
- is toilet music on
- is party mode on
- what is active
- active actions

## Important Detection Rule
Safe audio detection should be broad enough to catch natural language, but not so broad that unrelated questions get hijacked.

Current practical rule:
- status phrases are always safe-routed
- action phrases require action wording plus music/audio/party intent plus room or mode context

## Router Order
Inside `route_ai_safe_action(...)`, the correct order is:

1. explicit action match
2. global status question
3. room status question
4. return error if unmatched

This order matters.

If room status is checked before explicit action matching, phrases like:
- put music on in the bathroom

can be misread as status checks instead of start actions.

## Confirmed Working Query Families

### Living
- play some music in the living room
- is living room music on
- turn the living room music off

### Bathroom
- put music on in the bathroom
- is bathroom music on
- turn the bathroom music off

### Toilet / WC
- play music in the toilet
- is toilet music on
- turn the toilet music off

### Party
- start the party music
- is party mode on
- stop the party music

## Confirmed Working Response Pattern
When safe-routed successfully, response shape should look like:

- `mode: "safe_action_router"`
- `route_guard: "agent_query_safe_action_debug"`
- `answer: <human summary>`
- `safe_action: <router result>`

This makes safe-route behavior obvious during curl testing.

## Runtime State Integration
Status requests are backed by runtime safe-action state, not by audio sensing.

This means:
- the agent does not listen to real music output
- it reports whether safe audio actions are marked active in runtime state

Example:
- if `music_living_start` is active, then `is living room music on` returns active

## Known Limits
This router only knows what was started and stopped through safe actions.

It does not automatically know about:
- manual changes made outside the safe action path
- LMS actions triggered elsewhere
- direct Loxone scene triggers outside this route
- real acoustic verification

## Guidance For Future Changes
When extending the router:
1. add phrases only after real misses
2. prefer helper functions over one-off conditions
3. do not move Flask route code into service files
4. do not import a service into itself
5. always rerun the regression script after edits

## Regression Script
Use:
`~/house-agent/test_safe_audio_router.sh`

This is now the baseline smoke test for safe audio routing.
