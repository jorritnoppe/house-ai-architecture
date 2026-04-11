# services/speaker_router_service.py

from services.device_registry import get_audio_target_config, normalize_audio_target
from services.audio_orchestrator import announce


def normalize_speaker(target: str) -> str:
    return normalize_audio_target(target)


def speak_text(text: str, speaker: str = "living", level: str = "attention", volume=None) -> dict:
    normalized = normalize_audio_target(speaker)
    config = get_audio_target_config(normalized)

    if config.get("target_type") != "player":
        return {
            "status": "error",
            "error": f"Target '{normalized}' is not a direct playback target",
            "target": normalized,
            "mode": "invalid_target",
            "result": None,
        }

    result = announce(
        text=text,
        target=normalized,
        priority="normal",
        source="speaker_router",
        level=level,
        volume=volume,
    )

    return {
        "status": result.get("status", "error"),
        "target": normalized,
        "player_id": config.get("player_id"),
        "mode": config.get("route_mode"),
        "result": result,
    }
