# Audio Validation Intents

## Supported intent behavior

### audio_timing_health
Use when the user asks:
- is desk speaker timing healthy
- did the last timing validation pass
- what is the current speaker timing status
- is playback timing okay

This should call:
- `GET /ai/audio_timing_health`

### audio_timing_last
Use when the user asks:
- show me the last timing validation
- give me full timing diagnostics
- show latest beep analysis
- what happened in the last speaker validation

This should call:
- `GET /ai/audio_timing_last`

### audio_output_confidence
Use when the user asks:
- how confident are we that output is audible
- can we trust the desk speaker output
- do we have high confidence in playback audibility

This should call:
- `GET /ai/audio_output_confidence`

### audio_timing_run
Use when the user asks:
- run a desk speaker timing test
- validate the desk speaker
- rerun timing validation
- test the feedback probe speaker path again

This should call:
- `POST /ai/audio_timing_run`

Default payload:
```json
{
  "target": "desk",
  "volume": 60,
  "probe_seconds_back": 18,
  "probe_label": "timing_test"
}
