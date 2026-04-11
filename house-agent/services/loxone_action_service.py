import requests
from requests.auth import HTTPBasicAuth

from config import LOXONE_HOST, LOXONE_USER, LOXONE_PASSWORD
from services.loxone_service import (
    get_audio_tool_targets,
    find_control_by_name,
    get_audio_action_map,
)

BASE_URL = f"http://{LOXONE_HOST}"


def _auth():
    return HTTPBasicAuth(LOXONE_USER, LOXONE_PASSWORD)


def _get(url: str):
    r = requests.get(url, auth=_auth(), timeout=10)
    r.raise_for_status()
    return r.text.strip()


def trigger_pushbutton(uuid: str):
    url = f"{BASE_URL}/dev/sps/io/{uuid}/Pulse"
    return {
        "status": "ok",
        "action": "pulse",
        "uuid": uuid,
        "response": _get(url),
    }


def set_switch(uuid: str, value: int):
    if value not in (0, 1):
        raise ValueError("Switch value must be 0 or 1")

    url = f"{BASE_URL}/dev/sps/io/{uuid}/{value}"
    return {
        "status": "ok",
        "action": "set_switch",
        "uuid": uuid,
        "value": value,
        "response": _get(url),
    }


def command_on(uuid: str):
    url = f"{BASE_URL}/dev/sps/io/{uuid}/On"
    return {
        "status": "ok",
        "action": "command_on",
        "uuid": uuid,
        "response": _get(url),
    }


def command_off(uuid: str):
    url = f"{BASE_URL}/dev/sps/io/{uuid}/Off"
    return {
        "status": "ok",
        "action": "command_off",
        "uuid": uuid,
        "response": _get(url),
    }


def execute_control(control: dict, desired_state: str):
    """
    Generic/default control execution.
    Keep normal switch handling for node power and other regular controls.
    """
    ctrl = control.get("control", control)
    uuid = ctrl.get("uuid")
    ctrl_type = str(ctrl.get("type") or "").lower()

    if not uuid:
        return {
            "status": "error",
            "message": "Missing control uuid",
            "control": ctrl,
        }

    if ctrl_type == "pushbutton":
        result = trigger_pushbutton(uuid)
        result["resolved_control"] = ctrl
        return result

    if ctrl_type == "switch":
        if desired_state == "on":
            result = set_switch(uuid, 1)
            result["resolved_control"] = ctrl
            return result
        if desired_state == "off":
            result = set_switch(uuid, 0)
            result["resolved_control"] = ctrl
            return result
        return {
            "status": "error",
            "message": "Switch requires on/off desired_state",
            "control": ctrl,
        }

    return {
        "status": "error",
        "message": f"Unsupported control type: {ctrl_type}",
        "uuid": uuid,
        "control": ctrl,
    }


def execute_audio_route_control(control: dict, desired_state: str):
    """
    Speaker module controls proved to require /On and /Off, not /1 and /0.
    """
    ctrl = control.get("control", control)
    uuid = ctrl.get("uuid")
    ctrl_type = str(ctrl.get("type") or "").lower()

    if not uuid:
        return {
            "status": "error",
            "message": "Missing control uuid",
            "control": ctrl,
        }

    if ctrl_type == "pushbutton":
        result = trigger_pushbutton(uuid)
        result["resolved_control"] = ctrl
        return result

    if ctrl_type == "switch":
        if desired_state == "on":
            result = command_on(uuid)
            result["resolved_control"] = ctrl
            return result
        if desired_state == "off":
            result = command_off(uuid)
            result["resolved_control"] = ctrl
            return result
        return {
            "status": "error",
            "message": "Switch requires on/off desired_state",
            "control": ctrl,
        }

    return {
        "status": "error",
        "message": f"Unsupported control type: {ctrl_type}",
        "uuid": uuid,
        "control": ctrl,
    }


def resolve_audio_speaker_route(target: str):
    targets = get_audio_tool_targets()
    key = (target or "").strip().lower()

    if key == "toilet":
        key = "wc"

    for _, room_data in targets.items():
        speaker_targets = room_data.get("speaker_targets", {})
        if key in speaker_targets:
            mapping = speaker_targets[key]
            resolved = find_control_by_name(mapping["room"], mapping["control_name"])
            return {
                "target": target,
                "normalized_target": key,
                "mapping": mapping,
                "resolved": resolved,
            }

    return {
        "status": "error",
        "message": f"Unknown speaker target: {target}",
    }


