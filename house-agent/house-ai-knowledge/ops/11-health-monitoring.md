> Detail doc: this file expands on the canonical root docs listed in `INDEX.md` and should be read after the numbered root files.

# Health and Monitoring

## Related files
- routes/health_routes.py
- routes/status.py
- services/status_service.py
- services/monitor_ups_voice.py
- services/apc_legacy_core.py
- services/apc_service.py

## Current monitoring themes
- basic service health
- device ping / port checks
- Ollama check
- InfluxDB check
- Open WebUI availability
- voice availability
- UPS-related announcements

## Current direction
The system is capable of building spoken status summaries and detecting core service failures.

## TODO
Document:
- exact monitored endpoints/devices
- severity levels
- spoken summary behavior
- how failures are surfaced to the user
