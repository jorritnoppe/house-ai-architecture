from pathlib import Path
import subprocess

from faster_whisper import WhisperModel


MODEL_SIZE = "base"
MODEL_DEVICE = "cpu"
MODEL_COMPUTE_TYPE = "int8"



_model = None


def get_model():
    global _model
    if _model is None:
        _model = WhisperModel(
            MODEL_SIZE,
            device=MODEL_DEVICE,
            compute_type=MODEL_COMPUTE_TYPE,
        )
    return _model


def convert_to_mono_16k(src: str, dst: str) -> str:
    cmd = [
        "ffmpeg",
        "-y",
        "-i", src,
        "-ac", "1",
        "-ar", "16000",
        dst,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return dst


def transcribe_wav(path: str, language: str = "en") -> dict:
    src = Path(path)
    mono_path = Path("/tmp") / f"{src.stem}_mono16k.wav"
    convert_to_mono_16k(str(src), str(mono_path))

    model = get_model()
    segments, info = model.transcribe(str(mono_path), language=language)

    text_parts = []
    for seg in segments:
        if seg.text:
            text_parts.append(seg.text.strip())

    text = " ".join(part for part in text_parts if part).strip()

    return {
        "text": text,
        "language": info.language,
        "language_probability": getattr(info, "language_probability", None),
        "mono_file": str(mono_path),
    }
