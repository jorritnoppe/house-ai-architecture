# Audio Validation Agent Behavior

## Purpose
Allow the house AI to safely reason about speaker playback validation using the external feedback probe node.

## Available routes
- `GET /ai/audio_timing_health`
- `GET /ai/audio_timing_last`
- `POST /ai/audio_timing_run`

## When to use each route
### `/ai/audio_timing_health`
Use when the user asks:
- is desk speaker timing healthy
- did the last audio validation pass
- is playback validation okay
- what is the current timing health

This is the preferred quick check route.

### `/ai/audio_timing_last`
Use when the user asks for:
- detailed timing diagnostics
- last validation details
- beep count
- interval spacing
- saved capture path
- pattern URL
- deeper debugging context

### `/ai/audio_timing_run`
Use only when the user explicitly asks to:
- run a desk speaker timing test
- validate whether the speaker output is audible
- rerun the feedback timing validation
- test the speaker/feedback path again

This route is audible and should be treated as explicit diagnostics.

## Response guidance
### Healthy result
If `/ai/audio_timing_health` returns:
- `health = healthy`
- `verdict = ok`

Then explain that:
- the last timing test passed
- beeps were detected correctly
- interval spacing is normal
- playback-to-room capture path appears healthy

### Warning result
If:
- beep count is low
- verdict is warning-like
- analysis is incomplete

Then explain that:
- the speaker path may be degraded
- background noise or room conditions may have affected validation
- a rerun may help

### Failed result
If no beeps are found or timing fails:
- explain that the validation failed
- recommend a rerun
- mention possible causes: playback issue, room noise, capture issue, routing issue

## Safety
Do not run `/ai/audio_timing_run` automatically without user intent.
Read-only health queries are safe.


### `/ai/audio_output_confidence`
Use when the user asks:
- how confident are we that desk output is really audible
- can you trust the speaker path
- do we have good playback confidence

This is a derived confidence signal based on the latest timing validation, not a new live measurement.
