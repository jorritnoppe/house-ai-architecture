from __future__ import annotations

import re
from typing import Optional

from services.device_registry import normalize_audio_target


_OUTPUT_PATTERNS = [
    r"\boutput in (?P<target>[a-zA-Z ]+)\b",
    r"\bplay (?:it|that|the answer) in (?P<target>[a-zA-Z ]+)\b",
    r"\bsay (?:it|that|the answer) in (?P<target>[a-zA-Z ]+)\b",
    r"\bannounce (?:it|that|the answer) in (?P<target>[a-zA-Z ]+)\b",
    r"\bon (?P<target>[a-zA-Z ]+) speaker(?:s)?\b",
]


_STOP_WORDS = {
    "please",
    "now",
    "thanks",
    "thank you",
}


_TARGET_NORMALIZATION = {
    "living room": "livingroom",
    "living-room": "livingroom",
    "desk room": "desk",
    "deskroom": "desk",
    "office": "desk",
    "toilet room": "toilet",
    "bath room": "bathroom",
    "master bedroom": "masterbedroom",
    "child room": "childroom",
}


def _clean_target_text(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[,.!?;:]+$", "", value).strip()
    value = re.sub(r"\s+", " ", value)

    for stop in sorted(_STOP_WORDS, key=len, reverse=True):
        if value.endswith(f" {stop}"):
            value = value[: -len(stop)].strip()
        elif value == stop:
            value = ""

    return value.strip()


def _normalize_spoken_target(text: str) -> str:
    value = _clean_target_text(text)
    if not value:
        return value

    if value in _TARGET_NORMALIZATION:
        return _TARGET_NORMALIZATION[value]

    return value


def extract_output_target(transcript: str) -> Optional[str]:
    text = (transcript or "").strip().lower()
    if not text:
        return None

    for pattern in _OUTPUT_PATTERNS:
        match = re.search(pattern, text)
        if not match:
            continue

        raw_target = match.group("target")
        normalized_spoken = _normalize_spoken_target(raw_target)
        if not normalized_spoken:
            continue

        normalized = normalize_audio_target(normalized_spoken)
        if normalized:
            return normalized

    return None
