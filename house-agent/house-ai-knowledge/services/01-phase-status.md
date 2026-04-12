# Phase Status

Last updated: 2026-04-12

## Current phase

Current phase: **House Intelligence Layer Stabilization**

This phase sits after the earlier infrastructure and safe execution milestones and focuses on turning raw home data into useful, trustworthy, room-aware AI answers.

The main goal of this phase is:

- convert structured house sensor data into human-meaningful room intelligence
- ensure house questions route to house intelligence rather than action handlers
- keep read/query behavior separate from action execution behavior
- make answers compact, accurate, and explainable

## Phase objective

The objective of the current phase is to make the house AI reliably answer questions like:

- What is happening in a room?
- Why is a room active?
- Which rooms are likely in use?
- Which rooms look like background automation?
- Is the house occupied or mostly idle?

without requiring raw payload inspection.

## Phase completion summary

### Completed in this phase

#### House sensor summarization path
Completed:

- house sensor summarization wired through internal safe route execution
- room-level state interpretation added
- room explanations now use ranked room intelligence rather than simple raw-state checks

#### Activity reasoning enrichment
Completed:

- sensor payload enrichment with activity reasons
- prioritization of stronger signals such as presence over weaker background indicators
- confidence scoring and human activity scoring
- room role awareness such as transitional vs utility vs living spaces

#### Room intelligence ranking
Completed:

- ranking of likely used rooms
- ranking of background-automation-like rooms
- room-specific status summarization
- better distinction between occupied and active-without-presence rooms

#### Query routing fix
Completed:

- false interception by safe-action router reduced
- house state questions now correctly reach room intelligence logic
- normal `/agent/query` responses are concise instead of full raw dumps

#### Validation smoke checks
Completed:

Validated examples include:

- `What is active in deskroom?`
- `Why is deskroom active?`
- `Which rooms are likely being used?`
- `Which rooms look like background automation?`
- `What is happening in livingroom?`

These now return meaningful compact responses.

## Current status by stream

### Stream: architecture safety
Status: **stable**

Notes:

- safe execution architecture is established
- safe read routes and safe action routes are conceptually separated
- more guardrail refinement is still possible, but the direction is correct

### Stream: room intelligence reasoning
Status: **working, needs tuning**

Notes:

- core reasoning model is working
- presence and occupancy answers are good
- transitional room behavior and decay tuning still need refinement
- edge-case wording can still be improved

### Stream: query routing
Status: **fixed for current known regression**

Notes:

- the major misrouting issue has been corrected
- additional regression tests should be documented to protect against future route drift

### Stream: documentation
Status: **partially up to date, refresh in progress**

Notes:

- many knowledge files exist already
- latest room intelligence and phase status need explicit project-state docs
- roadmap docs should be consolidated and refreshed

### Stream: operational reliability
Status: **mixed**

Notes:

- main house-agent service is working
- UniFi collector is still showing rate-limit issues in logs
- this is not a blocker for house intelligence, but it is still an operational watch item

## What this phase has proven

This phase has proven that the system can now do more than just expose sensor data.

It can:

- infer likely occupancy
- explain why a room is considered active
- distinguish probable human use from probable system/background activity
- answer in a short AI-friendly format

That is a key shift from integration infrastructure to actual house intelligence.

## What remains before this phase can be considered complete

This phase should be considered fully complete once the following are done:

1. documentation is updated to reflect the new room intelligence architecture
2. a validation checklist exists for routing and reasoning regressions
3. known issues are documented explicitly
4. transitional room and decaying presence behavior are reviewed with more real-world examples
5. safe-action query matching is reviewed to ensure future wording changes do not reintroduce route collisions

## Readiness to move to next phase

Readiness: **high, after documentation and validation cleanup**

The implementation is already strong enough to move forward, but it is worth taking the short pause now to:

- document what exists
- define validation checks
- list known issues
- lock in the current architecture understanding

That will make the next phase cleaner and safer.
