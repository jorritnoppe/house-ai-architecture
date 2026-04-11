import math
import os
import wave
import struct
import uuid
from pathlib import Path
from datetime import datetime

from piper import PiperVoice
from piper.config import SynthesisConfig

from services.voice_service import (
    VOICE_DIR,
    PUBLIC_BASE_URL,
    play_url_on_player,
)
from services.announcement_log_service import log_announcement
import time


from services.loxone_action_service import audio_speaker_route




ANNOUNCEMENT_PIPER_MODEL = os.getenv(
    "ANNOUNCEMENT_PIPER_MODEL",
    "/opt/house-ai/models/piper/en_US-lessac-medium.onnx",
)
DEFAULT_ANNOUNCEMENT_PLAYER = os.getenv("DEFAULT_ANNOUNCEMENT_PLAYER", "desk")

VOICE_QUIET_HOURS_START = int(os.getenv("VOICE_QUIET_HOURS_START", "22"))
VOICE_QUIET_HOURS_END = int(os.getenv("VOICE_QUIET_HOURS_END", "7"))
VOICE_QUIET_AUTO_VOLUME = float(os.getenv("VOICE_QUIET_AUTO_VOLUME", "18"))
VOICE_QUIET_ATTENTION_VOLUME = float(os.getenv("VOICE_QUIET_ATTENTION_VOLUME", "24"))

_ANNOUNCEMENT_VOICE = None

LEVELS = {
    "auto": {
        "prefix": "",
        "volume": 28,
        "chime": False,
        "length_scale": 1.03,
        "noise_scale": 0.62,
        "noise_w_scale": 0.78,
        "repeat": 1,
    },
    "attention": {
        "prefix": "Attention please",
        "volume": 34,
        "chime": True,
        "length_scale": 1.10,
        "noise_scale": 0.55,
        "noise_w_scale": 0.70,
        "repeat": 1,
    },
    "warning": {
        "prefix": "Warning",
        "volume": 40,
        "chime": True,
        "length_scale": 1.16,
        "noise_scale": 0.48,
        "noise_w_scale": 0.62,
        "repeat": 1,
    },
    "emergency": {
        "prefix": "Emergency",
        "volume": 48,
        "chime": True,
        "length_scale": 1.22,
        "noise_scale": 0.40,
        "noise_w_scale": 0.55,
        "repeat": 1,
    },
}



def _is_living_target(player_id: str) -> bool:
    key = (player_id or "").strip().lower()
    return key in {"living", "livingarea", "d8:3a:dd:3e:08:37"}


