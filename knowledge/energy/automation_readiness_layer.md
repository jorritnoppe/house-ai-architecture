# Energy Automation Readiness Layer (v0.4)

## Status
Implemented on April 12, 2026.

## Purpose
Provide a safe, stable, and authoritative signal indicating when the house has usable excess solar energy for automation.

This layer prevents unstable triggers by enforcing:
- stability windows
- hysteresis
- cooldown periods

## Endpoint

GET /ai/automation/excess_energy_ready

## Example response

```json
{
  "ready": true,
  "level": "high",
  "available_kw": 3.2,
  "safe_to_use": true
}
