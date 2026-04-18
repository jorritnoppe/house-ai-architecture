import requests

LMS_URL = "http://192.168.1.15:9000/jsonrpc.js"

PLAYERS = {
    "toilet": {
        "mac": "d8:3a:dd:af:ea:3e",
        "volume": 35,
    },
    "living": {
        "mac": "d8:3a:dd:3e:08:37",
        "volume": 35,
    },
    "bathroom": {
        "mac": "b8:27:eb:58:aa:97",
        "volume": 40,
    },
    "desk": {
        "mac": "b8:27:eb:55:b2:8d",
        "volume": 35,
    },
}

AI_HOUSE_PLAYLIST = "/mnt/Trueshare/Music/ai-house/meta/enabled_playlist.m3u"


def _post_lms(player_mac: str, command: list):
    payload = {
        "id": 1,
        "method": "slim.request",
        "params": [player_mac, command],
    }
    response = requests.post(LMS_URL, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def play_ai_house_music(target: str):
    player = PLAYERS.get(str(target or "").strip().lower())
    if not player:
        return {
            "status": "error",
            "error": f"Unknown player target: {target}",
        }

    player_mac = player["mac"]
    volume = int(player["volume"])

    try:
        _post_lms(player_mac, ["mixer", "volume", str(volume)])
        _post_lms(player_mac, ["playlist", "load", AI_HOUSE_PLAYLIST])
        _post_lms(player_mac, ["playlist", "shuffle", "1"])
        _post_lms(player_mac, ["play"])

        return {
            "status": "ok",
            "target": target,
            "player_mac": player_mac,
            "volume": volume,
            "playlist": AI_HOUSE_PLAYLIST,
            "answer": f"Started AI house music on {target}.",
        }
    except Exception as e:
        return {
            "status": "error",
            "target": target,
            "error": str(e),
        }


def stop_room_music(target: str):
    player = PLAYERS.get(str(target or "").strip().lower())
    if not player:
        return {
            "status": "error",
            "error": f"Unknown player target: {target}",
        }

    player_mac = player["mac"]

    try:
        _post_lms(player_mac, ["mixer", "volume", "0"])
        _post_lms(player_mac, ["stop"])

        return {
            "status": "ok",
            "target": target,
            "player_mac": player_mac,
            "answer": f"Stopped music on {target}.",
        }
    except Exception as e:
        return {
            "status": "error",
            "target": target,
            "error": str(e),
        }
