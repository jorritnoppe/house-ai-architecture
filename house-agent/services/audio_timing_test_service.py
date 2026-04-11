from __future__ import annotations

import time
import uuid
from pathlib import Path

import requests

from services.audio_test_pattern import save_test_pattern
from services.audio_pattern_analysis import detect_beep_regions
from services.voice_service import play_url_on_player

DISCOVER_PI_BASE = "http://feedback-node.local:8091"


def _download_probe_file(probe_name: str) -> str:
    tmp_dir = Path("/tmp/feedback-probe-tests")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    local_path = tmp_dir / probe_name

    resp = requests.get(
        f"{DISCOVER_PI_BASE}/audio/get_file",
        params={"name": probe_name},
        timeout=60,
    )
    resp.raise_for_status()
    local_path.write_bytes(resp.content)
    return str(local_path)


def _start_timing_capture(
    session_id: str,
    seconds: int,
    label: str,
    metadata: dict,
    pre_roll_seconds: int = 2,
) -> dict:
    resp = requests.post(
        f"{DISCOVER_PI_BASE}/timing/start_capture",
        json={
            "session_id": session_id,
            "seconds": seconds,
            "label": label,
            "metadata": metadata,
            "pre_roll_seconds": pre_roll_seconds,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _get_timing_session(session_id: str) -> dict:
    resp = requests.get(
        f"{DISCOVER_PI_BASE}/timing/session/{session_id}",
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _wait_for_timing_session(
    session_id: str,
    timeout_sec: int = 40,
    poll_interval: float = 0.5,
) -> dict:
    started = time.time()

    while True:
        state = _get_timing_session(session_id)
        status = (state.get("status") or "").lower()

        if status in {"completed", "error", "cancelled"}:
            return state

        if time.time() - started > timeout_sec:
            return {
                "status": "error",
                "session_id": session_id,
                "error": f"timing session timeout after {timeout_sec} seconds",
            }

        time.sleep(poll_interval)


def _summarize_analysis(analysis: dict) -> dict:
    beeps = analysis.get("beeps", []) or []
    intervals = analysis.get("start_intervals_sec", []) or []

    if beeps:
        avg_duration = round(
            sum(b.get("duration_sec", 0.0) for b in beeps) / len(beeps), 4
        )
        first_beep_offset = beeps[0].get("start_sec")
    else:
        avg_duration = None
        first_beep_offset = None

    if intervals:
        avg_interval = round(sum(intervals) / len(intervals), 4)
    else:
        avg_interval = None

    status = "ok"
    if analysis.get("beep_count", 0) < 5:
        status = "missing_beeps"
    elif intervals and any(abs(x - 1.0) > 0.15 for x in intervals):
        status = "timing_drift"

    return {
        "status": status,
        "beep_count": analysis.get("beep_count"),
        "first_beep_offset_sec": first_beep_offset,
        "avg_beep_duration_sec": avg_duration,
        "avg_interval_sec": avg_interval,
    }


def run_timing_test(
    target: str = "desk",
    volume: int = 60,
    probe_seconds_back: int = 18,
    probe_label: str = "timing_test",
) -> dict:
    session_id = f"timing_{uuid.uuid4().hex[:12]}"
    pattern = save_test_pattern()

    pattern_path = Path(pattern["path"])
    if not pattern_path.exists():
        return {
            "status": "error",
            "error": "pattern file was not created on disk",
            "session_id": session_id,
            "pattern": pattern,
        }

    url = f"http://house-ai.local:8010/{pattern['filename']}"
    arm_result = _start_timing_capture(
        session_id=session_id,
        seconds=probe_seconds_back,
        label=probe_label,
        metadata={
            "target": target,
            "pattern_filename": pattern["filename"],
            "pattern_url": url,
            "volume": volume,
            "session_id": session_id,
        },
        pre_roll_seconds=2,
    )

    # Give the file a moment to settle and the timing session to fully enter recording state.
    time.sleep(1.5)

    playback = play_url_on_player(
        player_id=target,
        url=url,
        volume=volume,
    )

    session_result = _wait_for_timing_session(
        session_id=session_id,
        timeout_sec=probe_seconds_back + 15,
    )

    if session_result.get("status") != "completed":
        return {
            "status": "error",
            "error": session_result.get("error", "timing session did not complete"),
            "session_id": session_id,
            "pattern": pattern,
            "pattern_url": url,
            "arm_result": arm_result,
            "playback": playback,
            "session_result": session_result,
        }

    saved_path = session_result["saved_to"]
    probe_name = Path(saved_path).name
    local_probe_path = _download_probe_file(probe_name)

    analysis = detect_beep_regions(local_probe_path)
    summary = _summarize_analysis(analysis)

    return {
        "status": "ok",
        "session_id": session_id,
        "pattern": pattern,
        "pattern_url": url,
        "arm_result": arm_result,
        "playback": playback,
        "probe_saved": session_result,
        "local_probe_path": local_probe_path,
        "analysis": analysis,
        "summary": summary,
    }
