# Safe Audio Router Regression Test

## Purpose
Provide a repeatable regression test for the safe audio routing layer after edits to:
- `routes/agent_routes.py`
- `services/ai_safe_action_router.py`
- `services/safe_action_service.py`
- action registry / runtime logic

## Script
Regression script location:

`~/house-agent/test_safe_audio_router.sh`

Make executable:
```bash
sudo chmod +x ~/house-agent/test_safe_audio_router.sh
