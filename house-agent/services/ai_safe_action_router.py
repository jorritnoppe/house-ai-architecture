import re

from services.safe_action_service import (
    get_safe_action,
    execute_safe_action,
    get_safe_action_status_summary,
    get_active_safe_actions,
)


CATEGORY_LABELS = {
    "cat1": "ai_can_use_when_needed",
    "cat2": "ai_can_use_when_requested",
    "cat3": "verification_required",
    "cat4": "review_before_run",
    "cat5": "forbidden",
}


def _normalize(text: str) -> str:
    text = str(text or "").strip().lower()
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def _has_words(text: str, words: list[str]) -> bool:
    return all(word in text for word in words)


def _has_turn_on_pattern(text: str) -> bool:
    return _has_words(text, ["turn", "on"])


def _has_turn_off_pattern(text: str) -> bool:
    return _has_words(text, ["turn", "off"])


def _has_put_on_pattern(text: str) -> bool:
    return _has_words(text, ["put", "on"])


def _has_put_off_pattern(text: str) -> bool:
    return _has_words(text, ["put", "off"])


def _has_switch_on_pattern(text: str) -> bool:
    return _has_words(text, ["switch", "on"])


def _has_switch_off_pattern(text: str) -> bool:
    return _has_words(text, ["switch", "off"])


def _friendly_name(action_name: str) -> str:
    mapping = {
        "music_living_start": "Living room music",
        "music_living_stop": "Living room music",
        "music_bathroom_start": "Bathroom music",
        "music_bathroom_stop": "Bathroom music",
        "music_wc_start": "WC music",
        "music_wc_night_start": "WC night music",
        "music_wc_stop": "WC music",
        "music_party_start": "Party mode",
        "music_party_stop": "Party mode",
    }
    return mapping.get(action_name, action_name)


def _active_start_name_for_room(room_key: str) -> str | None:
    mapping = {
        "living": "music_living_start",
        "bathroom": "music_bathroom_start",
        "wc": "music_wc_start",
        "party": "music_party_start",
    }
    return mapping.get(room_key)


def _detect_room_key(text: str) -> str | None:
    t = _normalize(text)

    if any(word in t for word in ["living room", "livingroom", "woonkamer", "downstairs"]):
        return "living"

    if any(word in t for word in ["bathroom", "badkamer", "bath"]):
        return "bathroom"

    if any(word in t for word in ["toilet", "wcroom", "toilet speaker", "wc speaker"]):
        return "wc"

    if any(word in t for word in ["party mode", "party music", "feest"]):
        return "party"

    if " wc " in f" {t} ":
        return "wc"

    if " party " in f" {t} ":
        return "party"

    return None


def _is_explicit_user_request(text: str) -> bool:
    t = _normalize(text)

    request_words = [
        "start",
        "stop",
        "play",
        "enable",
        "disable",
        "music",
        "audio",
        "party",
        "scene",
    ]

    return (
        _contains_any(t, request_words)
        or _has_turn_on_pattern(t)
        or _has_turn_off_pattern(t)
        or _has_put_on_pattern(t)
        or _has_put_off_pattern(t)
        or _has_switch_on_pattern(t)
        or _has_switch_off_pattern(t)
    )


def _is_start_request(text: str) -> bool:
    t = _normalize(text)
    return (
        _contains_any(t, ["start", "play", "enable"])
        or _has_turn_on_pattern(t)
        or _has_put_on_pattern(t)
        or _has_switch_on_pattern(t)
    )


def _is_stop_request(text: str) -> bool:
    t = _normalize(text)
    return (
        _contains_any(t, ["stop", "disable"])
        or _has_turn_off_pattern(t)
        or _has_put_off_pattern(t)
        or _has_switch_off_pattern(t)
    )


def _looks_like_music_or_audio_request(text: str) -> bool:
    t = _normalize(text)
    return _contains_any(
        t,
        [
            "music",
            "audio",
            "party",
            "party mode",
            "party music",
            "scene",
        ],
    )


def _is_global_status_question(text: str) -> bool:
    t = _normalize(text)
    phrases = [
        "what is active",
        "what is running",
        "what music is playing",
        "what is playing",
        "is music playing",
        "status of music",
        "active actions",
        "what audio is active",
    ]
    return _contains_any(t, phrases)


