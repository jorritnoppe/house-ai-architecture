# Safe Audio Action Runtime Policy

## Purpose
Define how safe audio actions are tracked at runtime and how the AI should interpret active versus inactive music states.

## Core Principle
Music state is currently inferred from safe action runtime state, not from real-world audio detection.

This means the AI answers:
- what music is playing
- is living room music on
- is bathroom music on
- is toilet music on
- is party mode on

based on tracked action activity.

## Runtime State File
Runtime state is stored in:

`house-ai-knowledge/policy/action_runtime_state.json`

This file tracks active/inactive status for start actions such as:
- `music_living_start`
- `music_bathroom_start`
- `music_wc_start`
- `music_party_start`

## Runtime State Rules

### Start action rule
When a `_start` action succeeds:
- that start action is marked active

Example:
- `music_living_start` => active = true

### Stop action rule
When a `_stop` action succeeds:
- the paired `_start` action is marked inactive

Example:
- `music_living_stop` => `music_living_start` active = false

### Cleanup rule
Some stop actions also run cleanup steps after the main stop action succeeds.

Examples:
- living room stop turns off living route switch
- WC stop turns off WC route switch
- party stop turns off living and storageroom route switches

## Current Practical Meaning Of "Playing"
The AI currently treats "playing" as:
- an active safe music action exists in runtime state

This is not the same as:
- proven speaker output
- verified LMS playback state
- acoustic microphone confirmation

## Current Runtime Endpoints

### `GET /tools/safe/state`
Returns raw runtime state.

### `GET /tools/safe/active`
Returns only currently active actions.

### `GET /tools/safe/status`
Returns summary status of active safe actions.

## Safe Audio Categories

### cat1
AI can use when needed.
Examples:
- living start/stop
- bathroom start/stop
- WC stop
- party stop

### cat2
AI can use when explicitly requested.
Example:
- WC start

### cat3
Verification/confirmation required.
Example:
- party start

## Party Mode Rule
Party mode start is a higher-risk action and should require explicit confirmation.

Execution policy:
- no confirmation => return confirmation_required
- confirmed=true => execute

## What The AI Should Say
Examples of correct summaries:

### Global
- `No safe audio actions are currently active.`
- `Active safe actions: Living room music.`
- `Active safe actions: Bathroom music.`
- `Active safe actions: WC music.`
- `Active safe actions: Party mode.`

### Room-specific
- `Living room music is active.`
- `Living room music is not active.`
- `Bathroom music is active.`
- `Bathroom music is not active.`
- `WC music is active.`
- `WC music is not active.`
- `Party mode is active.`
- `Party mode is not active.`

## Known Limit
Runtime state can be wrong if something changes outside the safe action path.

Examples:
- manual button presses
- direct Loxone automation
- external player control
- reboot without proper sync logic

## Future Improvement
Later, runtime state can be strengthened by combining:
- safe action runtime state
- player API status
- Loxone state verification
- optional mic/audio confirmation

For now, runtime state is good enough and is the correct source of truth for `/agent/query` safe audio status answers.
