import os
import requests


def announce_text(text: str):
    """
    Sends text to the local voice pipeline.
    Tries several common payload formats/endpoints so it works in more setups.
    """

    base_url = os.getenv("VOICE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    candidate_requests = [
        {
            "url": f"{base_url}/voice/speak",
            "json": {"text": text, "target": "desk_speakers", "priority": "normal"},
        },
        {
            "url": f"{base_url}/voice/say",
            "json": {"text": text},
        },
        {
            "url": f"{base_url}/api/voice/speak",
            "json": {"text": text},
        },
        {
            "url": f"{base_url}/speak",
            "json": {"text": text},
        },
    ]

    last_error = None

    for candidate in candidate_requests:
        try:
            resp = requests.post(candidate["url"], json=candidate["json"], timeout=15)
            if 200 <= resp.status_code < 300:
                return {
                    "ok": True,
                    "detail": f"Announcement sent to {candidate['url']}"
                }
            last_error = f"{candidate['url']} returned HTTP {resp.status_code}: {resp.text[:300]}"
        except Exception as exc:
            last_error = f"{candidate['url']} failed: {exc}"

    return {
        "ok": False,
        "detail": last_error or "No voice endpoint succeeded"
    }