def _is_room_status_question(text: str) -> bool:
    t = _normalize(text)
    room_key = _detect_room_key(t)
    if not room_key:
        return False

    # Never treat clear action requests as status questions.
    if _match_action_name(t):
        return False

    if t.startswith("is "):
        return True

    if t.startswith("what "):
        return True

    if t.startswith("status"):
        return True

    status_words = [
        " active",
        " playing",
        " running",
        " currently",
        " status",
    ]
    padded = f" {t} "
    return _contains_any(padded, status_words)


def _match_action_name(text: str) -> str | None:
    t = _normalize(text)

    living_words = ["living room", "livingroom", "woonkamer", "downstairs"]
    bathroom_words = ["bathroom", "badkamer", "bath"]
    wc_words = ["wc", "toilet", "wcroom", "toilet speaker", "wc speaker"]
    party_words = ["party mode", "party music", "party", "feest"]
    night_words = ["night", "nacht"]

    is_start = _is_start_request(t)
    is_stop = _is_stop_request(t)

    if _contains_any(t, party_words):
        if is_start:
            return "music_party_start"
        if is_stop:
            return "music_party_stop"

    if _contains_any(t, wc_words):
        if is_start and _contains_any(t, night_words):
            return "music_wc_night_start"
        if is_start:
            return "music_wc_start"
        if is_stop:
            return "music_wc_stop"

    if _contains_any(t, bathroom_words):
        if is_start and _looks_like_music_or_audio_request(t):
            return "music_bathroom_start"
        if is_stop and _looks_like_music_or_audio_request(t):
            return "music_bathroom_stop"

    if _contains_any(t, living_words):
        if is_start and _looks_like_music_or_audio_request(t):
            return "music_living_start"
        if is_stop and _looks_like_music_or_audio_request(t):
            return "music_living_stop"

    return None


def _build_summary(action_name: str, execution: dict) -> str:
    if not isinstance(execution, dict):
        return f"Action processed: {action_name}"

    status = execution.get("status")
    reason = execution.get("reason")

    friendly_ok = {
        "music_living_start": "Living room music started.",
        "music_living_stop": "Living room music stopped.",
        "music_bathroom_start": "Bathroom music started.",
        "music_bathroom_stop": "Bathroom music stopped.",
        "music_wc_start": "WC music started.",
        "music_wc_night_start": "WC night music started.",
        "music_wc_stop": "WC music stopped.",
        "music_party_start": "Party mode started.",
        "music_party_stop": "Party mode stopped.",
    }

    if status == "ok" and reason == "noop":
        name = _friendly_name(action_name)
        if action_name.endswith("_start"):
            return f"{name} is already active."
        if action_name.endswith("_stop"):
            return f"{name} is already stopped."
        return f"No change needed for {name}."

    if status == "ok":
        return friendly_ok.get(action_name, f"Action executed: {action_name}")

    if status == "confirmation_required":
        return f"Confirmation required before executing {action_name}."

    if status == "forbidden":
        return f"Action is blocked for AI use: {action_name}."

    if status == "review_required":
        return f"Action requires review before running: {action_name}."

    if status == "error":
        message = execution.get("message") or "Unknown error"
        return f"Action failed: {message}"

    return f"Action processed: {action_name}"


def _build_global_status_summary() -> dict:
    active = get_active_safe_actions()
    active_actions = active.get("active_actions", {})

    if not active_actions:
        return {
            "status": "ok",
            "summary": "No safe audio actions are currently active.",
            "active_actions": {},
            "execution": active,
        }

    labels = []
    for action_name in sorted(active_actions.keys()):
        labels.append(_friendly_name(action_name))

    return {
        "status": "ok",
        "summary": "Active safe actions: " + ", ".join(labels) + ".",
        "active_actions": active_actions,
        "execution": active,
    }


