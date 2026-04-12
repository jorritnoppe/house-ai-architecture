# Validation Checklist

Last updated: 2026-04-12

## Purpose

This checklist is used to validate the current house intelligence and routing behavior after changes to:

- `routes/agent_routes.py`
- `services/agent_router_bridge.py`
- related room intelligence logic
- safe-action routing heuristics

## Pre-check

Before validation:

- activate the correct environment
- ensure `house-agent.service` is restarted after changes
- verify Python compile passes for touched files
- confirm the expected route exists

Recommended pre-check commands:

```bash
cd ~/house-agent
source venv/bin/activate

python3 -m py_compile routes/agent_routes.py services/agent_router_bridge.py && echo "PY OK"
sudo systemctl restart house-agent.service
sudo systemctl status house-agent.service --no-pager
