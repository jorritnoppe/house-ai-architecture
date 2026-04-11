import json
import os
import threading
from pathlib import Path
from extensions import app


import requests
from flask import Blueprint, jsonify, request

house_bp = Blueprint("house", __name__)

ELECTRICPI_BASE_URL = os.getenv("ELECTRICPI_BASE_URL", "http://audio-node.local:8877").rstrip("/")
HOUSE_AGENT_SELF_BASE_URL = os.getenv("HOUSE_AGENT_SELF_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

CONVERSATION_STORE_FILE = Path(
    os.getenv(
        "HOUSE_CONVERSATION_STORE_FILE",
        "/opt/house-ai/data/conversation_last_speaker.json",
    )
)
CONVERSATION_STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
_conversation_lock = threading.Lock()

SPEAKER_DEFAULTS = {
    "living": {
        "volume": 55,
        "start_delay_s": 3,
        "duration_s": 8,
        "release_delay_s": 1,
        "ttl_s": 25,
        "test_text": "Living room test from the safe house endpoint.",
        "mode": "relay_managed",
        "player_id": "living",
    },
    "wc": {
        "volume": 40,
        "start_delay_s": 3,
        "duration_s": 8,
        "release_delay_s": 1,
        "ttl_s": 25,
        "test_text": "WC speaker test from the safe house endpoint.",
        "mode": "relay_managed",
        "player_id": "wc",
    },
    "desk": {
        "volume": 25,
        "start_delay_s": 2,
        "duration_s": 8,
        "release_delay_s": 1,
        "ttl_s": 90,
        "test_text": "Desk speaker test from the safe house endpoint.",
        "mode": "boot_aware_keep_alive",
        "player_id": "desk",
    },


    "party": {
        "player_id": "party",
        "volume": 55.0,
        "start_delay_s": 3.0,
        "duration_s": 8.0,
        "release_delay_s": 1.0,
        "ttl_s": 25.0,
        "mode": "relay_managed",
        "test_text": "Party speaker test from the safe house endpoint."
    },



    "bathroom": {
        "volume": 20,
        "start_delay_s": 2,
        "duration_s": 8,
        "release_delay_s": 1,
        "ttl_s": 90,
        "test_text": "Bathroom speaker test from the safe house endpoint.",
        "mode": "boot_aware_keep_alive",
        "player_id": "bathroom",
    },
}


def _speaker_or_404(speaker: str) -> str:
    speaker = (speaker or "").strip().lower()
    if speaker not in SPEAKER_DEFAULTS:
        raise ValueError(f"Unsupported speaker: {speaker}")
    return speaker







def _audio-node-1_request(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{ELECTRICPI_BASE_URL}{path}"

    if method.upper() == "GET":
        resp = requests.get(url, timeout=(5, 20))
    elif method.upper() == "POST":
        resp = requests.post(url, json=payload or {}, timeout=(5, 60))
    else:
        raise ValueError(f"Unsupported method: {method}")

    resp.raise_for_status()
    return resp.json()


def _local_request(method: str, path: str) -> dict:
    url = f"{HOUSE_AGENT_SELF_BASE_URL}{path}"

    if method.upper() == "GET":
        resp = requests.get(url, timeout=30)
    else:
        raise ValueError(f"Unsupported local method: {method}")

    resp.raise_for_status()
    return resp.json()


def _load_conversation_store() -> dict:
    with _conversation_lock:
        if not CONVERSATION_STORE_FILE.exists():
            return {}

        try:
            with open(CONVERSATION_STORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}


def _save_conversation_store(data: dict) -> None:
    with _conversation_lock:
        tmp_file = CONVERSATION_STORE_FILE.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_file.replace(CONVERSATION_STORE_FILE)


def remember_last_speaker(conversation_id: str, speaker: str) -> None:
    conversation_id = (conversation_id or "").strip()
    speaker = (speaker or "").strip().lower()

    if not conversation_id or not speaker:
        return

    data = _load_conversation_store()
    data[conversation_id] = speaker
    _save_conversation_store(data)


def get_last_speaker(conversation_id: str) -> str | None:
    conversation_id = (conversation_id or "").strip()
    if not conversation_id:
        return None

    data = _load_conversation_store()
    speaker = data.get(conversation_id)
    if not speaker:
        return None

    speaker = str(speaker).strip().lower()
    if speaker not in SPEAKER_DEFAULTS:
        return None

    return speaker


def _build_speaker_payload(speaker: str, payload: dict) -> dict:
    defaults = SPEAKER_DEFAULTS[speaker]

    return {
        "owner": payload.get("owner", "ai"),
        "text": (payload.get("text") or "").strip(),
        "duration_s": float(payload.get("duration_s", defaults["duration_s"])),
        "release_delay_s": float(payload.get("release_delay_s", defaults["release_delay_s"])),
        "ttl_s": float(payload.get("ttl_s", defaults["ttl_s"])),
        "volume": float(payload.get("volume", defaults["volume"])),
        "start_delay_s": float(payload.get("start_delay_s", defaults["start_delay_s"])),
    }


@house_bp.get("/house/status")
def house_status():
    return jsonify({
        "status": "ok",
        "audio-node-1_base_url": ELECTRICPI_BASE_URL,
        "speakers": {
            name: {
                "defaults": cfg,
            }
            for name, cfg in SPEAKER_DEFAULTS.items()
        },
    })


@house_bp.get("/house/speaker/<speaker>/status")
def house_speaker_status(speaker: str):
    try:
        speaker = _speaker_or_404(speaker)
        data = _audio-node-1_request("GET", f"/speaker/{speaker}/status")
        return jsonify(data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "speaker": speaker,
        }), 500


@house_bp.post("/house/speaker/<speaker>/test")
def house_speaker_test(speaker: str):
    try:
        speaker = _speaker_or_404(speaker)
        defaults = SPEAKER_DEFAULTS[speaker]

        audio-node-1_payload = {
            "owner": "ai",
            "text": defaults["test_text"],
            "duration_s": defaults["duration_s"],
            "release_delay_s": defaults["release_delay_s"],
            "ttl_s": defaults["ttl_s"],
            "volume": defaults["volume"],
            "start_delay_s": defaults["start_delay_s"],
        }

        data = _audio-node-1_request("POST", f"/speaker/{speaker}/speak", audio-node-1_payload)
        return jsonify(data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "speaker": speaker,
        }), 500


