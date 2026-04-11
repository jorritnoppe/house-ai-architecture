import numpy as np
import wave
import uuid

from services.voice_service import VOICE_DIR


def generate_beep_pattern(
    sample_rate=16000,
    beep_freq=1000,
    beep_duration=0.3,
    silence_duration=0.7,
    repetitions=5,
):
    def tone(freq, duration):
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        return 0.5 * np.sin(2 * np.pi * freq * t)

    def silence(duration):
        return np.zeros(int(sample_rate * duration))

    signal = []

    for _ in range(repetitions):
        signal.append(tone(beep_freq, beep_duration))
        signal.append(silence(silence_duration))

    return np.concatenate(signal)


def save_test_pattern():
    VOICE_DIR.mkdir(parents=True, exist_ok=True)

    data = generate_beep_pattern()

    filename = f"test_pattern_{uuid.uuid4().hex}.wav"
    path = VOICE_DIR / filename

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes((data * 32767).astype(np.int16).tobytes())

    return {
        "path": str(path),
        "filename": filename,
    }
