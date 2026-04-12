# House Sensor Reasoning Model

Last updated: 2026-04-12

## Purpose

This document describes the current reasoning model used to interpret structured house sensor data into room intelligence.

The model is not a raw sensor dump. It is an interpretation layer that tries to answer:

- is a room occupied?
- is there likely human activity?
- is the room merely showing background system behavior?
- why is the room considered active or idle?

## Main implementation points

Core functions currently identified in `services/agent_router_bridge.py`:

- `_summarize_house_sensors(...)`
- `_enrich_house_sensor_payload_with_activity_reasons(...)`
- `_build_ranked_room_intelligence(...)`
- `handle_house_or_ai_question(...)`

These functions sit on top of structured data from:

- `/ai/house_sensors`

## Input model

The reasoning model works from structured room entries that include fields such as:

- room name
- room role
- room status
- presence state
- motion state
- lighting state
- climate data
- access/security data
- signal ages
- decay factors
- occupancy confidence
- human activity score
- activity reason fields

The model uses both current states and recency/decay concepts.

## Core room classifications

The current model uses room-level states such as:

- `occupied`
- `idle`
- `active_no_presence`
- `unknown`

### Occupied
Used when strong evidence suggests actual ongoing human presence.

Typical indicators:

- presence currently active
- strong recent occupancy-related signals
- high human activity score
- high or medium occupancy confidence

### Idle
Used when no strong human activity is currently inferred.

Typical indicators:

- no current presence
- no meaningful active motion
- no strong access or usage signals
- mostly background or stale state

### Active without presence
Used when the room has recent activity-like signals but lacks strong ongoing presence proof.

Typical indicators:

- access event
- status/event changes
- some recent binary activity
- but no current presence signal

This is important because some rooms can be recently touched or triggered without being genuinely occupied.

### Unknown
Used when the system lacks enough room data to make a real judgment.

## Signal priority philosophy

The model prioritizes stronger human evidence over weaker automation evidence.

General priority order:

1. presence
2. meaningful motion or human-linked activity
3. recent access-related triggers
4. climate/system/background behaviors
5. lack of evidence

This is a heuristic model, not a perfect occupancy truth engine.

## Activity reason fields

The enriched room model now includes explanation fields such as:

- `activity_reason`
- `activity_reason_primary`
- `activity_reason_secondary`
- `activity_reason_confidence`
- `human_activity_score`
- `automation_noise_likelihood`

These exist so the AI can explain not just the classification, but the likely reason behind it.

## Common primary reasons

### `presence_detected`
Meaning:

- presence is currently detected
- strongest current occupancy signal
- high-confidence explanation path

Typical answer form:

- room currently appears occupied because presence is currently detected

### `access_triggered`
Meaning:

- there was a recent access-related trigger
- access alone is not strong proof of ongoing presence

This is useful for entrances, NFC/code touch points, and brief passage behavior.

### `background_automation`
Meaning:

- the room has climate or passive system activity
- signals look more like background behavior than direct human occupancy

This is useful for rooms where climate values exist but no true occupancy evidence is present.

### `idle`
Meaning:

- no strong activity signals are currently active

## Room roles and behavior shaping

The model is room-role aware.

Examples of room roles seen in current data:

- desk
- living
- bathroom
- bedroom
- attic
- kitchen
- transitional
- utility
- general

### Why room roles matter

A transitional room should not be interpreted the same way as a deskroom or livingroom.

Examples:

- `entranceroom` and `hallwayroom` should decay faster
- utility rooms may show equipment/system activity without human use
- living and desk spaces can tolerate stronger occupancy interpretation
- bedrooms may carry access/security-related activity that should not overstate occupancy

## Decay and recency concepts

The model uses aging concepts rather than treating every recent event equally forever.

Related fields include:

- `presence_age_seconds`
- `motion_age_seconds`
- `access_age_seconds`
- `climate_age_seconds`
- decay factors
- `recency_band`

Common recency ideas include:

- fresh
- aging
- unknown

This allows the system to distinguish:

- currently occupied
- recently passed through
- stale/low-confidence residual activity

## Human activity score

The `human_activity_score` gives a rough normalized interpretation of how human-driven the room state appears.

This is not a direct truth value. It is a heuristic signal intended to support summaries and ranking.

Interpretation guideline:

- high score: likely human activity
- medium score: mixed evidence
- low score: weak or non-human evidence

## Automation noise likelihood

The model also carries an `automation_noise_likelihood` field.

This helps identify rooms that may be:

- reporting system state
- climate values
- device status
- weak/stale transitions

rather than genuine human use.

This is especially useful for “Which rooms look like background automation?” queries.

## Ranked room intelligence

The reasoning model is not only room-by-room. It also ranks rooms against each other.

This enables answers like:

- which rooms are likely being used
- which rooms look like background automation

The ranking appears to prefer:

- strong presence + high activity score for likely-used rooms
- low-confidence/background/system-like patterns for automation-style rooms

## Example current behavior

Observed good behavior:

- `deskroom` reported occupied due to presence detection
- `livingroom` reported occupied due to presence detection
- occupied room answers include confidence and human activity score
- lower-confidence spaces like `entranceroom` and `kitchenroom` can be described via access-triggered logic instead of full occupancy

## Model limitations

This model is still heuristic and not a perfect occupancy engine.

Known limitations:

- recent movement across multiple rooms can keep several rooms looking active
- transitional rooms may still need sharper decay tuning
- some access/security/status signals may over-contribute in specific rooms
- no full multi-sensor temporal sequence model exists yet
- no personal identity layer is assumed in these summaries

## Design principle

The reasoning model is deliberately conservative:

- strong occupancy claims should be tied to presence-like evidence
- weaker evidence should be phrased as recent activity, access trigger, or background automation
- answers should remain explainable

This design is much safer and more trustworthy than simply treating any recent event as proof of human presence.