def audio_node_power(room: str, state: str):
    targets = get_audio_tool_targets()
    room_key = room.lower()

    if room_key not in targets:
        return {"status": "error", "message": f"Unknown audio room: {room}"}

    mapped_room = targets[room_key].get("node_power_room")
    if not mapped_room:
        return {"status": "error", "message": f"No node power room mapped for: {room}"}

    action_map = get_audio_action_map(mapped_room)
    node_power = action_map.get("node_power", {})

    if room_key == "living":
        living_ctrl = node_power.get("PICORE LIVING AUDIO")
        if not living_ctrl:
            return {"status": "error", "message": "Living node power control not found"}
        return execute_control(living_ctrl["switch"], state)

    if room_key == "bathroom":
        paired = node_power.get("paired_buttons", {})
        ctrl = paired.get("on" if state == "on" else "off")
        if not ctrl:
            return {"status": "error", "message": f"Bathroom node power {state} control not found"}
        return execute_control(ctrl, state)

    if room_key == "toilet":
        toilet_ctrl = node_power.get("PICORE TOILET AUDIO")
        if not toilet_ctrl:
            return {"status": "error", "message": "Toilet node power control not found"}
        return execute_control(toilet_ctrl["switch"], state)

    return {"status": "error", "message": f"No node power logic implemented for: {room}"}


def audio_speaker_route(target: str, state: str):
    info = resolve_audio_speaker_route(target)
    if info.get("status") == "error":
        return info

    resolved = info["resolved"]
    if resolved.get("status") != "ok":
        return resolved

    result = execute_audio_route_control(resolved["control"], state)
    return {
        "target": info["target"],
        "normalized_target": info["normalized_target"],
        "mapping": info["mapping"],
        "resolved_control": resolved.get("control"),
        "result": result,
    }


def audio_control_probe(target: str):
    info = resolve_audio_speaker_route(target)
    if info.get("status") == "error":
        return info

    resolved = info["resolved"]
    if resolved.get("status") != "ok":
        return resolved

    ctrl = resolved["control"]
    uuid = ctrl.get("uuid")

    out = {
        "target": info["target"],
        "normalized_target": info["normalized_target"],
        "mapping": info["mapping"],
        "resolved_control": ctrl,
        "tests": {},
    }

    for name, fn in {
        "switch_on": lambda: set_switch(uuid, 1),
        "switch_off": lambda: set_switch(uuid, 0),
        "command_on": lambda: command_on(uuid),
        "command_off": lambda: command_off(uuid),
        "pulse": lambda: trigger_pushbutton(uuid),
    }.items():
        try:
            out["tests"][name] = fn()
        except Exception as e:
            out["tests"][name] = {
                "status": "error",
                "message": str(e),
            }

    return out


def audio_party(state: str):
    targets = get_audio_tool_targets()
    party = targets["living"]["party"]
    control_name = party["on_control"] if state == "on" else party["off_control"]
    resolved = find_control_by_name(party["room"], control_name)

    if resolved.get("status") != "ok":
        return resolved

    result = execute_control(resolved["control"], state)
    return {
        "target": "party",
        "mapping": party,
        "resolved_control": resolved.get("control"),
        "result": result,
    }


def audio_playback(room: str, state: str):
    targets = get_audio_tool_targets()
    room_key = room.lower()

    if room_key not in targets:
        return {"status": "error", "message": f"Unknown playback room: {room}"}

    playback = targets[room_key].get("playback")
    if not playback:
        return {"status": "error", "message": f"No playback mapping for room: {room}"}

    control_name = playback["on_control"] if state == "on" else playback["off_control"]
    resolved = find_control_by_name(playback["room"], control_name)

    if resolved.get("status") != "ok":
        return resolved

    result = execute_control(resolved["control"], state)
    return {
        "room": room,
        "mapping": playback,
        "resolved_control": resolved.get("control"),
        "result": result,
    }
