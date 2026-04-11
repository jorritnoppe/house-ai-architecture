> Detail doc: this file expands on the canonical root docs listed in `INDEX.md` and should be read after the numbered root files.

# Route Inventory

This file is the human-maintained summary.
See also:
- `api/15-generated-route-map.md` for auto-detected route handlers
- `generated/route_map.json` for machine-readable data

## Route families
- health/status
- power / sma / water / pdata / price
- agent / house
- voice / voice input
- tools / openai / loxone / audio

## What to maintain here
- which routes are read-only
- which routes perform writes
- which routes are safe for AI invocation
- which routes require confirmation
