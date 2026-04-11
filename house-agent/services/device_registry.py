# services/device_registry.py

ROOM_ALIASES = {
    "living": "living",
    "livingroom": "living",

    "wc": "toilet",
    "toilet": "toilet",

    "bath": "bathroom",
    "bathroom": "bathroom",

    "desk": "desk",
    "office": "desk",

    "bass": "bass",
    "berging": "bass",

    "party": "party",
}

AUDIO_TARGETS = {
    "living": {
        "name": "Living Room",
        "player_id": "living",
        "target_type": "player",
        "room": "living",
        "route_mode": "controlled_house_speaker",
        "requires_audio_relay": True,
        "audio_relay_group": "living_speaker_module",
        "speaker_route_target": "living",
        "warmup_seconds": 2.0,
        "release_delay_seconds": 3.0,
        "stop_before_play": True,
        "release_after_play": True,
    },
    "toilet": {
        "name": "Toilet",
        "player_id": "wc",
        "target_type": "player",
        "room": "toilet",
        "route_mode": "controlled_house_speaker",
        "requires_audio_relay": True,
        "audio_relay_group": "living_speaker_module",
        "speaker_route_target": "wc",
        "warmup_seconds": 2.0,
        "release_delay_seconds": 3.0,
        "stop_before_play": True,
        "release_after_play": True,
    },
    "bathroom": {
        "name": "Bathroom",
        "player_id": "bathroom",
        "target_type": "player",
        "room": "bathroom",
        "route_mode": "direct_player",
        "requires_audio_relay": False,
        "audio_relay_group": None,
        "speaker_route_target": None,
        "warmup_seconds": 0.0,
        "release_delay_seconds": 0.0,
        "stop_before_play": True,
        "release_after_play": False,
    },
    "desk": {
        "name": "Desk Speaker",
        "player_id": "desk",
        "target_type": "player",
        "room": "desk",
        "route_mode": "direct_player",
        "requires_audio_relay": False,
        "audio_relay_group": None,
        "speaker_route_target": None,
        "warmup_seconds": 0.0,
        "release_delay_seconds": 0.0,
        "stop_before_play": True,
        "release_after_play": False,
    },
    "bass": {
        "name": "Bass / Berging",
        "player_id": "bass",
        "target_type": "player",
        "room": "berging",
        "route_mode": "controlled_house_speaker",
        "requires_audio_relay": True,
        "audio_relay_group": "living_speaker_module",
        "speaker_route_target": "bass",
        "warmup_seconds": 2.0,
        "release_delay_seconds": 3.0,
        "stop_before_play": True,
        "release_after_play": True,
    },
}

AUDIO_GROUPS = {
    "party": {
        "name": "Party Group",
        "target_type": "group",
        "group_mode": "linked_trigger",
        "description": "Linked multi-speaker group trigger, not a direct speaker endpoint.",
        "on_endpoint": "/tools/music/party/on",
        "off_endpoint": "/tools/music/party/off",
    }
}


def normalize_audio_target(target: str) -> str:
    if not target:
        return "living"
    key = str(target).strip().lower()
    return ROOM_ALIASES.get(key, key)


def get_audio_target_config(target: str) -> dict:
    normalized = normalize_audio_target(target)

    if normalized in AUDIO_TARGETS:
        return {"target_key": normalized, **AUDIO_TARGETS[normalized]}

    if normalized in AUDIO_GROUPS:
        return {"target_key": normalized, **AUDIO_GROUPS[normalized]}

    raise ValueError(f"Unknown audio target: {target}")


def is_playback_target(target: str) -> bool:
    cfg = get_audio_target_config(target)
    return cfg.get("target_type") == "player"


def is_group_target(target: str) -> bool:
    cfg = get_audio_target_config(target)
    return cfg.get("target_type") == "group"


