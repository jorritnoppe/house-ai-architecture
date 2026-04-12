# Voice roadmap

## Done
- LMS playback to piCorePlayer
- /voice/say endpoint
- /voice/volume endpoint
- Player aliases
- Volume control
- Piper TTS
- Piper tuning from .env
- In-memory Piper service
- AI answers spoken through LMS

## Current decisions
- Keep one voice for now
- CUDA support enabled/pursued
- No room/audio mapping yet
- No house announcements yet
- No microphones yet

## Next later
- House announcements
- Audio routing by room/presence
- Microphones in rooms
- Wake word
- Speech to text
- Full spoken house interaction


## ⚡ Energy Automation (NEW)

- v0.4: ✅ automation readiness layer (stable + SQLite-backed)
- v0.5: ⏳ device eligibility + safety policies
- v0.6: ⏳ real load orchestration (EV / boiler / appliances)

## Energy Automation Roadmap

### v0.4
- Completed excess-energy automation readiness endpoint
- Added anti-flapping logic: stability window, hysteresis, cooldown
- Added SQLite shared state for cross-worker consistency
- Endpoint: /ai/automation/excess_energy_ready

### v0.5
- Add stale-state guard so old readiness state cannot be trusted indefinitely
- Add passive Loxone polling integration
- Add per-device eligibility endpoints for future smart appliances
- Add manual arm / policy layer before any real actuation

### Future smart appliance phase
When real controllable smart loads are available, extend the energy brain with:
- boiler eligibility
- EV charging eligibility
- laundry eligibility
- Alco eligibility
- priority-based load scheduling
