import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path("/opt/house-ai")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests
from services.announcement_state_service import clear_announce_key

STATE_FILE = PROJECT_ROOT / "data" / "ups_voice_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

AGENT_URL = "http://127.0.0.1:8000/agent/query"
ANNOUNCE_URL = "http://127.0.0.1:8000/voice/announce_once"

CHECK_INTERVAL_SECONDS = 30
PLAYER_ID = "desk"

ON_BATTERY_KEY = "ups_on_battery_warning"
BACK_ON_MAINS_KEY = "ups_back_on_mains_attention"


def load_state():
    if not STATE_FILE.exists():
        return {"last_on_battery": None}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"last_on_battery": None}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def query_ups_on_battery():
    payload = {"question": "Is my UPS on battery?"}
    response = requests.post(AGENT_URL, json=payload, timeout=20)
    response.raise_for_status()
    data = response.json()

    tool_data = data.get("tool_data", {}) or {}
    ups = tool_data.get("apc_on_battery_status", {}) or {}
    devices = ups.get("devices", []) or []

    on_battery = False
    device_name = "UPS"

    for device in devices:
        status_flags = device.get("status_flags", {}) or {}
        if status_flags.get("onbattery") is True:
            on_battery = True
            device_name = device.get("device", "UPS")
            break

        conclusions = " ".join(device.get("conclusions", [])).lower()
        if "running on battery" in conclusions:
            on_battery = True
            device_name = device.get("device", "UPS")
            break

    return {
        "on_battery": on_battery,
        "device_name": device_name,
        "raw": data,
    }


def announce(text, level, key, cooldown_seconds=300):
    payload = {
        "text": text,
        "level": level,
        "player_id": PLAYER_ID,
        "key": key,
        "cooldown_seconds": cooldown_seconds,
    }
    response = requests.post(ANNOUNCE_URL, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def main():
    while True:
        try:
            state = load_state()
            current = query_ups_on_battery()

            was_on_battery = state.get("last_on_battery")
            now_on_battery = current["on_battery"]
            device_name = current["device_name"]

            if now_on_battery:
                announce(
                    text=f"{device_name} is running on battery",
                    level="warning",
                    key=ON_BATTERY_KEY,
                    cooldown_seconds=300,
                )
            elif was_on_battery:
                announce(
                    text=f"{device_name} is back on mains power",
                    level="attention",
                    key=BACK_ON_MAINS_KEY,
                    cooldown_seconds=120,
                )
                clear_announce_key(ON_BATTERY_KEY)

            state["last_on_battery"] = now_on_battery
            save_state(state)

        except Exception as e:
            print(f"[monitor_ups_voice] error: {e}", flush=True)

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
