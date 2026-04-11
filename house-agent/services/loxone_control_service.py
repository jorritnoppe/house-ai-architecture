import requests
from requests.auth import HTTPBasicAuth

from config import LOXONE_HOST, LOXONE_USER, LOXONE_PASSWORD
from services.loxone_service import get_controls_by_room, resolve_room_name


BASE_URL = f"http://{LOXONE_HOST}"


def _auth():
    return HTTPBasicAuth(LOXONE_USER, LOXONE_PASSWORD)


def _find_control(room_name: str, control_name: str):
    resolved_room = resolve_room_name(room_name)
    controls = get_controls_by_room(resolved_room).get("items", [])

    wanted = str(control_name or "").strip().lower()

    for item in controls:
        name = str(item.get("name") or "").strip().lower()
        if name == wanted:
            return item

    return None


def press_control(room_name: str, control_name: str):
    control = _find_control(room_name, control_name)
    if not control:
        raise ValueError(f"Control not found: room={room_name}, control={control_name}")

    uuid = control.get("uuid")
    if not uuid:
        raise ValueError(f"Control has no uuid: {control_name}")

    url = f"{BASE_URL}/jdev/sps/io/{uuid}/Pulse"
    response = requests.get(url, auth=_auth(), timeout=10)
    response.raise_for_status()

    return {
        "status": "ok",
        "action": "pulse",
        "room_name": room_name,
        "control_name": control_name,
        "uuid": uuid,
        "response_text": response.text.strip()
    }


def set_switch_control(room_name: str, control_name: str, value):
    control = _find_control(room_name, control_name)
    if not control:
        raise ValueError(f"Control not found: room={room_name}, control={control_name}")

    uuid = control.get("uuid")
    if not uuid:
        raise ValueError(f"Control has no uuid: {control_name}")

    normalized = 1 if str(value).strip() in {"1", "true", "on", "True"} else 0

    url = f"{BASE_URL}/jdev/sps/io/{uuid}/{normalized}"
    response = requests.get(url, auth=_auth(), timeout=10)
    response.raise_for_status()

    return {
        "status": "ok",
        "action": "set_switch",
        "room_name": room_name,
        "control_name": control_name,
        "uuid": uuid,
        "value": normalized,
        "response_text": response.text.strip()
    }
