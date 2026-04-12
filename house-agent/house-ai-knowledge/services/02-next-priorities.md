# Next Priorities

Last updated: 2026-04-12

## Priority summary

The next priorities should focus on stabilizing and validating the current intelligence layer before expanding into broader context-aware and multi-system behaviors.

## Priority 1: finish documentation refresh

Reason:

The implementation has advanced significantly, especially around room intelligence and routing, but documentation needs to be aligned so future work is grounded in the current real system rather than memory.

Tasks:

- write current project state summary
- write phase status summary
- document next priorities
- document room intelligence query routing
- document house sensor reasoning model
- document validation notes
- update architecture overview
- update root knowledge index and readme
- create master roadmap page tying all roadmap files together

Outcome:

- current state is preserved clearly
- future chats and future implementation work can resume without ambiguity
- documentation mirrors actual live/project behavior

## Priority 2: formalize room intelligence validation

Reason:

The recent routing fix and compact answer improvements work, but they should be protected by a repeatable validation checklist.

Tasks:

- define known-good test questions
- document expected routing behavior
- document expected answer style
- list likely false-match phrases for safe-action routing
- define sample edge cases for transitional rooms
- add regression notes for future route/intent changes

Suggested validation question set:

- What is active in deskroom?
- Why is deskroom active?
- What is happening in livingroom?
- Which rooms are likely being used?
- Which rooms look like background automation?
- Are lights on in deskroom?
- Why is entranceroom active?
- What is happening in kitchenroom?

Outcome:

- future refactors can be checked quickly
- route collisions become easier to detect
- answer quality can be tracked

## Priority 3: tune transitional and low-confidence room behavior

Reason:

The current model already distinguishes occupied rooms from lower-confidence/background ones, but transitional rooms still need careful tuning.

Focus areas:

- entranceroom
- hallwayroom
- kitchenroom in access-only cases
- masterbedroom when access/security signals appear without ongoing presence
- rooms that should decay faster after brief passage

Tasks:

- review decay logic for transitional rooms
- review scoring weight for access-only events
- confirm whether some security/status signals should influence activity at all
- refine wording for low-confidence activity answers

Outcome:

- fewer misleading “active” interpretations
- better distinction between human presence and lingering automation/noise
- more trustworthy room explanations

## Priority 4: improve answer richness without dumping payloads

Reason:

The compact answers are much better than raw dumps, but the next step is making them slightly richer while staying concise.

Possible improvements:

- include secondary reasons where useful
- mention recent signal type for low-confidence cases
- mention “recently active but no current presence” as a stable phrasing
- mention room role when it helps explain behavior, such as transitional room logic

Outcome:

- better human understanding
- more trustworthy interpretations
- still compact enough for normal use and voice output

## Priority 5: address operational watch items

Reason:

Not all issues are intelligence bugs. Some are operational reliability concerns that could degrade later features.

Current watch items:

- UniFi collector login/refresh rate-limit 429s
- possible future route drift between action queries and house queries
- docs lagging implementation
- possible duplicate worker-side startup behaviors that need periodic review

Outcome:

- cleaner service health
- less debugging noise
- more stable base for the next phase

## Priority 6: prepare next evolution layer

Reason:

Once current room intelligence is documented and validated, the next step is to evolve from room-state interpretation to richer house intelligence.

Likely next expansions:

- contextual daily house briefing logic
- room-aware spoken summaries
- scheduling and recurring task intelligence
- multi-room / multi-node spoken interaction later
- richer use of house state, energy, and event history together
- integration with future announcements and household routines

Outcome:

- transition from “house state reporter” to “house assistant”
- stronger bridge between sensing, inference, and safe action

## What should not be rushed yet

The following should not be rushed before current stabilization is documented:

- broad autonomous action expansion
- uncontrolled AI automation access
- multi-mic arbitration implementation
- complex personal context orchestration
- large scheduling engine expansion

These are valid future directions, but the right move now is to stabilize the intelligence core first.

## Recommended immediate sequence

Recommended immediate sequence:

1. complete knowledge docs refresh
2. complete validation checklist and watchlist
3. validate room-intelligence routing and sample answers
4. tune transitional-room logic if needed
5. then proceed into next-phase house intelligence features
