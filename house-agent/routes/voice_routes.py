from services.voice_service import stop_player

from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory

from services.voice_service import (
    VOICE_DIR,
    get_players,
    say_text,
    set_player_volume,
    mute_player,
    stop_player,
    resolve_player_id,

)


from services.announcement_service import announce_text
from services.announcement_state_service import should_announce


import json
from pathlib import Path




voice_bp = Blueprint("voice", __name__)



@voice_bp.get("/voice/status")
def voice_status():
    return jsonify({
        "status": "ok",
        "default_player": "desk",
        "available_players": ["desk", "living", "livingarea", "toilet", "bass"],
        "quiet_hours_start": 22,
        "quiet_hours_end": 7,
        "log_file": "/opt/house-ai/data/announcement_log.jsonl",
        "ups_monitor_service": "ups-voice-monitor.service",
    })





@voice_bp.get("/voice/logs")
def voice_logs():
    log_file = Path("/opt/house-ai/data/announcement_log.jsonl")
    limit = int(request.args.get("limit", 20))

    if not log_file.exists():
        return jsonify({
            "status": "ok",
            "logs": [],
        })

    lines = log_file.read_text(encoding="utf-8").splitlines()
    lines = lines[-limit:]

    logs = []
    for line in lines:
        try:
            logs.append(json.loads(line))
        except Exception:
            pass

    return jsonify({
        "status": "ok",
        "count": len(logs),
        "logs": logs,
    })


@voice_bp.post("/voice/announce")
def voice_announce():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    player_id = (payload.get("player_id") or "").strip()
    volume = payload.get("volume")
    level = (payload.get("level") or "attention").strip().lower()

    if not text:
        return jsonify({
            "status": "error",
            "message": "missing 'text'",
        }), 400

    try:
        result = announce_text(
            text=text,
            level=level,
            player_id=player_id,
            volume=volume,
        )
        return jsonify({
            "status": "ok",
            **result,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500




@voice_bp.get("/voice/players")
def voice_players():
    try:
        players = get_players()
        return jsonify({
            "status": "ok",
            "players": players,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@voice_bp.post("/voice/volume")
def voice_volume():
    payload = request.get_json(silent=True) or {}
    player_id = (payload.get("player_id") or "").strip()
    volume = payload.get("volume")

    try:
        result = set_player_volume(player_id=player_id, volume=volume)
        return jsonify({
            "status": "ok",
            **result,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500

@voice_bp.post("/voice/stop")
def voice_stop():
    payload = request.get_json(silent=True) or {}
    player = payload.get("player", "")
    data = stop_player(player)
    return jsonify({
        "status": "ok",
        **data,
    })


@voice_bp.post("/voice/say")
def voice_say():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    player_id = (payload.get("player_id") or "").strip()
    volume = payload.get("volume")

    if not text:
        return jsonify({
            "status": "error",
            "message": "missing 'text'",
        }), 400

    try:
        result = say_text(text, player_id=player_id, volume=volume)
        return jsonify({
            "status": "ok",
            **result,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@voice_bp.get("/voice/files/<path:filename>")
def voice_file(filename):
    return send_from_directory(str(Path(VOICE_DIR)), filename, mimetype="audio/wav")




@voice_bp.post("/voice/announce_once")
def voice_announce_once():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    player_id = (payload.get("player_id") or "").strip()
    volume = payload.get("volume")
    level = (payload.get("level") or "attention").strip().lower()
    key = (payload.get("key") or text).strip()
    cooldown_seconds = int(payload.get("cooldown_seconds", 300))

    if not text:
        return jsonify({
            "status": "error",
            "message": "missing 'text'",
        }), 400

    if not should_announce(key, cooldown_seconds=cooldown_seconds):
        return jsonify({
            "status": "skipped",
            "reason": "cooldown_active",
            "key": key,
        })

    try:
        result = announce_text(
            text=text,
            level=level,
            player_id=player_id,
            volume=volume,
        )
        return jsonify({
            "status": "ok",
            **result,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500



@voice_bp.post("/voice/player_action")
def voice_player_action():
    payload = request.get_json(silent=True) or {}
    player_id = (payload.get("player_id") or "").strip()
    action = (payload.get("action") or "").strip().lower()

    try:
        if action == "stop":
            result = stop_player(player_id)
        elif action == "mute":
            result = mute_player(player_id)
        else:
            return jsonify({
                "status": "error",
                "message": "unsupported action",
            }), 400

        return jsonify({
            "status": "ok",
            **result,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500




@voice_bp.get("/voice/player_status/<player_key>")
def voice_player_status(player_key):
    try:
        resolved_id = resolve_player_id(player_key)
        players = get_players()

        for player in players:
            if player.get("playerid") == resolved_id:
                return jsonify({
                    "status": "ok",
                    "player_key": player_key,
                    "player_id": resolved_id,
                    "alive": bool(player.get("connected", 0)),
                    "player": player,
                })

        return jsonify({
            "status": "ok",
            "player_key": player_key,
            "player_id": resolved_id,
            "alive": False,
            "player": None,
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500