def _build_room_status_summary(text: str) -> dict:
    room_key = _detect_room_key(text)
    active = get_active_safe_actions()
    active_actions = active.get("active_actions", {})

    if not room_key:
        return {
            "status": "ok",
            "summary": "No safe audio actions are currently active.",
            "active_actions": active_actions,
            "execution": active,
            "checked_action_name": None,
            "checked_room": None,
        }

    action_name = _active_start_name_for_room(room_key)
    is_active = bool(action_name and action_name in active_actions)

    room_labels = {
        "living": "Living room music",
        "bathroom": "Bathroom music",
        "wc": "WC music",
        "party": "Party mode",
    }
    label = room_labels.get(room_key, room_key)

    if is_active:
        summary = f"{label} is active."
    else:
        summary = f"{label} is not active."

    return {
        "status": "ok",
        "summary": summary,
        "active_actions": active_actions,
        "execution": active,
        "checked_action_name": action_name,
        "checked_room": room_key,
    }


def route_ai_safe_action(text: str, confirmed: bool = False) -> dict:
    input_text = str(text or "").strip()
    if not input_text:
        return {
            "status": "error",
            "message": "Missing text",
        }

    # Order matters:
    # 1) explicit actions
    # 2) global status
    # 3) room status
    action_name = _match_action_name(input_text)

    if action_name:
        action_info = get_safe_action(action_name)
        if action_info.get("status") != "ok":
            return {
                "status": "error",
                "message": action_info.get("message", "Unknown action lookup failure"),
                "input_text": input_text,
                "action_name": action_name,
            }

        action = action_info.get("action", {}) or {}
        category = str(action.get("category") or "cat3")
        category_label = CATEGORY_LABELS.get(category, category)
        explicit_request = _is_explicit_user_request(input_text)

        if category == "cat5":
            return {
                "status": "forbidden",
                "message": f"Action is forbidden for AI use: {action_name}",
                "input_text": input_text,
                "action_name": action_name,
                "action_info": action_info,
                "summary": _build_summary(action_name, {"status": "forbidden"}),
            }

        if category == "cat4":
            return {
                "status": "review_required",
                "message": f"Action requires manual review before execution: {action_name}",
                "input_text": input_text,
                "action_name": action_name,
                "action_info": action_info,
                "summary": _build_summary(action_name, {"status": "review_required"}),
            }

        if category == "cat2" and not explicit_request:
            return {
                "status": "forbidden",
                "message": f"Action requires an explicit user request: {action_name}",
                "input_text": input_text,
                "action_name": action_name,
                "action_info": action_info,
                "summary": f"Explicit request required for {action_name}.",
            }

        if category == "cat3" and not confirmed:
            execution = {
                "status": "confirmation_required",
                "message": f"Confirmation required before executing action: {action_name}",
                "action_name": action_name,
            }
            return {
                "status": "confirmation_required",
                "input_text": input_text,
                "action_name": action_name,
                "action_info": action_info,
                "execution": execution,
                "summary": _build_summary(action_name, execution),
            }

        execution = execute_safe_action(action_name=action_name, confirmed=confirmed)

        return {
            "status": execution.get("status", "ok"),
            "input_text": input_text,
            "action_name": action_name,
            "action_info": {
                "status": action_info.get("status"),
                "action_name": action_info.get("action_name"),
                "category_label": category_label,
                "action": action_info.get("action"),
            },
            "execution": execution,
            "summary": _build_summary(action_name, execution),
        }

    if _is_global_status_question(input_text):
        status_info = _build_global_status_summary()
        return {
            "status": status_info.get("status", "ok"),
            "input_text": input_text,
            "action_name": None,
            "action_info": None,
            "execution": status_info.get("execution", get_safe_action_status_summary()),
            "summary": status_info.get("summary", "No status available."),
            "active_actions": status_info.get("active_actions", {}),
            "checked_room": None,
            "checked_action_name": None,
        }

    if _is_room_status_question(input_text):
        room_status = _build_room_status_summary(input_text)
        return {
            "status": room_status.get("status", "ok"),
            "input_text": input_text,
            "action_name": None,
            "action_info": None,
            "execution": room_status.get("execution", get_safe_action_status_summary()),
            "summary": room_status.get("summary", "No status available."),
            "active_actions": room_status.get("active_actions", {}),
            "checked_room": room_status.get("checked_room"),
            "checked_action_name": room_status.get("checked_action_name"),
        }

    return {
        "status": "error",
        "message": "No safe action matched this request.",
        "input_text": input_text,
    }
