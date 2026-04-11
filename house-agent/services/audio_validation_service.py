from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from services.audio_timing_test_service import run_timing_test

CACHE_DIR = Path("/opt/house-ai/runtime")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

LAST_TIMING_RESULT_FILE = CACHE_DIR / "last_timing_test.json"


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_last_timing_result(result: dict) -> dict:
    payload = {
        "saved_at": utc_iso(),
        "result": result,
    }
    LAST_TIMING_RESULT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_last_timing_result() -> dict:
    if not LAST_TIMING_RESULT_FILE.exists():
        return {
            "status": "missing",
            "message": "no timing validation has been saved yet",
        }

    try:
        return json.loads(LAST_TIMING_RESULT_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }


def build_timing_health_summary() -> dict:
    payload = load_last_timing_result()
    if payload.get("status") in {"missing", "error"}:
        return payload

    result = payload.get("result") or {}
    summary = result.get("summary") or {}
    analysis = result.get("analysis") or {}
    probe_saved = result.get("probe_saved") or {}

    beep_count = summary.get("beep_count", 0)
    avg_interval = summary.get("avg_interval_sec")
    first_beep_offset = summary.get("first_beep_offset_sec")
    verdict = summary.get("status", "unknown")

    health = "unknown"
    if verdict == "ok" and beep_count >= 5:
        health = "healthy"
    elif beep_count >= 1:
        health = "warning"
    else:
        health = "failed"

    return {
        "status": "ok",
        "health": health,
        "verdict": verdict,
        "saved_at": payload.get("saved_at"),
        "session_id": result.get("session_id"),
        "target": ((result.get("arm_result") or {}).get("metadata") or {}).get("target"),
        "volume": ((result.get("arm_result") or {}).get("metadata") or {}).get("volume"),
        "beep_count": beep_count,
        "avg_interval_sec": avg_interval,
        "first_beep_offset_sec": first_beep_offset,
        "probe_rms": probe_saved.get("rms"),
        "pattern_url": result.get("pattern_url"),
        "saved_to": probe_saved.get("saved_to"),
        "analysis_status": analysis.get("status"),
    }


def run_and_cache_timing_test(
    target: str = "desk",
    volume: int = 60,
    probe_seconds_back: int = 18,
    probe_label: str = "timing_test",
) -> dict:
    result = run_timing_test(
        target=target,
        volume=volume,
        probe_seconds_back=probe_seconds_back,
        probe_label=probe_label,
    )
    save_last_timing_result(result)
    return result
