> Detail doc: this file expands on the canonical root docs listed in `INDEX.md` and should be read after the numbered root files.

# Safety Guardrails (Updated)

## Critical systems detected
- Loxone control
- Audio routing
- Package installation services
- Experimental tools

## High risk services
- loxone_action_service.py
- package_install_service.py
- experimental_* services

## Rules
- No direct hardware control from LLM
- All actions via routes
- Tool promotion must be audited
- Package installs must be restricted

