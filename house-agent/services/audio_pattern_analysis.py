from __future__ import annotations

import wave
import numpy as np


def load_wav_mono(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        frames = wf.readframes(wf.getnframes())

    if sampwidth != 2:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)

    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)

    max_abs = np.max(np.abs(data)) if data.size else 0.0
    if max_abs > 0:
        data = data / max_abs

    return data, sample_rate


def moving_average(x: np.ndarray, window_size: int) -> np.ndarray:
    if window_size <= 1:
        return x
    kernel = np.ones(window_size, dtype=np.float32) / window_size
    return np.convolve(x, kernel, mode="same")


def detect_beep_regions(
    path: str,
    threshold: float = 0.12,
    smooth_ms: int = 20,
    min_beep_ms: int = 120,
    merge_gap_ms: int = 120,
) -> dict:
    data, sr = load_wav_mono(path)

    envelope = np.abs(data)
    smooth_samples = max(1, int(sr * smooth_ms / 1000))
    env = moving_average(envelope, smooth_samples)

    above = env >= threshold

    regions = []
    start = None

    for i, flag in enumerate(above):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            end = i
            regions.append([start, end])
            start = None

    if start is not None:
        regions.append([start, len(above) - 1])

    min_beep_samples = int(sr * min_beep_ms / 1000)
    filtered = []
    for s, e in regions:
        if (e - s) >= min_beep_samples:
            filtered.append([s, e])

    merge_gap_samples = int(sr * merge_gap_ms / 1000)
    merged = []
    for s, e in filtered:
        if not merged:
            merged.append([s, e])
            continue
        prev_s, prev_e = merged[-1]
        if s - prev_e <= merge_gap_samples:
            merged[-1][1] = e
        else:
            merged.append([s, e])

    beeps = []
    for idx, (s, e) in enumerate(merged, start=1):
        beeps.append({
            "index": idx,
            "start_sec": round(s / sr, 4),
            "end_sec": round(e / sr, 4),
            "duration_sec": round((e - s) / sr, 4),
            "peak": round(float(np.max(env[s:e + 1])) if e > s else 0.0, 4),
        })

    starts = [b["start_sec"] for b in beeps]
    intervals = []
    for i in range(1, len(starts)):
        intervals.append(round(starts[i] - starts[i - 1], 4))

    return {
        "status": "ok",
        "path": path,
        "sample_rate": sr,
        "threshold": threshold,
        "beep_count": len(beeps),
        "beeps": beeps,
        "start_intervals_sec": intervals,
    }