@house_bp.post("/house/speak/<speaker>")
def house_speak_named(speaker: str):
    try:
        speaker = _speaker_or_404(speaker)
        payload = request.get_json(silent=True) or {}
        conversation_id = (payload.get("conversation_id") or "").strip()

        audio-node-1_payload = _build_speaker_payload(speaker, payload)

        if not audio-node-1_payload["text"]:
            return jsonify({
                "status": "error",
                "message": "missing 'text'",
            }), 400

        app.logger.warning(
            "HOUSE_SPEAK_DEBUG speaker=%s payload=%s base_url=%s",
            speaker,
            audio-node-1_payload,
            ELECTRICPI_BASE_URL,
        )

        data = _audio-node-1_request("POST", f"/speaker/{speaker}/speak", audio-node-1_payload)

        if conversation_id:
            remember_last_speaker(conversation_id, speaker)

        return jsonify(data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "speaker": speaker,
        }), 500



@house_bp.post("/house/speak/all")
def house_speak_all():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    targets = payload.get("targets") or ["living", "wc", "desk", "bathroom"]
    continue_on_error = bool(payload.get("continue_on_error", True))
    conversation_id = (payload.get("conversation_id") or "").strip()
    remember_broadcast_last = bool(payload.get("remember_last", False))

    if not text:
        return jsonify({
            "status": "error",
            "message": "missing 'text'",
        }), 400

    valid_targets = {"living", "wc", "desk", "bathroom"}
    cleaned_targets = []

    for target in targets:
        t = str(target).strip().lower()
        if t in valid_targets and t not in cleaned_targets:
            cleaned_targets.append(t)

    if not cleaned_targets:
        return jsonify({
            "status": "error",
            "message": "no valid targets",
        }), 400

    results = []
    overall_ok = True
    last_successful_speaker = None

    for speaker in cleaned_targets:
        try:
            speaker_payload = _build_speaker_payload(speaker, payload)
            speaker_payload["text"] = text

            data = _audio-node-1_request("POST", f"/speaker/{speaker}/speak", speaker_payload)

            results.append({
                "speaker": speaker,
                "ok": True,
                "result": data,
            })
            last_successful_speaker = speaker

        except Exception as e:
            overall_ok = False
            results.append({
                "speaker": speaker,
                "ok": False,
                "error": str(e),
            })
            if not continue_on_error:
                break

    if conversation_id and remember_broadcast_last and last_successful_speaker:
        remember_last_speaker(conversation_id, last_successful_speaker)

    return jsonify({
        "status": "ok" if overall_ok else "partial_error",
        "text": text,
        "targets": cleaned_targets,
        "results": results,
        "conversation_id": conversation_id or None,
        "remember_last": remember_broadcast_last,
    })


