from __future__ import annotations

import tempfile
from pathlib import Path

import requests

from services.audio_test_pattern import save_test_pattern
from services.audio_pattern_analysis import detect_beep_regions
from services.feedback_probe_client import probe_save_window
from services.voice_service import play_url_on_player


def _download_probe_file(probe_name: str) -> str:
    tmp_dir = Path("/tmp/feedback-probe-tests")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    local_path = tmp_dir / probe_name

    resp = requests.get(
        "http://192.168.9.198:8091/audio/get_file",
        params={"name": probe_name},
        timeout=60,
    )
    resp.raise_for_status()
    local_path.write_bytes(resp.content)
    return str(local_path)


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

    recommended_seconds_back = 7
    if first_beep_offset is not None:
        if first_beep_offset > 5.5:
            recommended_seconds_back = 8
        elif first_beep_offset < 3.5:
            recommended_seconds_back = 6

    return {
        "status": status,
        "beep_count": analysis.get("beep_count"),
        "first_beep_offset_sec": first_beep_offset,
        "avg_beep_duration_sec": avg_duration,
        "avg_interval_sec": avg_interval,
        "recommended_probe_seconds_back": recommended_seconds_back,
    }


def run_timing_test(
    target: str = "desk",
    volume: int = 60,
    probe_seconds_back: int = 10,
    probe_label: str = "timing_test",
) -> dict:
    pattern = save_test_pattern()
    url = f"http://192.168.9.182:8000/voice/files/{pattern['filename']}"

    playback = play_url_on_player(
        player_id=target,
        url=url,
        volume=volume,
    )

    probe_saved = probe_save_window(
        seconds_back=probe_seconds_back,
        label=probe_label,
        metadata={
            "target": target,
            "pattern_filename": pattern["filename"],
            "pattern_url": url,
            "volume": volume,
        },
    )

    probe_name = Path(probe_saved["saved_to"]).name
    local_probe_path = _download_probe_file(probe_name)
    analysis = detect_beep_regions(local_probe_path)
    summary = _summarize_analysis(analysis)

    return {
        "status": "ok",
        "pattern": pattern,
        "pattern_url": url,
        "playback": playback,
        "probe_saved": probe_saved,
        "local_probe_path": local_probe_path,
        "analysis": analysis,
        "summary": summary,
    }
