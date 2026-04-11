> Detail doc: this file expands on the canonical root docs listed in `INDEX.md` and should be read after the numbered root files.

# Agent and Routing Layer

## Files observed
- services/agent_service.py
- services/agent_house.py
- services/agent_crypto.py
- services/intent_detection.py
- router_logic.py
- router_tools.py

## Current role
Translate user questions into:
- summaries
- sensor lookups
- house status responses
- safe action requests

## Notes
- router_logic.py contains power and Loxone-oriented intent matching
- current system includes phrases for power, import/export, phase, anomaly, house overview, and Loxone structure lookup
- project is moving toward a richer structured house assistant rather than a pure chatbot

## Knowledge objective
Document how intent flows from question -> route -> service -> device/data.
