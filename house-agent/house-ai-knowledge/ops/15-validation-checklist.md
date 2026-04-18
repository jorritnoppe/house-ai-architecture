# Validation Checklist

Last updated: 2026-04-18

## Purpose

This checklist validates house intelligence, safe executor routing, summarization quality, and safe separation between read questions and action questions.

Use this after changes to:
- `services/agent_router_bridge.py`
- `services/internal_route_executor.py`
- `services/house_state_service.py`
- `routes/house_state_routes.py`
- `services/agent_house.py`
- policy allowlists related to safe routes

## Pre-check

Before validation:
- activate the correct environment
- compile touched Python files
- restart `house-agent.service` if code changed
- verify service health
- verify touched routes still exist

## Compile and restart

Run:

    cd ~/house-agent
    source venv/bin/activate

    python3 -m py_compile \
      services/agent_router_bridge.py \
      services/internal_route_executor.py \
      services/house_state_service.py \
      routes/house_state_routes.py \
      services/agent_house.py \
      services/agent_executor.py && echo "PY OK"

    python3 -m json.tool house-ai-knowledge/policy/safe_route_allowlist.json >/dev/null && echo "SAFE ROUTE JSON OK"

    sudo systemctl restart house-agent.service
    sleep 2
    sudo systemctl status house-agent.service --no-pager

## Route existence checks

Run:

    cd ~/house-agent
    grep -Rni "daily_house_summary" services routes house-ai-knowledge app.py | sed -n '1,240p'
    grep -Rni "summarize current house status\|house briefing\|daily briefing\|house summary" services/agent_router_bridge.py | sed -n '1,220p'

Expected:
- `get_daily_house_summary()` exists
- `/ai/daily_house_summary` exists in routes
- `/ai/daily_house_summary` exists in internal executor
- `/ai/daily_house_summary` exists in `safe_route_allowlist.json`
- agent phrase matching includes house briefing / house summary wording

## Direct endpoint validation

### 1. House state route

Run:

    curl -s http://127.0.0.1:8000/ai/house_state | python3 -m json.tool | sed -n '1,220p'

Expected:
- returns `status: ok`
- includes `summary`
- includes `climate_summary`
- includes `house_sensors`
- includes `energy_flow`

### 2. Daily house summary route

Run:

    curl -s http://127.0.0.1:8000/ai/daily_house_summary | python3 -m json.tool

Expected:
- returns `status: ok`
- includes `spoken_summary`
- includes `energy`, `activity`, `climate`, `infrastructure`
- includes `generated_at`

## Agent query validation

### 1. Climate summary

Run:

    curl -s -X POST http://127.0.0.1:8000/agent/query \
      -H "Content-Type: application/json" \
      -d '{"question":"give me latest temperature and humidity in the house"}' | python3 -m json.tool

Expected:
- routes to `/ai/loxone_history_telemetry_latest`
- returns readable climate summary
- does not fall back to generic unsummarized output

### 2. Most active room

Run:

    curl -s -X POST http://127.0.0.1:8000/agent/query \
      -H "Content-Type: application/json" \
      -d '{"question":"which room seems most active right now"}' | python3 -m json.tool

Expected:
- routes to `/ai/house_sensors`
- returns ranked room reasoning
- does not return room inventory/config list

### 3. House briefing

Run:

    curl -s -X POST http://127.0.0.1:8000/agent/query \
      -H "Content-Type: application/json" \
      -d '{"question":"give me the house briefing"}' | python3 -m json.tool

Expected:
- routes to `/ai/daily_house_summary`
- returns `status: ok`
- answer mirrors `spoken_summary`

### 4. Daily house summary wording

Run:

    curl -s -X POST http://127.0.0.1:8000/agent/query \
      -H "Content-Type: application/json" \
      -d '{"question":"daily house summary"}' | python3 -m json.tool

Expected:
- routes to `/ai/daily_house_summary`
- returns `status: ok`

### 5. General house summary wording

Run:

    curl -s -X POST http://127.0.0.1:8000/agent/query \
      -H "Content-Type: application/json" \
      -d '{"question":"summarize current house status"}' | python3 -m json.tool

    curl -s -X POST http://127.0.0.1:8000/agent/query \
      -H "Content-Type: application/json" \
      -d '{"question":"give me a house summary"}' | python3 -m json.tool

Expected:
- routes to `/ai/daily_house_summary`
- does not fall into stale `house_overview` path
- answer is butler-style summary, not raw meter dump

## Safe execution policy validation

Run:

    cd ~/house-agent
    sed -n '1,220p' house-ai-knowledge/policy/safe_route_allowlist.json

Expected:
- `/ai/daily_house_summary` exists in allowlist

## Regression watch

Check these remain correct:
- `give me latest temperature and humidity in the house`
- `which room seems most active right now`
- `give me the house briefing`
- `daily house summary`
- `summarize current house status`
- `give me a house summary`

## Failure patterns

### If agent says:
`Route not allowed: /ai/daily_house_summary`

Then check:
- `house-ai-knowledge/policy/safe_route_allowlist.json`
- `services/agent_executor.py`
- service restart actually loaded new allowlist

### If direct route works but agent route fails

Then check:
- `services/internal_route_executor.py`
- `services/agent_router_bridge.py`
- route phrase matching order

### If house summary falls back to old energy dump

Then check:
- general house-summary phrases are present in `agent_router_bridge.py`
- old stale `house_overview` path is not being used for natural summary prompts
