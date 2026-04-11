import json
import os
import subprocess
import time

from services.loxone_service import get_sensor_inventory, fetch_loxone_state_value
from services.loxone_control_service import press_control, set_switch_control


POLICY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "house-ai-knowledge",
    "policy",
)

ALLOWLIST_PATH = os.path.join(POLICY_DIR, "action_allowlist.json")
REGISTRY_PATH = os.path.join(POLICY_DIR, "action_registry.json")
STATE_PATH = os.path.join(POLICY_DIR, "action_runtime_state.json")


def _load_json_file(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json_file(path: str, data):
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def _load_allowlist():
    data = _load_json_file(ALLOWLIST_PATH, {})
    if not isinstance(data, dict):
        return {}
    return data


def _load_registry():
    data = _load_json_file(REGISTRY_PATH, {"actions": {}})
    if not isinstance(data, dict):
        return {"actions": {}}
    if "actions" not in data or not isinstance(data["actions"], dict):
        data["actions"] = {}
    return data


def _load_runtime_state():
    data = _load_json_file(STATE_PATH, {"actions": {}})
    if not isinstance(data, dict):
        return {"actions": {}}
    if "actions" not in data or not isinstance(data["actions"], dict):
        data["actions"] = {}
    return data


def _save_runtime_state(data: dict):
    if not isinstance(data, dict):
        data = {"actions": {}}
    if "actions" not in data or not isinstance(data["actions"], dict):
        data["actions"] = {}
    _save_json_file(STATE_PATH, data)


def _get_action_runtime_entry(action_name: str) -> dict:
    state = _load_runtime_state()
    return state.get("actions", {}).get(action_name, {})


def _set_action_runtime_entry(action_name: str, entry: dict):
    state = _load_runtime_state()
    actions = state.setdefault("actions", {})
    actions[action_name] = entry
    _save_runtime_state(state)


def _mark_action_active(action_name: str, active: bool):
    entry = _get_action_runtime_entry(action_name)
    entry["active"] = bool(active)
    entry["updated_at"] = int(time.time())
    _set_action_runtime_entry(action_name, entry)


def _is_action_active(action_name: str) -> bool:
    entry = _get_action_runtime_entry(action_name)
    return bool(entry.get("active", False))


def _all_inventory_items():
    inventory = get_sensor_inventory()
    return inventory.get("items", []) if isinstance(inventory, dict) else []


def _find_control_by_name(control_name: str):
    wanted = str(control_name or "").strip().lower()
    if not wanted:
        return None

    for item in _all_inventory_items():
        if str(item.get("name") or "").strip().lower() == wanted:
            return item
    return None


def _category_map():
    return {
        "cat1": "ai_can_use_when_needed",
        "cat2": "ai_can_use_when_requested",
        "cat3": "verification_required",
        "cat4": "review_before_run",
        "cat5": "forbidden",
    }


def get_safe_action_inventory():
    allowlist = _load_allowlist()
    items = _all_inventory_items()

    allowed = {}
    blocked_count = 0

    for domain, names in allowlist.items():
        if not isinstance(names, list):
            continue

        allowed[domain] = []
        names_set = set(names)

        for item in items:
            item_name = str(item.get("name") or "")
            if item_name in names_set:
                allowed[domain].append({
                    "uuid": item.get("uuid"),
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "room_name": item.get("room_name"),
                    "domain": item.get("domain"),
                    "sensor_type": item.get("sensor_type"),
                    "states": item.get("states", {}),
                })

    allowed_names = set()
    for names in allowlist.values():
        if isinstance(names, list):
            allowed_names.update(names)

    for item in items:
        if str(item.get("name") or "") not in allowed_names:
            blocked_count += 1

    for domain in allowed:
        allowed[domain] = sorted(
            allowed[domain],
            key=lambda x: (
                str(x.get("room_name") or ""),
                str(x.get("name") or "")
            )
        )

    return {
        "status": "ok",
        "allowed": allowed,
        "blocked_count": blocked_count,
    }


def validate_safe_action(control_name: str):
    allowlist = _load_allowlist()
    control = _find_control_by_name(control_name)

    if not control:
        return {
            "status": "error",
            "message": f"Control not found: {control_name}",
        }

    control_name_real = str(control.get("name") or "")
    allowed_domain = None

    for domain, names in allowlist.items():
        if isinstance(names, list) and control_name_real in names:
            allowed_domain = domain
            break

    if not allowed_domain:
        return {
            "status": "forbidden",
            "message": f"Control is not allowlisted: {control_name_real}",
            "control": {
                "name": control.get("name"),
                "room_name": control.get("room_name"),
                "type": control.get("type"),
                "domain": control.get("domain"),
                "sensor_type": control.get("sensor_type"),
            }
        }

    return {
        "status": "ok",
        "domain": allowed_domain,
        "control": control,
    }


def get_safe_action(action_name: str):
    registry = _load_registry()
    actions = registry.get("actions", {})
    action = actions.get(action_name)

    if not action:
        return {
            "status": "error",
            "message": f"Unknown action: {action_name}",
        }

    category_labels = _category_map()
    category = str(action.get("category") or "cat3")

    return {
        "status": "ok",
        "action_name": action_name,
        "action": action,
        "category_label": category_labels.get(category, category),
    }


def list_safe_actions():
    registry = _load_registry()
    actions = registry.get("actions", {})
    category_labels = _category_map()

    result = {}
    for action_name, action in sorted(actions.items()):
        category = str(action.get("category") or "cat3")
        result[action_name] = {
            "category": category,
            "category_label": category_labels.get(category, category),
            "description": action.get("description"),
            "confirmation_required": bool(action.get("confirmation_required", False)),
            "step_count": len(action.get("steps", [])),
            "cleanup_steps": len(action.get("cleanup_steps", [])) if isinstance(action.get("cleanup_steps"), list) else 0,
        }

    return {
        "status": "ok",
        "actions": result,
    }


def _ping_host(host: str, timeout_seconds: int = 2) -> bool:
    if not host:
        return False

    cmd = [
        "ping",
        "-c", "1",
        "-W", str(int(timeout_seconds)),
        host,
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _read_switch_state(control):
    states = control.get("states", {}) or {}
    state_uuid = states.get("active")
    if not state_uuid:
        return None

    try:
        live = fetch_loxone_state_value(state_uuid)
    except Exception:
        return None

    if not isinstance(live, dict):
        return None

    value = live.get("value")
    try:
        return int(float(value))
    except Exception:
        value_str = str(value).lower()
        if value_str in {"true", "on"}:
            return 1
        if value_str in {"false", "off"}:
            return 0
    return None


def _set_switch_if_needed(control_name: str, desired_value: int):
    validation = validate_safe_action(control_name)
    if validation.get("status") != "ok":
        return validation

    control = validation["control"]
    room_name = str(control.get("room_name") or "")
    ctrl_type = str(control.get("type") or "").lower()

    if ctrl_type != "switch":
        return {
            "status": "error",
            "message": f"Control is not a switch: {control_name}",
        }

    current = _read_switch_state(control)
    if current == desired_value:
        return {
            "status": "ok",
            "mode": "already_set",
            "control_name": control_name,
            "room_name": room_name,
            "current_state": current,
        }

    result = set_switch_control(
        room_name=room_name,
        control_name=control_name,
        value=desired_value,
    )

    return {
        "status": "ok",
        "mode": "switch_set",
        "control_name": control_name,
        "room_name": room_name,
        "previous_state": current,
        "requested_value": desired_value,
        "result": result,
    }


def _execute_step(step: dict):
    control_name = step.get("control_name")
    if not control_name:
        return {
            "status": "error",
            "message": "Step missing control_name",
            "step": step,
        }

    action = str(step.get("action") or "").lower()

    if action == "ensure_host_online":
        host = str(step.get("host") or "").strip()
        verify = step.get("verify", {}) or {}
        method = str(verify.get("method") or "ping").lower()
        timeout_seconds = int(verify.get("timeout_seconds", 2))
        retries = int(verify.get("retries", 2))
        power_on_wait_seconds = int(step.get("power_on_wait_seconds", 30))

        validation = validate_safe_action(control_name)
        if validation.get("status") != "ok":
            return validation

        control = validation["control"]
        room_name = str(control.get("room_name") or "")

        if method != "ping":
            return {
                "status": "error",
                "message": f"Unsupported verify method: {method}",
                "control_name": control_name,
                "room_name": room_name,
            }

        for _ in range(retries):
            if _ping_host(host, timeout_seconds=timeout_seconds):
                return {
                    "status": "ok",
                    "mode": "host_already_online",
                    "control_name": control_name,
                    "room_name": room_name,
                    "host": host,
                }

        switch_result = _set_switch_if_needed(control_name, 1)
        if switch_result.get("status") != "ok":
            return switch_result

        time.sleep(power_on_wait_seconds)

        for _ in range(retries):
            if _ping_host(host, timeout_seconds=timeout_seconds):
                return {
                    "status": "ok",
                    "mode": "host_powered_on_and_online",
                    "control_name": control_name,
                    "room_name": room_name,
                    "host": host,
                    "power_result": switch_result,
                }

        return {
            "status": "error",
            "message": f"Host did not come online after power-on: {host}",
            "control_name": control_name,
            "room_name": room_name,
            "host": host,
            "power_result": switch_result,
        }

    validation = validate_safe_action(control_name)
    if validation.get("status") != "ok":
        return validation

    control = validation["control"]
    ctrl_type = str(control.get("type") or "").lower()
    room_name = str(control.get("room_name") or "")

    if action == "ensure_on":
        if ctrl_type != "switch":
            return {
                "status": "error",
                "message": f"ensure_on requires switch control: {control_name}",
            }

        current = _read_switch_state(control)
        if current == 1:
            return {
                "status": "ok",
                "mode": "already_on",
                "control_name": control_name,
                "room_name": room_name,
                "previous_state": current,
            }

        result = set_switch_control(room_name=room_name, control_name=control_name, value=1)
        return {
            "status": "ok",
            "mode": "switch_on",
            "control_name": control_name,
            "room_name": room_name,
            "previous_state": current,
            "result": result,
        }

    if action == "ensure_off":
        if ctrl_type != "switch":
            return {
                "status": "error",
                "message": f"ensure_off requires switch control: {control_name}",
            }

        current = _read_switch_state(control)
        if current == 0:
            return {
                "status": "ok",
                "mode": "already_off",
                "control_name": control_name,
                "room_name": room_name,
                "previous_state": current,
            }

        result = set_switch_control(room_name=room_name, control_name=control_name, value=0)
        return {
            "status": "ok",
            "mode": "switch_off",
            "control_name": control_name,
            "room_name": room_name,
            "previous_state": current,
            "result": result,
        }

    if action == "set_value":
        if ctrl_type != "switch":
            return {
                "status": "error",
                "message": f"set_value currently only supports switch controls: {control_name}",
            }

        value = step.get("value", 0)
        current = _read_switch_state(control)
        result = set_switch_control(room_name=room_name, control_name=control_name, value=value)
        return {
            "status": "ok",
            "mode": "switch_set",
            "control_name": control_name,
            "room_name": room_name,
            "previous_state": current,
            "requested_value": value,
            "result": result,
        }

    if action == "press":
        result = press_control(room_name=room_name, control_name=control_name)
        return {
            "status": "ok",
            "mode": "button_press",
            "control_name": control_name,
            "room_name": room_name,
            "result": result,
        }

    return {
        "status": "error",
        "message": f"Unsupported step action: {action}",
        "step": step,
    }


def _run_steps(steps: list[dict]):
    results = []
    for step in steps:
        result = _execute_step(step)
        results.append(result)
        if result.get("status") != "ok":
            return {
                "status": "error",
                "failed_step": step,
                "results": results,
            }
    return {
        "status": "ok",
        "results": results,
    }


def _action_is_start(action_name: str) -> bool:
    return action_name.endswith("_start")


def _action_is_stop(action_name: str) -> bool:
    return action_name.endswith("_stop")


def _action_already_in_target_state(action_name: str) -> bool:
    if _action_is_start(action_name):
        return _is_action_active(action_name)
    if _action_is_stop(action_name):
        paired_start = action_name.replace("_stop", "_start")
        return not _is_action_active(paired_start)
    return False


def execute_safe_action(action_name: str, confirmed: bool = False):
    registry = _load_registry()
    actions = registry.get("actions", {})
    action = actions.get(action_name)

    if not action:
        return {
            "status": "error",
            "message": f"Unknown action: {action_name}",
        }

    category = str(action.get("category") or "cat3")
    confirmation_required = bool(action.get("confirmation_required", False))

    if category == "cat5":
        return {
            "status": "forbidden",
            "message": f"Action is forbidden for AI use: {action_name}",
            "action_name": action_name,
        }

    if category == "cat4":
        return {
            "status": "forbidden",
            "message": f"Action requires manual review before execution: {action_name}",
            "action_name": action_name,
        }

    if category == "cat3" or confirmation_required:
        if not confirmed:
            return {
                "status": "confirmation_required",
                "message": f"Confirmation required before executing action: {action_name}",
                "action_name": action_name,
            }

    steps = action.get("steps", [])
    cleanup_steps = action.get("cleanup_steps", [])

    if not isinstance(steps, list) or not steps:
        return {
            "status": "error",
            "message": f"Action has no steps: {action_name}",
            "action_name": action_name,
        }

    if _action_already_in_target_state(action_name):
        return {
            "status": "ok",
            "reason": "noop",
            "action_name": action_name,
            "category": category,
            "results": [],
        }

    execution = _run_steps(steps)
    if execution.get("status") != "ok":
        return {
            "status": "error",
            "action_name": action_name,
            "failed_step": execution.get("failed_step"),
            "results": execution.get("results", []),
        }

    results = list(execution.get("results", []))

    if _action_is_start(action_name):
        _mark_action_active(action_name, True)

    if _action_is_stop(action_name):
        paired_start = action_name.replace("_stop", "_start")
        _mark_action_active(paired_start, False)

        if isinstance(cleanup_steps, list) and cleanup_steps:
            cleanup_execution = _run_steps(cleanup_steps)
            cleanup_result = {
                "phase": "cleanup",
                "status": cleanup_execution.get("status"),
                "results": cleanup_execution.get("results", []),
            }
            results.append(cleanup_result)

            if cleanup_execution.get("status") != "ok":
                return {
                    "status": "error",
                    "action_name": action_name,
                    "message": "Main stop action succeeded, but cleanup failed.",
                    "results": results,
                }

    return {
        "status": "ok",
        "action_name": action_name,
        "category": category,
        "results": results,
    }


def get_safe_action_runtime_state():
    state = _load_runtime_state()
    return {
        "status": "ok",
        "state": state,
    }


def get_active_safe_actions():
    registry = _load_registry()
    actions = registry.get("actions", {})
    active_actions = {}

    for action_name in sorted(actions.keys()):
        if _action_is_start(action_name) and _is_action_active(action_name):
            active_actions[action_name] = _get_action_runtime_entry(action_name)

    return {
        "status": "ok",
        "count": len(active_actions),
        "active_action_names": sorted(active_actions.keys()),
        "active_actions": active_actions,
    }


def get_safe_action_status_summary():
    active = get_active_safe_actions()
    return {
        "status": "ok",
        "count": active.get("count", 0),
        "active_action_names": active.get("active_action_names", []),
        "active_actions": active.get("active_actions", {}),
    }
