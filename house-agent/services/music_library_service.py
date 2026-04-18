from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

AI_HOUSE_ROOT = Path(
    os.environ.get("AI_HOUSE_MUSIC_ROOT", "/mnt/aihousemusicfolder/ai-house")
).resolve()

META_DIR = AI_HOUSE_ROOT / "meta"
TRACK_STATUS_CSV = META_DIR / "track_status.csv"
ENABLED_PLAYLIST_M3U = META_DIR / "enabled_playlist.m3u"

SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".wma",
}

CSV_FIELDS = [
    "relative_path",
    "title",
    "enabled",
    "size_bytes",
    "modified_at",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_meta() -> None:
    META_DIR.mkdir(parents=True, exist_ok=True)


def _safe_relpath_from_root(file_path: Path) -> str:
    rel = file_path.resolve().relative_to(AI_HOUSE_ROOT)
    return rel.as_posix()


def _title_from_path(relative_path: str) -> str:
    return Path(relative_path).stem


def _is_audio_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def _walk_audio_files() -> List[Path]:
    if not AI_HOUSE_ROOT.exists():
        return []

    files: List[Path] = []
    for path in AI_HOUSE_ROOT.rglob("*"):
        if META_DIR in path.parents:
            continue
        if _is_audio_file(path):
            files.append(path)

    files.sort(key=lambda p: p.as_posix().lower())
    return files


def _read_existing_status_map() -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    if not TRACK_STATUS_CSV.exists():
        return result

    with TRACK_STATUS_CSV.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rel = (row.get("relative_path") or "").strip()
            if not rel:
                continue

            result[rel] = {
                "relative_path": rel,
                "title": (row.get("title") or "").strip() or _title_from_path(rel),
                "enabled": str(row.get("enabled") or "1").strip(),
                "size_bytes": str(row.get("size_bytes") or "").strip(),
                "modified_at": str(row.get("modified_at") or "").strip(),
            }

    return result


def _normalize_enabled(value) -> str:
    return "1" if str(value).strip().lower() in {"1", "true", "yes", "on"} else "0"


def _build_track_rows() -> List[Dict[str, str]]:
    existing = _read_existing_status_map()
    rows: List[Dict[str, str]] = []

    for file_path in _walk_audio_files():
        stat = file_path.stat()
        rel = _safe_relpath_from_root(file_path)
        old = existing.get(rel, {})

        rows.append(
            {
                "relative_path": rel,
                "title": old.get("title") or _title_from_path(rel),
                "enabled": _normalize_enabled(old.get("enabled", "1")),
                "size_bytes": str(stat.st_size),
                "modified_at": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        )

    rows.sort(key=lambda x: x["relative_path"].lower())
    return rows


def _write_track_status(rows: List[Dict[str, str]]) -> None:
    _ensure_meta()
    with TRACK_STATUS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def _write_enabled_playlist(rows: List[Dict[str, str]]) -> int:
    _ensure_meta()

    enabled_count = 0
    with ENABLED_PLAYLIST_M3U.open("w", encoding="utf-8") as handle:
        handle.write("#EXTM3U\n")
        for row in rows:
            if _normalize_enabled(row.get("enabled", "0")) != "1":
                continue

            enabled_count += 1
            rel = row["relative_path"]
            title = row.get("title") or _title_from_path(rel)

            # Write the filesystem path that LMS should be able to read through the share.
            lms_path = f"/mnt/Trueshare/Music/ai-house/{rel}"
            handle.write(f"#EXTINF:-1,{title}\n")
            handle.write(f"{lms_path}\n")

    return enabled_count


def refresh_music_library() -> Dict[str, object]:
    rows = _build_track_rows()
    _write_track_status(rows)
    enabled_count = _write_enabled_playlist(rows)

    return {
        "status": "ok",
        "answer": "AI house music library refreshed.",
        "root": str(AI_HOUSE_ROOT),
        "track_status_csv": str(TRACK_STATUS_CSV),
        "enabled_playlist_m3u": str(ENABLED_PLAYLIST_M3U),
        "track_count": len(rows),
        "enabled_count": enabled_count,
        "tracks": rows,
        "refreshed_at": _utc_now_iso(),
    }


def get_music_library() -> Dict[str, object]:
    if not TRACK_STATUS_CSV.exists():
        refresh_music_library()

    rows = _read_existing_status_map()
    ordered = list(rows.values())
    ordered.sort(key=lambda x: x["relative_path"].lower())

    enabled_count = sum(
        1 for row in ordered if _normalize_enabled(row.get("enabled", "0")) == "1"
    )

    return {
        "status": "ok",
        "root": str(AI_HOUSE_ROOT),
        "track_status_csv": str(TRACK_STATUS_CSV),
        "enabled_playlist_m3u": str(ENABLED_PLAYLIST_M3U),
        "track_count": len(ordered),
        "enabled_count": enabled_count,
        "tracks": ordered,
    }


def set_track_enabled(relative_path: str, enabled: bool) -> Dict[str, object]:
    rel = (relative_path or "").strip().replace("\\", "/")
    if not rel:
        return {"status": "error", "error": "Missing relative_path"}

    rows = _build_track_rows()
    found = False

    for row in rows:
        if row["relative_path"] == rel:
            row["enabled"] = "1" if enabled else "0"
            found = True
            break

    if not found:
        return {"status": "error", "error": f"Track not found: {rel}"}

    _write_track_status(rows)
    enabled_count = _write_enabled_playlist(rows)

    return {
        "status": "ok",
        "answer": f"Track {'enabled' if enabled else 'disabled'}: {rel}",
        "relative_path": rel,
        "enabled": bool(enabled),
        "enabled_count": enabled_count,
        "track_count": len(rows),
    }


def delete_track(relative_path: str) -> Dict[str, object]:
    rel = (relative_path or "").strip().replace("\\", "/")
    if not rel:
        return {"status": "error", "error": "Missing relative_path"}

    target = (AI_HOUSE_ROOT / rel).resolve()

    try:
        target.relative_to(AI_HOUSE_ROOT)
    except ValueError:
        return {"status": "error", "error": "Path escapes music root"}

    if META_DIR in target.parents:
        return {"status": "error", "error": "Refusing to delete files inside meta"}

    if not target.exists() or not target.is_file():
        return {"status": "error", "error": f"Track not found: {rel}"}

    if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return {"status": "error", "error": f"Unsupported audio file type: {rel}"}

    target.unlink()

    refresh_result = refresh_music_library()
    refresh_result.update(
        {
            "answer": f"Deleted track: {rel}",
            "deleted_relative_path": rel,
        }
    )
    return refresh_result