@house_bp.post("/house/speak/last")
def house_speak_last():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    conversation_id = (payload.get("conversation_id") or "").strip()

    if not conversation_id:
        return jsonify({
            "status": "error",
            "message": "missing 'conversation_id'",
        }), 400

    if not text:
        return jsonify({
            "status": "error",
            "message": "missing 'text'",
        }), 400

    speaker = get_last_speaker(conversation_id)
    if not speaker:
        return jsonify({
            "status": "error",
            "message": f"no last speaker stored for conversation_id '{conversation_id}'",
        }), 404

    try:
        audio-node-1_payload = _build_speaker_payload(speaker, payload)
        audio-node-1_payload["text"] = text

        data = _audio-node-1_request("POST", f"/speaker/{speaker}/speak", audio-node-1_payload)

        remember_last_speaker(conversation_id, speaker)

        return jsonify(data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "speaker": speaker,
            "conversation_id": conversation_id,
        }), 500


@house_bp.get("/house/conversation/<conversation_id>/speaker")
def house_conversation_last_speaker(conversation_id: str):
    speaker = get_last_speaker(conversation_id)

    return jsonify({
        "status": "ok",
        "conversation_id": conversation_id,
        "last_speaker": speaker,
    })


@house_bp.get("/house/diagnostics")
def house_diagnostics():
    diagnostics = {
        "status": "ok",
        "audio-node-1_base_url": ELECTRICPI_BASE_URL,
        "house_agent_self_base_url": HOUSE_AGENT_SELF_BASE_URL,
        "audio-node-1_health": None,
        "speakers": {},
        "conversation_last_speaker_map": _load_conversation_store(),
    }

    try:
        diagnostics["audio-node-1_health"] = _audio-node-1_request("GET", "/health")
    except Exception as e:
        diagnostics["audio-node-1_health"] = {
            "status": "error",
            "message": str(e),
        }
        diagnostics["status"] = "partial_error"

    for speaker, cfg in SPEAKER_DEFAULTS.items():
        speaker_entry = {
            "defaults": cfg,
            "audio-node-1_status": None,
            "player_status": None,
        }

        try:
            speaker_entry["audio-node-1_status"] = _audio-node-1_request("GET", f"/speaker/{speaker}/status")
        except Exception as e:
            speaker_entry["audio-node-1_status"] = {
                "status": "error",
                "message": str(e),
            }
            diagnostics["status"] = "partial_error"

        try:
            speaker_entry["player_status"] = _local_request("GET", f"/voice/player_status/{speaker}")
        except Exception as e:
            speaker_entry["player_status"] = {
                "status": "error",
                "message": str(e),
            }
            diagnostics["status"] = "partial_error"

        diagnostics["speakers"][speaker] = speaker_entry

    return jsonify(diagnostics)


