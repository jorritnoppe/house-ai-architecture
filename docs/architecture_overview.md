# Architecture Overview

## Core flow
User or system input
-> intent interpretation
-> route selection
-> safety validation
-> service execution
-> telemetry/state feedback

## Main layers

### Input layer
Accepts voice, API, and internal trigger inputs.

### Reasoning layer
Interprets requests and maps them to structured actions.

### Safety layer
Separates read-only actions from sensitive write actions and applies approval logic where needed.

### Execution layer
Uses modular services to interact with telemetry sources, automation layers, and output channels.

### Feedback layer
Returns results, current state, and historical context for follow-up reasoning.

## Design goals
- local-first
- modular
- safe by default
- observable
- extensible
