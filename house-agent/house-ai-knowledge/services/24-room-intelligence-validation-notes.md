# Room Intelligence Validation Notes

Last updated: 2026-04-12

## Purpose

This document records current validation observations for room intelligence query behavior and answer quality.

It is intended as a practical checkpoint after the routing and compact-answer fixes.

## Validated route entry

Validated endpoint:

- `POST /agent/query`

Important note:

- `/agent/ask` was not present in the live route map during validation
- `/agent/query` is the correct currently available route for these checks

This explains the earlier 404 confusion during testing.

## Validation context

The main validation target was to confirm that room/house questions:

- no longer route into the safe-action status path by mistake
- return compact room intelligence summaries
- do not dump giant raw payloads in the normal user-facing answer

## Confirmed functional checks

### 1. Background automation query

Query:

- `Which rooms look like background automation?`

Observed answer pattern:

- compact list of lower-confidence/background-like rooms
- example output included rooms such as:
  - diningroom
  - kitchenroom
  - childroom
  - entranceroom
  - gardenroom
  - hallwayroom

Validation result:

- pass

Notes:

- output is concise
- output aligns with lower-confidence/background-oriented classification

### 2. Deskroom explanation query

Query:

- `Why is deskroom active?`

Observed answer pattern:

- deskroom currently appears occupied because presence is currently detected
- occupancy confidence high
- reasoning confidence high
- human activity score included

Validation result:

- pass

Notes:

- this is the desired explanation style
- it is compact but still explainable

### 3. Deskroom state query

Query:

- `What is active in deskroom?`

Observed answer pattern:

- same compact occupancy explanation rather than safe-action output

Validation result:

- pass

Notes:

- this is especially important because this wording previously collided with the safe-action router

### 4. Likely-used rooms query

Query:

- `Which rooms are likely being used?`

Observed answer pattern:

- ranked compact answer listing:
  - deskroom
  - livingroom
  - attickroom
  - bathroom

Validation result:

- pass

Notes:

- result matches observed presence-active rooms
- ranking appears reasonable

### 5. Livingroom state query

Query:

- `What is happening in livingroom?`

Observed answer pattern:

- livingroom currently appears occupied because presence is currently detected
- occupancy confidence high
- reasoning confidence high
- human activity score included

Validation result:

- pass

## Confirmed prior regression

A prior regression was clearly observed before the routing fix.

Problem behavior:

- query: `What is active in deskroom?`
- returned safe action information such as bathroom music status
- caused by overly broad safe-action phrase matching in `routes/agent_routes.py`

This regression is now considered resolved for the validated examples above.

## Validation findings about service/routes

### `/agent/ask` route issue
Observed:

- direct requests to `/agent/ask` returned 404

Confirmed by route map:

- `/agent/query` exists
- `/agent/ask` does not exist

Conclusion:

- validation and future docs should use `/agent/query` as the canonical endpoint unless a dedicated alias is intentionally added later

### Safe-action router still exists and is valid
Observed:

- safe-action routing still exists for relevant action-style prompts
- this is correct and expected

Conclusion:

- the goal was not to remove safe-action routing
- the goal was to prevent room-state prompts from being misclassified as action queries

## Practical interpretation of recent live behavior

The live outputs suggest the current model is behaving reasonably:

- deskroom and livingroom were correctly interpreted as occupied
- multiple rooms can appear recently active if the user moved around
- hallway/entrance-style rooms can show low-confidence transitional traces
- background automation classification is functioning and returning plausible candidates

The user specifically noted having gone downstairs recently, which explains why some room activity distribution may legitimately reflect recent movement.

## What still deserves more validation

### Transitional rooms
Need more checks on:

- entranceroom
- hallwayroom
- kitchenroom
- masterbedroom under access/security triggers

### Idle vs unknown behavior
Need more checks on:

- rooms with almost no sensor data
- whether `idle` and `unknown` are being used consistently

### Wording consistency
Need more checks on:

- whether "what is active in X" should always phrase as occupied/recently active
- whether low-confidence cases should explicitly say "recent activity without current presence"

### False-match routing protection
Need more checks on:

- action-like wording that still includes a room name
- music-specific room questions
- Dutch or mixed-language phrasing if those are common in practice

## Current validation conclusion

Current conclusion:

- the routing bug appears fixed for core tested examples
- room intelligence answers are now compact and relevant
- the system is in a good state for documentation refresh and broader validation
- transitional-room tuning remains a meaningful next refinement area
