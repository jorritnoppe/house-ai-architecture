> Detail doc: this file expands on the canonical root docs listed in `INDEX.md` and should be read after the numbered root files.

# AI Evolution Roadmap

## Current State
Completed foundations:
- voice -> STT -> /agent/query
- /agent/query -> safe executor bridge
- executor -> allowlisted routes/tools only
- real sensor data from house systems
- blocked dangerous routes/tools
- knowledge pack + generated maps + policy files

This means the house AI is now a functional, policy-driven local agent.

---

## Phase 1 - Make It Feel Smart
Priority: High

### 1. Voice response quality
Goal: Make spoken answers short, natural, and useful.

Tasks:
- Replace raw dict-like answers with human-friendly summaries
- Add unit-aware formatting for watts, kWh, temperatures, prices
- Add endpoint-specific response builders
- Keep spoken responses concise by default

Examples:
- "The house is using 1.1 kilowatts right now."
- "Solar is currently producing 2.4 kilowatts."
- "Electricity costs 21 cents per kilowatt-hour right now."

### 2. Smarter intent matching
Goal: Understand more natural phrasing in voice and chat.

Tasks:
- Expand phrase coverage for existing safe routes
- Add synonym matching
- Add normalization layer
- Add better handling of common spoken wording

Examples:
- "What is the house using right now"
- "How much electricity are we drawing"
- "What's the load"

### 3. Structured answer layer
Goal: Separate data retrieval from human speech output.

Target structure:
- raw data
- spoken answer
- confidence
- matched action metadata

This becomes the base for better UI and future reasoning.

---

## Phase 2 - Real Intelligence
Priority: High

### 4. Multi-step reasoning engine
Goal: Combine multiple safe data sources into one intelligent answer.

Example questions:
- "Is now a good time to run the dishwasher?"
- "Why is power high right now?"
- "Should I wait until later to charge something?"

Inputs may include:
- current load
- solar production
- price
- recent patterns

### 5. Context awareness
Goal: Use time and normal patterns to improve answers.

Tasks:
- compare current usage with typical usage at this hour
- use room and conversation context
- identify repeated household patterns

### 6. Anomaly detection
Goal: Detect unusual behavior from stored data.

Targets:
- abnormal power spikes
- missing sensor data
- suspicious appliance patterns
- changed baseline behavior

Possible future voice output:
- "Power usage is unusually high for this time of day."

---

## Phase 3 - Safe Actions
Priority: High but after more review

### 7. Enable safe actions
Goal: Allow a controlled subset of house actions.

First candidates:
- music control
- speaker routing
- announcements
- selected non-destructive automation triggers

Rules:
- allowlist only
- policy-based
- cooldowns where needed
- explicit safety review

### 8. Action policy engine
Goal: Move from static allowlists to context-aware rules.

Examples:
- do not take over a speaker already in use
- do not toggle relays too often
- do not trigger actions during conflicting states

### 9. Confirmation flow
Goal: Add human confirmation for risky actions.

Example:
- "Do you want me to turn on party music?"

---

## Phase 4 - House Intelligence Layer
Priority: Medium-high

### 10. Daily briefing system
Goal: Personalized spoken and visual house briefings.

Planned inputs:
- calendar
- email
- house sensor data
- reminders
- price and energy info

Planned outputs:
- morning spoken summary
- dashboard-style daily overview

### 11. Chore and scheduling system
Goal: Household planning and accountability.

Planned features:
- recurring chores
- reminders
- yearly planning
- verification using electricity usage and house data

Examples:
- laundry detected or not detected
- dishwasher likely completed
- room or task reminders

### 12. Electricity-aware automation
Goal: Use price and solar context intelligently.

Possible flows:
- suggest best cheap hours
- align loads with solar production
- reduce expensive-time usage

---

## Phase 5 - Full Voice System
Priority: Medium

### 13. Multi-room voice awareness
Tasks:
- map microphones to rooms
- route answers to correct speakers
- preserve room ownership rules

### 14. Interruptions and conversations
Tasks:
- follow-up question handling
- last-speaker awareness
- lightweight context carry-over

### 15. Wake-word and passive listening
Tasks:
- room-aware wake word
- safer always-on interaction
- microphone fleet expansion

---

## Phase 6 - Control UI and Config
Priority: Medium

### 16. House control web interface
Goal: Reduce manual script editing.

Planned controls:
- device registry
- parameter tuning
- automation options
- settings management
- device inclusion/exclusion lists

### 17. Central config layer
Goal: Stable metadata for the whole system.

Planned data:
- friendly sensor names
- units
- thresholds
- room mappings
- device metadata
- policy categories

---

## Maintenance Rule
Whenever the project expands with:
- new routes
- new services
- new tools
- new actions
- new voice flows
- new scheduling logic

You must:
1. update the knowledge pack
2. regenerate route/service/tool maps
3. regenerate agent and policy files
4. review safety classification before exposing new capability to the AI

Core scripts:
- house-ai-knowledge/tools/rebuild_knowledge_pack.sh
- house-ai-knowledge/tools/generate_code_docs.py
- house-ai-knowledge/tools/generate_agent_layer.py
- house-ai-knowledge/tools/build_final_policy.py

---

## Recommended Next Focus
Best near-term return:
1. voice response quality
2. smarter intent matching
3. structured answer layer

These improve the experience immediately without opening risky actions too early.
