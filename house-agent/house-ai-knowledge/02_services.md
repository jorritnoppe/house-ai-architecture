# House AI Services

## Purpose
This file describes the service layer for future AI retrieval.

Services are the main behavior layer of the project. They are responsible for turning route requests into useful system actions while hiding hardware-specific complexity.

For future AI, this file should answer:
- which services exist
- what each service is responsible for
- where special logic lives
- which behaviors are important not to break

---

## Service Layer Role
In this project, services should:
- perform structured logic
- talk to integrations
- protect routes from device complexity
- keep special handling centralized
- return predictable data structures

Routes should be thin. Services should do the real work.

---

## Main Known Service Responsibilities

### `agent_service.py`
Purpose:
- implements the AI-facing orchestration behavior
- interprets user questions and agent requests
- decides whether a request is informational or actionable
- helps map natural-language input into safe system behavior

Why it matters:
- this is one of the core entrypoints for AI interaction
- future AI should understand that this file is part of the translation layer between human requests and house-safe behavior

---

### `loxone_service.py`
Purpose:
- wraps communication with Loxone
- sends structured control calls
- reads or triggers defined Loxone-related functions
- supports house control through controlled endpoints instead of raw arbitrary calls

Why it matters:
- Loxone is one of the most sensitive parts of the system
- future AI should prefer this wrapped path over direct device interaction

Important behavior:
- Loxone actions should stay explicit and safe
- future changes should preserve approved command structure

---

### `voice_service.py`
Purpose:
- handles speech generation and/or playback orchestration details
- routes spoken content toward player targets
- manages audio output behavior at the lower service level

Why it matters:
- voice output is one of the most visible house AI functions
- future AI sessions will often need to understand how speech is actually emitted

Important behavior:
- not all players behave the same
- routing details matter
- future AI should avoid assuming all rooms are interchangeable

---

### `announcement_service.py`
Purpose:
- implements higher-level spoken announcement behavior
- prepares playback targets before speech
- manages special controlled speaker behavior
- handles cleanup or release behavior after playback where needed

Why it matters:
- this is likely where important protected audio flows are enforced
- future AI should look here when understanding room speech behavior and living-room speaker protection

Important behavior:
- living room audio requires controlled handling
- prepare-before-play and release-after-play behavior should stay centralized here or in the linked voice path

---

### `influx_service.py`
Purpose:
- reads historical telemetry from InfluxDB
- supports sensor summaries, trend lookups, and recent-history queries
- provides time-series information in a structured way

Why it matters:
- many useful AI answers depend on history, not just current values
- future AI should prefer these structured queries over reinventing raw database access logic

---

### SMA-related service logic
Likely purpose:
- retrieve solar or inverter-related values
- expose power and production information
- provide structured energy context for house summaries

Why it matters:
- house energy understanding is a major project goal
- future AI should treat inverter data as part of the overall house state model

---

### Other device/integration service files
The project also appears to include or anticipate service logic for things such as:
- APC UPS data
- Buderus integration
- water-related data
- energy pricing
- scheduling
- house status summaries
- future helper orchestration

Future AI should inspect service files before assuming a feature does not already exist.

---

## Important Cross-Service Behavior

### Living Room Audio Protection
This is one of the most important known special cases.

Current understanding:
- living room playback is not a normal direct speaker target
- the speaker path requires controlled enable behavior
- the audio path should be released after use so the normal system can regain access

This means:
- future AI should not treat living room playback as a generic direct output
- future route additions should reuse the protected flow instead of bypassing it

---

### Safe Action Execution
Services should form the bridge between:
- AI requests
- approved routes
- actual device behavior

That means the future AI should look at services first when answering:
- what does this route really do
- what side effects happen
- what hardware is affected
- what cleanup or safety logic exists

---

## Guidance for Future AI
When unsure how something works:
1. inspect the route that exposes it
2. inspect the service it calls
3. inspect whether that service contains timing, safety, or cleanup behavior
4. document the real behavior before changing it

Do not assume a service is simple just because the route is simple.
