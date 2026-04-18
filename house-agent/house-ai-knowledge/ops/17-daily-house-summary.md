# Daily House Summary Flow

Last updated: 2026-04-18

## Purpose

This document explains the new unified daily house summary / house briefing flow.

It is the current preferred path for natural questions like:
- `give me the house briefing`
- `daily house summary`
- `summarize current house status`
- `give me a house summary`

## Why this was added

Older house-summary behavior could fall into stale or overly technical paths:
- raw energy summary dump
- disabled or missing `house_overview` route
- less natural output for spoken agent usage

The new daily house summary flow provides:
- cleaner spoken summary
- energy + climate + activity + infrastructure in one payload
- safe-read behavior through the existing executor model

## Main components

### 1. Data builder
File:
- `services/house_state_service.py`

Key function:
- `get_daily_house_summary()`

This function builds a compact summary from:
- `get_house_state()`
- energy flow
- climate summary
- occupancy/activity summary
- infrastructure summary
- crypto total value

It returns a payload containing:
- `energy`
- `activity`
- `climate`
- `infrastructure`
- `telemetry`
- `crypto`
- `spoken_summary`
- `generated_at`

### 2. Route
File:
- `routes/house_state_routes.py`

Route:
- `GET /ai/daily_house_summary`

Purpose:
- direct API access to the compact house summary

### 3. Internal executor
File:
- `services/internal_route_executor.py`

Path added:
- `/ai/daily_house_summary`

Purpose:
- allows safe executor to call the new route internally

### 4. Safe route policy
File:
- `house-ai-knowledge/policy/safe_route_allowlist.json`

Added safe route:
- `/ai/daily_house_summary`

Purpose:
- allows autonomous read-only execution through the safe action path

### 5. Agent routing
File:
- `services/agent_router_bridge.py`

Natural phrases routed to `/ai/daily_house_summary` include:
- `daily house summary`
- `house briefing`
- `daily briefing`
- `morning house briefing`
- `morning house summary`
- `summarize the house`
- `summarize current house status`
- `current house status`
- `house status`
- `house summary`
- `give me the house briefing`
- `give me a house briefing`
- `give me a house summary`
- `give me the house summary`

### 6. Spoken answer rendering
File:
- `services/agent_router_bridge.py`

Behavior:
- if target is `/ai/daily_house_summary`
- the agent returns `spoken_summary`

This keeps the answer short, natural, and suitable for:
- voice output
- dashboard summaries
- quick operational checks

## Current validated behavior

Validated live:
- `/ai/daily_house_summary` direct route works
- `give me the house briefing` works
- `daily house summary` works
- `summarize current house status` works
- `give me a house summary` works

Example output shape:
- estimated house load
- solar production
- grid import/export state
- likely occupied rooms
- climate range
- service/offline warnings
- quiet/playback state

## Current design note

This flow is now the preferred natural-language summary path.

The old `house_overview`-based approach should be treated as legacy and gradually removed or replaced.

## Next planned expansion

Later this daily summary can be merged with:
- agenda summary
- reminders/tasks
- household planning
- anomaly detection notes
- optional crypto highlights
- spoken morning narrative

That would become the full morning butler briefing layer.



## Related extension: waste pickup awareness

The house summary stack now has a working waste schedule source via Google Calendar.

Current behavior:
- Google Calendar auth was repaired
- the waste schedule service can parse pickup events from the personal calendar source
- normalized waste types currently include paper, PMD, GFT, rest waste, and glass

Current spoken outputs:
- `spoken_next`
- `spoken_tomorrow`

Validated example:
- `The next pickup is paper on Tuesday.`

Next intended integration:
- add tomorrow waste pickup notice into evening summary
- optionally add next pickup note into morning briefing
