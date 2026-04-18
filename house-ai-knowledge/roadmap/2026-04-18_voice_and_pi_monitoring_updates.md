# 2026-04-18 Voice and Pi Monitoring Updates

## Completed

### Voice-node truthfulness
- safe `/ai/house_state` routing expanded for voice-node questions
- interpreted summarizer now truthfully answers:
  - online
  - stale
  - offline
  - registered and unknown node states
- desk mic phrasing now resolves through safe executor instead of fallback model output

### Pi monitoring storage hardening
- Netdata retention reduced on Pi nodes
- oversized local Netdata caches cleaned on validated nodes

## Validated result
The router is now behaving correctly.

Current validated voice-node runtime state:
- `deskmic` is configured
- no heartbeat currently seen
- current live state is `unknown`

Spoken results now correctly reflect live state:
- no voice nodes online
- no stale voice nodes
- no offline voice nodes
- registered voice nodes without heartbeat yet are reported

## Important follow-up
The remaining issue is runtime heartbeat delivery from DeskPi, not router logic.

## Next likely step
Debug why DeskPi is not posting heartbeat to the AI server:
- wake listener heartbeat sender
- API endpoint reachability
- registry ingestion
- service logs
