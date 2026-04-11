# House AI Project Overview

## Purpose
This project is a local house AI system built to safely read house data, analyze time-series information, and trigger approved automations through controlled APIs.

The long-term goal is not just to answer questions, but to create a reliable house intelligence layer that understands:
- what devices exist
- what data sources exist
- what actions are allowed
- how actions must be executed safely
- what system behaviors are special or sensitive

This file is intended as a first-entry summary for future AI sessions and future maintainers.

---

## Core System Identity
This repository is the main `house-agent` backend running on the local AI server.

It acts as a bridge between:
- AI reasoning
- house telemetry
- automation controls
- voice output
- historical data

The project is designed so the AI does **not** directly talk to hardware in an uncontrolled way. Instead, the AI should work through approved routes and service functions.

---

## Main Capabilities

### 1. Sensor and Telemetry Access
The system can retrieve:
- current house power usage
- room temperature and humidity
- historical telemetry from InfluxDB
- external device data such as inverter and meter information
- future device integrations as they are added

### 2. Safe Automation Control
The system can expose safe endpoints for:
- Loxone-triggered automation
- music and speaker-related controls
- controlled relay operations
- future approved house actions

The design rule is that automations must be wrapped in named, predictable endpoints instead of raw direct control.

### 3. Voice and Announcement Output
The system can:
- generate text-to-speech
- route speech to room audio targets
- manage special speaker handling for protected zones
- support house summaries, agenda output, and future interactive speech features

### 4. AI Orchestration
The system can accept natural-language style requests through the agent layer and translate them into:
- information answers
- telemetry summaries
- safe route calls
- controlled action execution

---

## Main Platform Components

### Flask API
The Flask app is the main control layer of the project. It exposes routes, validates inputs, and calls services.

### Ollama
Ollama is used as the local large language model backend for AI reasoning and response generation.

### InfluxDB
InfluxDB stores historical data and time-series information used for summaries, comparisons, and state lookups.

### Loxone
Loxone is used for house automation, switching logic, relays, and control integration.

### Audio Stack
The voice/audio stack includes local speech generation plus playback routing through LMS / PiCore style targets and room-specific speaker logic.

---

## High-Level Design Philosophy

### Safety First
The project should always prefer:
- explicit routes
- explicit services
- explicit allowed actions
over raw direct control.

### Structured Integration
Hardware-specific logic should be isolated in services and helper modules so the AI layer stays clean and predictable.

### Retrieval-Friendly Documentation
The `house-ai-knowledge` folder exists so future AI sessions can quickly understand the system without re-reading the entire codebase every time.

### Expandability
The project is expected to grow over time with:
- more sensors
- more endpoints
- more voice interaction
- more scheduling
- more house intelligence
- more locked-down automation logic

---

## Important Operating Rule for Future AI
If a future AI is unsure whether an action is safe, it should prefer:
1. reading data instead of writing controls
2. using existing approved endpoints instead of inventing new ones
3. asking for verification rather than assuming device behavior
4. preserving current working flows unless explicitly told to change them
