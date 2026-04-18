# Known Issues Watchlist

Last updated: 2026-04-18

## Purpose

This file tracks currently known implementation, routing, and operational issues that should remain visible during stabilization.

## Active watch items

### 1. House overview legacy path still exists in older tool flow
Status: active but neutralized

Symptoms:
- older house overview handling still exists in `services/agent_house.py`
- historical behavior attempted to use `/ai/house_overview`, which currently returns 404
- this used to produce degraded or misleading house status output

Current mitigation:
- stale `house_overview` response block was disabled
- natural house summary prompts are now routed to `/ai/daily_house_summary`

Desired end state:
- fully remove or replace all stale `house_overview` assumptions
- unify all natural `house status / summary / briefing` prompts around the daily house summary flow

### 2. Daily house summary depends on safe route allowlist
Status: active dependency

Symptoms:
- if `/ai/daily_house_summary` is missing from `safe_route_allowlist.json`
- direct route works, but agent query returns:
  `Route not allowed: /ai/daily_house_summary`

Impact:
- safe executor path breaks
- user sees blocked read-only summary request

Current state:
- fixed
- route added to safe allowlist

Desired behavior:
- keep route in allowlist
- include this in validation checklist after policy edits

### 3. House summary output is useful but still standalone
Status: active enhancement item

Symptoms:
- current summary covers energy, climate, occupancy, infrastructure, quiet/playback state
- agenda/calendar/reminders are not yet merged into this summary

Impact:
- useful operational house briefing exists
- full butler-style morning briefing is not complete yet

Desired behavior:
- merge:
  - house summary
  - agenda summary
  - reminder/task layer
  - optional crypto note
  - optional anomaly/warning note

### 4. Monitoring/infrastructure summary is sensitive to node availability
Status: expected behavior, monitor

Symptoms:
- offline nodes or temporary monitor failures appear in spoken summary
- example seen: `discoverpi` unavailable/offline

Impact:
- briefing can change depending on node health
- not a code bug, but may look noisy if infra is unstable

Desired behavior:
- keep visible for now
- later tune verbosity thresholds for spoken summaries

## Recently resolved

### A. Climate summary fallback answer
Status: resolved

Previous issue:
- climate telemetry queries could end in generic fallback style output

Resolution:
- active summarizer now handles `/ai/loxone_history_telemetry_latest`
- validated with live climate query output

### B. Most active room routing regression
Status: resolved

Previous issue:
- `which room seems most active right now` could misroute or return weaker behavior

Resolution:
- room activity phrasing expanded and validated
- live query now returns ranked active-room reasoning

### C. House briefing safe executor block
Status: resolved

Previous issue:
- `give me the house briefing` routed correctly but was blocked by safe route allowlist

Resolution:
- `/ai/daily_house_summary` added to:
  - route layer
  - internal executor
  - safe route allowlist
- validated through `/agent/query`



## Waste schedule integration
Status: active and working

Current state:
- waste pickup events are now read from Google Calendar
- source calendar currently resolves to `jorritnoppe@gmail.com`
- detected waste types include:
  - paper
  - PMD
  - GFT
  - rest waste
  - glass

Validated behavior:
- waste schedule summary returns full 2026 pickup list
- `spoken_next` now renders in English
- example: `The next pickup is paper on Tuesday.`

Open follow-up:
- integrate tomorrow pickup warnings into evening briefing
- integrate next pickup mention into morning briefing when relevant
- later add spoken reminder trigger for evening-before collection days


## Waste schedule and briefing routing
Status: resolved and active

Resolved issues:
- voice/agent questions about waste schedule now route through the safe executor
- `/ai/waste_schedule_summary` is available as a safe-read route
- morning briefing includes waste pickup context
- evening briefing includes waste pickup context
- tomorrow-specific waste questions now answer naturally

Validated behavior:
- `what is the waste schedule` -> safe executor -> `/ai/waste_schedule_summary`
- `when is the next waste pickup` -> `The next pickup is paper on Tuesday.`
- `is there garbage tomorrow` -> `No, there is no waste pickup tomorrow. The next pickup is paper on Tuesday.`
- `give me my evening briefing` -> safe executor -> `/ai/evening_briefing`

Notes:
- waste events are read from Google Calendar via the personal calendar source
- output wording is English
- no credentials or tokens are stored in the mirrored repo

Open follow-up:
- if pickup is tomorrow, evening briefing can later say to take bins outside tonight
- later allow scheduled spoken reminder playback



