import json
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path("/home/jnoppe/house-agent/data/announcement_log.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log_announcement(level: str, text: str, player_id: str, volume):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "text": text,
        "player_id": player_id,
        "volume": volume,
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
