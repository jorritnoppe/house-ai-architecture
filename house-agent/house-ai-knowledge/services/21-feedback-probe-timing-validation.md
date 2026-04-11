# Feedback Probe Timing Validation

## Purpose
Validate whether House AI audio played on a speaker is actually audible in the room and captured by the external feedback probe node.

This is used as a safe diagnostics layer for:
- speaker validation
- playback timing checks
- future second-opinion / confidence checks
- future autonomous diagnostics under explicit policy

## Nodes
- AI server API: `192.168.9.182:8000`
- AI server static generated audio server: `192.168.9.182:8010`
- DiscoverPi feedback probe node: `192.168.9.198:8091`

## Why port 8010 exists
Generated timing WAV files originally went through the main Flask/Gunicorn app on port `8000`.

Because the main API runs with a single Gunicorn worker, timing-test playback could fail when:
- `/feedback-probe/run_timing_test` was executing
- and Lyrion / the player tried to fetch the generated WAV from `/voice/files/...`
- while that same single worker was already busy

This caused unreliable playback during the full timing route.

Fix:
- keep API logic on `8000`
- serve generated timing/test WAV files from a separate static server on `8010`

This removed the self-blocking problem.

## Current architecture
### Main API
- service: `house-agent.service`
- port: `8000`
- purpose: Flask API, agent routes, orchestration, diagnostics logic

### Static generated audio server
- service: `house-audio-files.service`
- port: `8010`
- purpose: serve files from `/tmp/house-agent-voice`

### Feedback probe node
- service: `feedback-node.service`
- port: `8091`
- purpose: room microphone capture, save recent audio windows, timing capture sessions

## Timing validation flow
1. AI server generates a short beep pattern WAV in `/tmp/house-agent-voice`
2. AI server exposes that file through static server `8010`
3. AI server asks DiscoverPi to arm a timing capture session
4. AI server triggers playback to target speaker using the static URL
5. DiscoverPi records with pre-roll + capture window
6. AI server downloads the captured WAV from DiscoverPi
7. AI server analyzes beep regions and timing spacing
8. AI server returns a structured summary

## Important route split
### On AI server
Use:
- `http://127.0.0.1:8000/...` for AI server routes
- `http://192.168.9.198:8091/...` for DiscoverPi feedback-node calls

### On DiscoverPi
Use:
- `http://127.0.0.1:8091/...` for local feedback-node routes
- `http://192.168.9.182:8000/...` for AI server routes

## Working route
### Full timing test
`POST /feedback-probe/run_timing_test`

Example body:
```json
{
  "target": "desk",
  "volume": 60,
  "probe_seconds_back": 18,
  "probe_label": "timing_test"
}
