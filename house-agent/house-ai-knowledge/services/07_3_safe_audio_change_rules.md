# 07_3 Safe Audio Change Rules

## Purpose
This file defines the editing rules for the safe audio router so future changes do not keep breaking working behavior.

---

## Rule 1
Do not change router phrase logic without first adding the intended phrase to:
- `07_2_safe_audio_aliases.md`
- `~/house-agent/test_safe_audio_router.sh`

---

## Rule 2
Always preserve this decision order inside the router:

1. explicit action request
2. global status request
3. room-specific status request
4. fallback to normal agent logic

If this order changes, regression risk becomes high.

---

## Rule 3
Do not copy Flask route code into `services/ai_safe_action_router.py`.

That file must only contain router logic.
It must not contain:
- Flask blueprints
- route handlers
- `jsonify`
- `request`

---

## Rule 4
Do not import `services.ai_safe_action_router` from `services.safe_action_service`.

That creates circular-import risk.

Safe dependency direction is:
- `routes/agent_routes.py` -> `services.ai_safe_action_router`
- `services.ai_safe_action_router.py` -> `services.safe_action_service`
- `routes/safe_action_routes.py` -> `services.safe_action_service`

Not the other way around.

---

## Rule 5
Every router edit must be followed by:

```bash
cd ~/house-agent
source venv/bin/activate

python3 -m py_compile services/safe_action_service.py
python3 -m py_compile services/ai_safe_action_router.py
python3 -m py_compile routes/safe_action_routes.py
python3 -m py_compile routes/agent_routes.py

sudo systemctl restart house-agent.service
sleep 2
systemctl status house-agent.service --no-pager -l
./test_safe_audio_router.sh
