# Audio Validation Routes

## GET /ai/audio_timing_health
Returns compact speaker timing health summary from the most recent cached timing test.

Useful fields:
- `health`
- `verdict`
- `beep_count`
- `avg_interval_sec`
- `first_beep_offset_sec`
- `probe_rms`
- `saved_at`

## GET /ai/audio_timing_last
Returns full cached timing test result.

Useful for:
- debugging
- inspecting beep region analysis
- inspecting saved capture path
- inspecting pattern URL and playback result

## POST /ai/audio_timing_run
Runs a fresh audible timing test and caches the result.

Example JSON body:
```json
{
  "target": "desk",
  "volume": 60,
  "probe_seconds_back": 18,
  "probe_label": "timing_test"
}