@house_bp.get("/house/diagnostics/text")
def house_diagnostics_text():
    try:
        data = house_diagnostics().get_json()
    except Exception as e:
        return f"Diagnostics failed: {e}\n", 500, {"Content-Type": "text/plain; charset=utf-8"}

    lines = []
    lines.append("House AI Diagnostics")
    lines.append("====================")
    lines.append("")
    lines.append(f"audio-node-1 Base URL : {data.get('audio-node-1_base_url')}")
    lines.append(f"House Agent Base URL: {data.get('house_agent_self_base_url')}")
    lines.append(f"Overall Status      : {data.get('status')}")
    lines.append("")

    audio-node-1_health = data.get("audio-node-1_health") or {}
    lines.append("audio-node-1 Health")
    lines.append("-----------------")
    lines.append(json.dumps(audio-node-1_health, indent=2, ensure_ascii=False))
    lines.append("")

    lines.append("Speakers")
    lines.append("--------")
    for speaker, info in (data.get("speakers") or {}).items():
        lines.append(f"{speaker}")
        lines.append(f"  defaults      : {json.dumps(info.get('defaults', {}), ensure_ascii=False)}")
        lines.append(f"  audio-node-1    : {json.dumps(info.get('audio-node-1_status', {}), ensure_ascii=False)}")
        lines.append(f"  player_status : {json.dumps(info.get('player_status', {}), ensure_ascii=False)}")
        lines.append("")

    lines.append("Conversation Last Speaker Map")
    lines.append("-----------------------------")
    lines.append(json.dumps(data.get("conversation_last_speaker_map", {}), indent=2, ensure_ascii=False))
    lines.append("")

    return "\n".join(lines), 200, {"Content-Type": "text/plain; charset=utf-8"}





@house_bp.post("/house/speak/default")
def house_speak_default():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    conversation_id = (payload.get("conversation_id") or "").strip()
    explicit_speaker = (payload.get("speaker") or "").strip().lower()

    if not text:
        return jsonify({
            "status": "error",
            "message": "missing 'text'",
        }), 400

    remembered_speaker = get_last_speaker(conversation_id) if conversation_id else None

    # Explicit speaker must override remembered speaker
    if explicit_speaker:
        speaker = explicit_speaker
        used_conversation_memory = False
        resolution_source = "explicit"
    elif remembered_speaker:
        speaker = remembered_speaker
        used_conversation_memory = True
        resolution_source = "conversation_memory"
    else:
        return jsonify({
            "status": "error",
            "message": "no default speaker could be resolved; provide 'speaker' or use a conversation_id with stored last speaker",
        }), 400

    if speaker not in SPEAKER_DEFAULTS:
        return jsonify({
            "status": "error",
            "message": f"unknown speaker: {speaker}",
        }), 404

    cfg = SPEAKER_DEFAULTS[speaker]

    audio-node-1_payload = {
        "owner": payload.get("owner", "ai"),
        "text": text,
        "volume": payload.get("volume", cfg["volume"]),
        "start_delay_s": payload.get("start_delay_s", cfg["start_delay_s"]),
        "duration_s": payload.get("duration_s", cfg["duration_s"]),
        "release_delay_s": payload.get("release_delay_s", cfg["release_delay_s"]),
        "ttl_s": payload.get("ttl_s", cfg["ttl_s"]),
    }

    try:
        data = _audio-node-1_request("POST", f"/speaker/{speaker}/speak", audio-node-1_payload)

        if conversation_id:
            remember_last_speaker(conversation_id, speaker)

        data["resolved_speaker"] = speaker
        data["used_conversation_memory"] = used_conversation_memory
        data["resolution_source"] = resolution_source
        data["status"] = "ok"

        return jsonify(data)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "resolved_speaker": speaker,
            "used_conversation_memory": used_conversation_memory,
            "resolution_source": resolution_source,
        }), 500




