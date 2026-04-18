# Waste-aware briefings

## Status
Active and validated.

## Implemented components
- `services/waste_schedule_service.py`
- `services/morning_briefing_service.py`
- `services/evening_briefing_service.py`
- `routes/house_state_routes.py`
- `services/internal_route_executor.py`
- `services/agent_router_bridge.py`
- `house-ai-knowledge/policy/safe_route_allowlist.json`

## Safe routes
- `/ai/waste_schedule_summary`
- `/ai/morning_briefing`
- `/ai/evening_briefing`

## Voice-safe routing
Waste questions are now matched explicitly in the safe action router so they do not fall through to the generic fallback agent.

Examples:
- `what is the waste schedule`
- `when is the next waste pickup`
- `is there garbage tomorrow`

## Wording behavior
General waste question:
- return next pickup wording

Tomorrow-specific question:
- if pickup exists tomorrow, answer with tomorrow wording
- if no pickup exists tomorrow, answer:
  - `No, there is no waste pickup tomorrow. The next pickup is ...`

## Briefing behavior
Morning briefing:
- includes waste context when useful

Evening briefing:
- includes waste context when useful
- later should gain stronger reminder wording for tomorrow pickup cases

## Safety notes
- all routes are safe-read only
- no Google credential files are mirrored into the architecture repo
- only code and documentation are copied into the repo mirror

## Next improvement
When waste pickup is tomorrow, evening briefing should say:
- `Important reminder. Tomorrow is PMD pickup. Please take the bin outside tonight.`
