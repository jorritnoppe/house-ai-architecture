import json
import os
from datetime import datetime, timezone
from typing import Any


PROMOTION_AUDIT_FILE = "/opt/house-ai/data/proposed_promotion_audit.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir() -> None:
    os.makedirs(os.path.dirname(PROMOTION_AUDIT_FILE), exist_ok=True)


def _load_all() -> list[dict[str, Any]]:
    _ensure_parent_dir()

    if not os.path.exists(PROMOTION_AUDIT_FILE):
        return []

    try:
        with open(PROMOTION_AUDIT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def _save_all(items: list[dict[str, Any]]) -> None:
    _ensure_parent_dir()
    with open(PROMOTION_AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def list_promotion_audit() -> list[dict[str, Any]]:
    return _load_all()


def add_promotion_audit_record(
    proposal_id: str,
    target: str,
    proposal_status: str,
    target_path: str | None,
    allow_overwrite: bool,
    validation: dict[str, Any] | None,
    preflight: dict[str, Any] | None,
    dependency_analysis: dict[str, Any] | None,
    actor: str = "admin",
) -> dict[str, Any]:
    items = _load_all()

    record = {
        "id": f"audit_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        "proposal_id": proposal_id,
        "target": target,
        "proposal_status": proposal_status,
        "target_path": target_path,
        "allow_overwrite": allow_overwrite,
        "actor": actor,
        "validation": validation or {},
        "preflight": preflight or {},
        "dependency_analysis": dependency_analysis or {},
        "created_at": _utc_now_iso(),
    }

    items.append(record)
    _save_all(items)
    return record