@house_bp.get("/house/help")
def house_help():
    return jsonify({
        "status": "ok",
        "overview": {
            "audio-node-1_base_url": ELECTRICPI_BASE_URL,
            "description": "Safe house speaker control endpoints for AI speech output.",
            "mic_future_note": "Later, room mic nodes can pass origin_room and still use these speaker endpoints explicitly.",
        },
        "speaker_types": {
            "living": "relay-managed speaker path",
            "wc": "relay-managed speaker path",
            "desk": "boot-aware Pi Zero Wi-Fi speaker, kept alive after speech",
            "bathroom": "boot-aware Pi Zero Wi-Fi speaker, kept alive after speech",
        },
        "endpoints": {
            "house_status": "GET /house/status",
            "house_help": "GET /house/help",
            "house_help_text": "GET /house/help/text",
            "house_diagnostics": "GET /house/diagnostics",
            "house_diagnostics_text": "GET /house/diagnostics/text",
            "living_status": "GET /house/speaker/living/status",
            "wc_status": "GET /house/speaker/wc/status",
            "desk_status": "GET /house/speaker/desk/status",
            "bathroom_status": "GET /house/speaker/bathroom/status",
            "living_test": "POST /house/speaker/living/test",
            "wc_test": "POST /house/speaker/wc/test",
            "desk_test": "POST /house/speaker/desk/test",
            "bathroom_test": "POST /house/speaker/bathroom/test",
            "living_speak": "POST /house/speak/living",
            "wc_speak": "POST /house/speak/wc",
            "desk_speak": "POST /house/speak/desk",
            "bathroom_speak": "POST /house/speak/bathroom",
            "broadcast": "POST /house/speak/all",
            "last": "POST /house/speak/last",
            "conversation_last_speaker": "GET /house/conversation/<conversation_id>/speaker",
            "default_speak": "POST /house/speak/default",
        },
        "examples": {
            "living": {
                "cmd": "curl -X POST http://127.0.0.1:8000/house/speak/living -H \"Content-Type: application/json\" -d '{\"text\":\"Hello living room\"}'"
            },
            "wc": {
                "cmd": "curl -X POST http://127.0.0.1:8000/house/speak/wc -H \"Content-Type: application/json\" -d '{\"text\":\"Hello WC\"}'"
            },
            "desk": {
                "cmd": "curl -X POST http://127.0.0.1:8000/house/speak/desk -H \"Content-Type: application/json\" -d '{\"conversation_id\":\"chat-001\",\"text\":\"Hello desk\"}'"
            },
            "bathroom": {
                "cmd": "curl -X POST http://127.0.0.1:8000/house/speak/bathroom -H \"Content-Type: application/json\" -d '{\"text\":\"Hello bathroom\"}'"
            },
            "broadcast": {
                "cmd": "curl -X POST http://127.0.0.1:8000/house/speak/all -H \"Content-Type: application/json\" -d '{\"text\":\"Broadcast test\",\"targets\":[\"living\",\"wc\",\"desk\",\"bathroom\"],\"continue_on_error\":true}'"
            },
            "broadcast_remember": {
                "cmd": "curl -X POST http://127.0.0.1:8000/house/speak/all -H \"Content-Type: application/json\" -d '{\"conversation_id\":\"chat-all-001\",\"text\":\"Broadcast and remember last successful speaker\",\"remember_last\":true}'"
            },
            "last_lookup": {
                "cmd": "curl http://127.0.0.1:8000/house/conversation/chat-001/speaker"
            },
            "last_speak": {
                "cmd": "curl -X POST http://127.0.0.1:8000/house/speak/last -H \"Content-Type: application/json\" -d '{\"conversation_id\":\"chat-001\",\"text\":\"Use same speaker again\"}'"
            },
            "diagnostics": {
                "cmd": "curl http://127.0.0.1:8000/house/diagnostics"
            },
            "default": {
                "cmd": "curl -X POST http://127.0.0.1:8000/house/speak/default -H \"Content-Type: application/json\" -d '{\"conversation_id\":\"chat-001\",\"text\":\"Use last speaker if known, otherwise set speaker explicitly.\"}'"
            },

        },
        "notes": [
            "living and wc are relay-managed with start delay, mute, stop, and release",
            "desk and bathroom are boot-aware and may wait up to the boot timeout before speaking if the player is offline",
            "desk and bathroom are kept alive after speech",
            "all outputs mute to volume 0 and stop before release/cleanup",
            "broadcast does not overwrite last speaker unless remember_last=true is sent",
            "conversation last speaker is stored on disk so it works across gunicorn workers",
            "explicit speaker arguments are fine for now; later room mic origin can choose speaker automatically",
            "default endpoint uses conversation last speaker first, otherwise explicit speaker argument",

        ],
    })