def _get_wav_duration_seconds(filepath: str) -> float:
    try:
        with wave.open(str(filepath), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return frames / float(rate)
    except Exception:
        pass
    return 5.0


def _prepare_living_audio() -> dict:
    results = {"mode": "living_controlled", "steps": []}

    try:
        results["steps"].append({
            "step": "speaker_route_on",
            "result": audio_speaker_route("living", "on"),
        })
    except Exception as e:
        results["steps"].append({
            "step": "speaker_route_on",
            "result": {"status": "error", "message": str(e)},
        })

    # give Loxone time for prestart / relay delay
    time.sleep(1.5)

    return results





def _release_living_audio() -> dict:
    results = {"mode": "living_controlled", "steps": []}

    try:
        results["steps"].append({
            "step": "speaker_route_off",
            "result": audio_speaker_route("living", "off"),
        })
    except Exception as e:
        results["steps"].append({
            "step": "speaker_route_off",
            "result": {"status": "error", "message": str(e)},
        })

    return results





def _get_announcement_voice():
    global _ANNOUNCEMENT_VOICE
    if _ANNOUNCEMENT_VOICE is None:
        _ANNOUNCEMENT_VOICE = PiperVoice.load(ANNOUNCEMENT_PIPER_MODEL)
    return _ANNOUNCEMENT_VOICE


def _syn_config_for_level(level: str) -> SynthesisConfig:
    cfg = LEVELS.get(level, LEVELS["attention"])
    return SynthesisConfig(
        length_scale=cfg["length_scale"],
        noise_scale=cfg["noise_scale"],
        noise_w_scale=cfg["noise_w_scale"],
    )


def _generate_chime(level: str, sr=22050):
    def tone(freq, duration, volume=0.35):
        total = int(sr * duration)
        out = []
        for i in range(total):
            env = min(1.0, i / (sr * 0.01), (total - i) / (sr * 0.02))
            sample = math.sin(2 * math.pi * freq * (i / sr)) * volume * env
            out.append(int(max(-1.0, min(1.0, sample)) * 32767))
        return out

    def silence(duration):
        return [0] * int(sr * duration)

    if level == "emergency":
        out = []
        out.extend(tone(880, 0.10, 0.45))
        out.extend(silence(0.04))
        out.extend(tone(1320, 0.10, 0.45))
        out.extend(silence(0.04))
        out.extend(tone(1760, 0.16, 0.50))
        out.extend(silence(0.18))
        return out

    if level == "warning":
        out = []
        out.extend(tone(880, 0.12, 0.36))
        out.extend(silence(0.07))
        out.extend(tone(1320, 0.12, 0.36))
        out.extend(silence(0.22))
        return out

    if level == "attention":
        out = []
        out.extend(tone(880, 0.14, 0.30))
        out.extend(silence(0.08))
        out.extend(tone(1320, 0.14, 0.30))
        out.extend(silence(0.25))
        return out

    return []


def _read_wav_mono_16(path):
    with wave.open(str(path), "rb") as wf:
        nch = wf.getnchannels()
        sw = wf.getsampwidth()
        fr = wf.getframerate()
        nframes = wf.getnframes()
        frames = wf.readframes(nframes)

    if sw != 2:
        raise RuntimeError("Only 16-bit WAV is supported")

    data = struct.unpack("<" + "h" * (len(frames) // 2), frames)

    if nch == 1:
        mono = list(data)
    elif nch == 2:
        mono = list(data[::2])
    else:
        raise RuntimeError(f"Unsupported channel count: {nch}")

    return mono, fr


def _write_wav_stereo_left_only(path, mono, sr):
    interleaved = []
    for s in mono:
        interleaved.append(int(max(-32768, min(32767, s))))
        interleaved.append(0)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack("<" + "h" * len(interleaved), *interleaved))


def _synthesize_announcement_wav(text: str, level: str) -> dict:
    filename = f"announcement_{uuid.uuid4().hex}.wav"
    speech_path = VOICE_DIR / f"speech_{filename}"
    final_path = VOICE_DIR / filename

    voice = _get_announcement_voice()
    syn_config = _syn_config_for_level(level)
    with wave.open(str(speech_path), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file, syn_config=syn_config)

    speech, sr = _read_wav_mono_16(speech_path)

    combined = []
    combined.extend(_generate_chime(level, sr=sr))
    combined.extend([0] * int(sr * 0.12))
    combined.extend(speech)

    _write_wav_stereo_left_only(final_path, combined, sr)

    try:
        speech_path.unlink(missing_ok=True)
    except Exception:
        pass

    return {
        "filename": filename,
        "filepath": str(final_path),
        "url": f"{PUBLIC_BASE_URL}/voice/files/{filename}",
        "text": text,
    }


def _is_quiet_hours(now_hour: int | None = None) -> bool:
    hour = datetime.now().hour if now_hour is None else now_hour

    start = VOICE_QUIET_HOURS_START
    end = VOICE_QUIET_HOURS_END

    if start == end:
        return False

    if start < end:
        return start <= hour < end

    return hour >= start or hour < end


def _resolve_announcement_volume(level: str, requested_volume, default_volume):
    if requested_volume is not None:
        return requested_volume

    if _is_quiet_hours():
        if level == "auto":
            return VOICE_QUIET_AUTO_VOLUME
        if level == "attention":
            return VOICE_QUIET_ATTENTION_VOLUME

    return default_volume


def announce_text(
    text: str,
    level: str = "attention",
    player_id: str = DEFAULT_ANNOUNCEMENT_PLAYER,
    volume=None,
    manage_speaker_route: bool = True,
):
    level = (level or "attention").strip().lower()
    if level not in LEVELS:
        level = "attention"

    cfg = LEVELS[level]
    final_text = text.strip()
    if cfg["prefix"]:
        final_text = f"{cfg['prefix']}. {final_text}"

    repeat_count = int(cfg.get("repeat", 1))
    if repeat_count > 1 and level != "emergency":
        final_text = " ".join([final_text] * repeat_count)

    audio = _synthesize_announcement_wav(final_text, level=level)
    resolved_volume = _resolve_announcement_volume(
        level=level,
        requested_volume=volume,
        default_volume=cfg["volume"],
    )

    prepare_result = None
    release_result = None
    duration = None

    if manage_speaker_route and _is_living_target(player_id):
        prepare_result = _prepare_living_audio()

    playback = play_url_on_player(
        player_id=player_id,
        url=audio["url"],
        volume=resolved_volume,
    )

    if manage_speaker_route and _is_living_target(player_id):
        duration = _get_wav_duration_seconds(audio["filepath"])
        time.sleep(duration + 2.0)
        release_result = _release_living_audio()

    log_announcement(
        level=level,
        text=final_text,
        player_id=playback["player_id"],
        volume=playback["volume"],
    )

    return {
        "ok": True,
        "level": level,
        "text": final_text,
        "audio_file": audio["filename"],
        "audio_url": audio["url"],
        "player_id": playback["player_id"],
        "volume": playback["volume"],
        "lms_response": playback["lms_response"],
        "prepare_result": prepare_result,
        "release_result": release_result,
        "duration_seconds": duration,
    }


def announce_house_event(
    message: str,
    level: str = "attention",
    player_id: str = DEFAULT_ANNOUNCEMENT_PLAYER,
    volume=None,
):
    return announce_text(
        text=message,
        level=level,
        player_id=player_id,
        volume=volume,
    )
