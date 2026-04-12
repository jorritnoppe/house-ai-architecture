import json
import os
import time
from datetime import datetime, timezone

AUDIT_LOG_PATH = "/home/jnoppe/house-agent/services/experimental_audit.log"
COOLDOWN_STATE_PATH = "/home/jnoppe/house-agent/services/experimental_cooldowns.json"


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_experimental_audit(
    event: str,
    tool_name: str | None = None,
    args: dict | None = None,
    source: str | None = None,
    status: str | None = None,
    details: str | None = None,
):
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)

    entry = {
        "timestamp": utc_now_iso(),
        "event": event,
        "tool_name": tool_name,
        "args": args or {},
        "source": source,
        "status": status,
        "details": details,
    }

    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _load_cooldowns() -> dict:
    if not os.path.exists(COOLDOWN_STATE_PATH):
        return {}

    try:
        with open(COOLDOWN_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cooldowns(data: dict):
    os.makedirs(os.path.dirname(COOLDOWN_STATE_PATH), exist_ok=True)
    with open(COOLDOWN_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def check_experimental_cooldown(tool_name: str, cooldown_seconds: int = 10) -> dict:
    now_ts = time.time()
    state = _load_cooldowns()

    last_ts = float(state.get(tool_name, 0))
    wait_seconds = int(round((last_ts + cooldown_seconds) - now_ts))

    if now_ts < last_ts + cooldown_seconds:
        return {
            "ok": False,
            "tool_name": tool_name,
            "cooldown_seconds": cooldown_seconds,
            "wait_seconds": max(wait_seconds, 1),
        }

    return {
        "ok": True,
        "tool_name": tool_name,
        "cooldown_seconds": cooldown_seconds,
        "wait_seconds": 0,
    }


def mark_experimental_cooldown(tool_name: str):
    state = _load_cooldowns()
    state[tool_name] = time.time()
    _save_cooldowns(state)



def write_package_install_audit(
    package_name: str,
    status: str,
    details: str = "",
    source: str = "api",
):
    write_experimental_audit(
        event="package_install",
        tool_name=package_name,
        args={"package_name": package_name},
        source=source,
        status=status,
        details=details,
    )
