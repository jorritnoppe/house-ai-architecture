# House AI Routes

## Purpose
This file documents the route layer for future AI retrieval.

Routes are the main API surface of the house-agent. They are the approved entrypoints for reading data and triggering controlled actions.

Future AI should use this file to understand:
- what API endpoints exist
- which endpoints are read-oriented
- which endpoints trigger actions
- which endpoints are part of the main AI control path

---

## Role of the Route Layer
Routes should:
- expose explicit endpoints
- validate requests
- call service logic
- return structured JSON
- avoid embedding too much low-level hardware behavior

The route layer is the public operational surface of the project.

---

## Core Agent Route

### `POST /agent/query`
Purpose:
- main AI-facing entrypoint
- accepts a question or request
- returns an answer and may also return structured execution details

Typical usage:
- ask for current house state
- ask for telemetry summaries
- request approved actions through the AI layer

Why it matters:
- this is the most important route for natural-language interaction
- future AI should understand that many user requests begin here even if the actual work happens deeper in the stack

Typical payload shape:
```json
{
  "question": "give me latest temperature and humidity in the house"
}
