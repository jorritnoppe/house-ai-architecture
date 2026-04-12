# Room Intelligence Query Routing

Last updated: 2026-04-12

## Purpose

This document explains how room-intelligence questions are routed through the system and how the recent routing bug was fixed.

The main concern is that house-state questions must reach the house intelligence path and must not be incorrectly intercepted by the safe-action router.

## Problem that existed

A routing bug existed in `routes/agent_routes.py`.

The `/agent/query` endpoint used a helper that tried to detect whether a user question looked like a safe action or safe action status query.

The heuristic was too broad and included phrases like:

- "what is active"
- "what is running"
- "active actions"

Because room-intelligence questions often use natural language such as:

- "What is active in deskroom?"
- "Why is deskroom active?"

those questions were sometimes incorrectly classified as safe-action-related instead of house-state-related.

## Bad behavior caused by the bug

When the bug occurred, the system could return answers about safe audio actions instead of room intelligence.

Example of wrong behavior:

- user asks: `What is active in deskroom?`
- safe-action router intercepts query
- system responds with active safe actions like bathroom music
- actual house sensor intelligence is skipped

This was especially confusing because the wording looked valid from a human perspective, but the routing heuristic interpreted it as action status rather than room state.

## Relevant route entry point

Main route:

- `routes/agent_routes.py`
- function: `agent_query()`

Important helper:

- `_looks_like_safe_action_text(text: str)`

Fallback intelligence path:

- `services.agent_query_service.run_agent_query(...)`
- which eventually reaches room/house intelligence logic

Relevant intelligence handler:

- `services/agent_router_bridge.py`
- `handle_house_or_ai_question(question: str)`

## Correct routing intent

The intended routing behavior is:

### Route to safe-action router when the question is really about actions

Examples:

- start bathroom music
- stop party mode
- turn on living room music
- is bathroom music on
- what music is playing
- active actions

These are action/control/state-of-safe-action requests.

### Route to house intelligence when the question is about room or house state

Examples:

- what is active in deskroom
- why is deskroom active
- what is happening in livingroom
- which rooms are likely being used
- which rooms look like background automation
- are lights on in bathroom
- why is entranceroom active

These are state/observation questions, not control questions.

## Fix that was applied

The routing fix narrowed the safe-action match behavior so that generic phrases like "what is active" do not automatically hijack room-state queries.

This allowed room-focused questions to fall through into the standard intelligence path instead of being consumed by the safe-action router.

After the fix, observed behavior became correct:

- room intelligence questions return room intelligence summaries
- safe audio questions still use the safe-action router
- normal `/agent/query` replies are compact and relevant

## Current routing flow

### 1. Request enters `/agent/query`

The endpoint receives a question payload.

### 2. Safe-action heuristic is checked

`_looks_like_safe_action_text(...)` evaluates whether the question should be treated as a safe-action-related request.

### 3. If strong safe-action match exists

The request is routed to:

- `route_ai_safe_action(...)`

This is appropriate for action queries and music control style questions.

### 4. Otherwise, fall back to general agent query

The request continues to:

- `run_agent_query(question)`

From there, house intelligence can process room/house state questions.

### 5. House intelligence path interprets the question

The intelligence layer can then:

- call safe internal read routes like `/ai/house_sensors`
- enrich room data
- rank likely activity
- produce compact summaries

## Why this separation matters

This separation matters because the system is built around safe architecture principles:

- action execution should remain deliberate and guarded
- observation queries should not be mistaken for action requests
- the user should get answers about the house itself, not the action registry, when asking room questions

A model that mixes those two too loosely becomes confusing and potentially unsafe.

## Current validated examples

Validated working examples include:

- `What is active in deskroom?`
- `Why is deskroom active?`
- `Which rooms are likely being used?`
- `Which rooms look like background automation?`
- `What is happening in livingroom?`

Observed compact outputs now correctly reference room occupancy/activity rather than safe-action state.

## Remaining routing risks

Even after the fix, these risk areas should be watched:

- future expansion of `_looks_like_safe_action_text(...)`
- adding broad status phrases without room-aware exclusions
- language variants or shorthand phrases
- mixed-intent user questions that mention both room state and action concepts

Examples of future edge cases to watch:

- what is active in the living room audio
- what is running in bathroom
- is the living room doing anything
- what is on downstairs

## Recommendation for future routing hardening

Future routing should increasingly rely on intent-aware logic rather than broad phrase matching.

Best direction:

- treat room names as a strong signal for house-state intent
- treat explicit verbs like start/stop/turn on/turn off as stronger action intent
- treat music/playback keywords as action/status intent only when not obviously about room-state explanation
- add regression examples to validation docs whenever routing rules change
