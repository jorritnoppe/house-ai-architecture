import json
import time
from pathlib import Path

STATE_FILE = Path("/home/jnoppe/house-agent/data/announcement_state.json")
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def _save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def should_announce(key: str, cooldown_seconds: int = 300) -> bool:
    state = _load_state()
    now = time.time()
    last_ts = state.get(key, 0)

    if now - last_ts < cooldown_seconds:
        return False

    state[key] = now
    _save_state(state)
    return True


def clear_announce_key(key: str):
    state = _load_state()
    if key in state:
        del state[key]
        _save_state(state)