@house_bp.get("/house/help/text")
def house_help_text():
    return """House AI Speaker Help
=====================

Overview
--------
This server exposes safe AI speech endpoints through audio-node-1.

Speaker Types
-------------
living   : relay-managed speaker path
wc       : relay-managed speaker path
desk     : boot-aware Pi Zero Wi-Fi speaker, kept alive after speech
bathroom : boot-aware Pi Zero Wi-Fi speaker, kept alive after speech

Status
------
GET /house/status
GET /house/help
GET /house/help/text
GET /house/diagnostics
GET /house/diagnostics/text
GET /house/speaker/living/status
GET /house/speaker/wc/status
GET /house/speaker/desk/status
GET /house/speaker/bathroom/status
GET /house/conversation/<conversation_id>/speaker

Tests
-----
POST /house/speaker/living/test
POST /house/speaker/wc/test
POST /house/speaker/desk/test
POST /house/speaker/bathroom/test

Speak
-----
POST /house/speak/living
POST /house/speak/wc
POST /house/speak/desk
POST /house/speak/bathroom
POST /house/speak/all
POST /house/speak/last
POST /house/speak/default

Examples
--------
curl -X POST http://127.0.0.1:8000/house/speak/living -H "Content-Type: application/json" -d '{"text":"Hello living room"}'
curl -X POST http://127.0.0.1:8000/house/speak/wc -H "Content-Type: application/json" -d '{"text":"Hello WC"}'
curl -X POST http://127.0.0.1:8000/house/speak/desk -H "Content-Type: application/json" -d '{"conversation_id":"chat-001","text":"Hello desk"}'
curl -X POST http://127.0.0.1:8000/house/speak/bathroom -H "Content-Type: application/json" -d '{"text":"Hello bathroom"}'
curl -X POST http://127.0.0.1:8000/house/speak/all -H "Content-Type: application/json" -d '{"text":"Broadcast test","targets":["living","wc","desk","bathroom"],"continue_on_error":true}'
curl -X POST http://127.0.0.1:8000/house/speak/last -H "Content-Type: application/json" -d '{"conversation_id":"chat-001","text":"Use same speaker again"}'
curl http://127.0.0.1:8000/house/conversation/chat-001/speaker
curl http://127.0.0.1:8000/house/diagnostics
curl http://127.0.0.1:8000/house/diagnostics/text
curl -X POST http://127.0.0.1:8000/house/speak/default -H "Content-Type: application/json" -d '{"conversation_id":"chat-001","text":"Use the remembered speaker"}'
curl -X POST http://127.0.0.1:8000/house/speak/default -H "Content-Type: application/json" -d '{"speaker":"living","text":"Use explicit speaker when no memory exists"}'


Behavior
--------
living/wc:
- acquire relay
- wait start delay
- play speech
- mute
- stop
- release relay

desk/bathroom:
- check if player is alive
- if not alive: boot and wait
- play speech
- mute
- stop
- keep player alive

Broadcast
---------
- sequential
- returns per-speaker results
- does not overwrite last speaker unless remember_last=true is sent

Conversation Memory
-------------------
- explicit speaker call with conversation_id stores last speaker
- /house/speak/last reuses that stored speaker
- stored on disk, so it survives across gunicorn workers
- /house/speak/default uses last speaker from conversation_id first
- if none is stored yet, it can use explicit "speaker"
- otherwise it returns a clear error



Diagnostics
-----------
- audio-node-1 health
- per-speaker audio-node-1 status
- per-speaker player alive status
- default speaker config
- conversation last-speaker map
""", 200, {"Content-Type": "text/plain; charset=utf-8"}
