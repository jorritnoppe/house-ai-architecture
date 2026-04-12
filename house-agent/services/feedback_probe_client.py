from __future__ import annotations

import re
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

import requests

from services.stt_service import transcribe_wav

FEEDBACK_PROBE_BASE = "http://192.168.9.198:8091"


def update_probe_metadata(path: str, patch: dict) -> dict:
    try:
        resp = requests.post(
            f"{FEEDBACK_PROBE_BASE}/audio/update_metadata",
            json={"path": path, "patch": patch},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def flag_probe_capture(path: str, reason: str) -> dict:
    try:
        resp = requests.post(
            f"{FEEDBACK_PROBE_BASE}/audio/flag_capture",
            json={"path": path, "reason": reason},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _normalize_compare_text(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s]", "", value)
    return value.strip()


def score_probe_capture(main_transcript: str, probe_transcript: str, rms: float | None) -> dict:
    main_n = _normalize_compare_text(main_transcript)
    probe_n = _normalize_compare_text(probe_transcript)

    similarity = SequenceMatcher(None, main_n, probe_n).ratio() if (main_n or probe_n) else 0.0

    if rms is None:
        rms = 0.0

    if rms < 0.005:
        classification = "low_signal"
    elif not probe_n:
        classification = "empty_probe_transcript"
    elif similarity < 0.45:
        classification = "possible_stt_mismatch"
    else:
        classification = "ok"

    return {
        "status": "ok",
        "classification": classification,
        "similarity": round(similarity, 4),
        "rms": rms,
        "main_transcript_normalized": main_n,
        "probe_transcript_normalized": probe_n,
    }


def probe_health() -> dict:
    r = requests.get(f"{FEEDBACK_PROBE_BASE}/health", timeout=10)
    r.raise_for_status()
    return r.json()


def probe_audio_window(seconds_back: int = 5) -> dict:
    r = requests.post(
        f"{FEEDBACK_PROBE_BASE}/audio/window",
        json={"seconds_back": seconds_back},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def probe_save_window(seconds_back: int = 8, label: str = "feedback_probe", metadata: dict | None = None) -> dict:
    r = requests.post(
        f"{FEEDBACK_PROBE_BASE}/audio/save_window",
        json={
            "seconds_back": seconds_back,
            "label": label,
            "metadata": metadata or {},
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def probe_list_recent(limit: int = 20) -> dict:
    r = requests.get(
        f"{FEEDBACK_PROBE_BASE}/audio/list_recent",
        params={"limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def probe_flag_file(path: str, reason: str = "review") -> dict:
    r = requests.post(
        f"{FEEDBACK_PROBE_BASE}/audio/flag_capture",
        json={"path": path, "reason": reason},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def probe_list_flagged(limit: int = 20) -> dict:
    r = requests.get(
        f"{FEEDBACK_PROBE_BASE}/audio/list_flagged",
        params={"limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def probe_download_file(path: str) -> bytes:
    r = requests.get(
        f"{FEEDBACK_PROBE_BASE}/audio/get_file",
        params={"path": path},
        timeout=60,
    )
    r.raise_for_status()
    return r.content


def transcribe_saved_probe_file(path: str, language: str = "en") -> dict:
    audio_bytes = probe_download_file(path)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = Path(tmp.name)

    try:
        result = transcribe_wav(str(tmp_path), language=language)
        return {
            "status": "ok",
            "path": path,
            "transcript": result.get("text", ""),
            "language": result.get("language"),
            "language_probability": result.get("language_probability"),
            "mono_file": result.get("mono_file"),
        }
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
