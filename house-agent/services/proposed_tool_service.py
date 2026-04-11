import json
import os
from datetime import datetime, timezone


PROPOSED_TOOLS_FILE = "/opt/house-ai/data/proposed_tools.json"


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir():
    os.makedirs(os.path.dirname(PROPOSED_TOOLS_FILE), exist_ok=True)


def _load_all():
    _ensure_parent_dir()

    if not os.path.exists(PROPOSED_TOOLS_FILE):
        return []

    try:
        with open(PROPOSED_TOOLS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def _save_all(items):
    _ensure_parent_dir()
    with open(PROPOSED_TOOLS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def list_proposed_tools():
    return _load_all()


def get_proposed_tool(proposal_id: str):
    items = _load_all()
    for item in items:
        if item.get("id") == proposal_id:
            return item
    return None


def read_proposed_tool(proposal_id: str):
    item = get_proposed_tool(proposal_id)
    if item is None:
        raise FileNotFoundError(proposal_id)
    return item


def save_proposed_tool(proposal):
    items = _load_all()

    if isinstance(proposal, dict) and "id" in proposal:
        proposal_id = proposal["id"]
        for idx, item in enumerate(items):
            if item.get("id") == proposal_id:
                proposal["updated_at"] = _utc_now_iso()
                items[idx] = proposal
                _save_all(items)
                return {
                    "status": "ok",
                    "message": "Proposed tool updated.",
                    "tool": proposal,
                }

        if "updated_at" not in proposal:
            proposal["updated_at"] = None

        items.append(proposal)
        _save_all(items)
        return {
            "status": "ok",
            "message": "Proposed tool saved.",
            "tool": proposal,
        }

    tool_name = (proposal.get("tool_name") or "").strip()
    code = proposal.get("code") or ""
    description = (proposal.get("description") or "").strip()
    filename = (proposal.get("filename") or f"{tool_name}.py").strip()
    requested_by = (proposal.get("requested_by") or "ai").strip()
    notes = proposal.get("notes") or ""

    if not tool_name:
        raise ValueError("tool_name is required")

    if not code.strip():
        raise ValueError("code is required")

    item = {
        "id": f"proposal_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        "name": tool_name,
        "description": description,
        "filename": filename,
        "code": code,
        "requested_by": requested_by,
        "notes": notes,
        "status": "pending",
        "created_at": _utc_now_iso(),
        "approved_at": None,
        "installed_at": None,
        "rejected_at": None,
        "updated_at": None,
    }

    items.append(item)
    _save_all(items)

    return {
        "status": "ok",
        "message": "Proposed tool saved.",
        "tool": item,
    }


def find_existing_pending_by_name(name: str):
    name = (name or "").strip().lower()
    if not name:
        return None

    for item in _load_all():
        if item.get("status") == "pending" and str(item.get("name", "")).strip().lower() == name:
            return item
    return None


def add_proposed_tool(
    name: str,
    description: str,
    filename: str,
    code: str,
    requested_by: str = "ai",
    notes: str | None = None,
):
    existing = find_existing_pending_by_name(name)

    if existing is not None:
        existing["description"] = description
        existing["filename"] = filename
        existing["code"] = code
        existing["requested_by"] = requested_by
        existing["notes"] = notes or ""
        existing["updated_at"] = _utc_now_iso()

        result = save_proposed_tool(existing)
        result["message"] = "Existing pending proposed tool updated."
        return result["tool"]

    proposal = {
        "id": f"proposal_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        "name": name,
        "description": description,
        "filename": filename,
        "code": code,
        "requested_by": requested_by,
        "notes": notes or "",
        "status": "pending",
        "created_at": _utc_now_iso(),
        "approved_at": None,
        "installed_at": None,
        "rejected_at": None,
        "updated_at": None,
    }

    result = save_proposed_tool(proposal)
    return result["tool"]


def approve_proposed_tool(proposal_id: str, approved_by: str = "admin"):
    proposal = get_proposed_tool(proposal_id)
    if proposal is None:
        return None

    proposal["status"] = "approved"
    proposal["approved_at"] = _utc_now_iso()
    proposal["approved_by"] = approved_by
    proposal["updated_at"] = _utc_now_iso()
    return save_proposed_tool(proposal)



def mark_proposed_tool_installed(
    proposal_id: str,
    status: str = "installed",
    promoted_by: str = "admin",
    target: str | None = None,
):
    proposal = get_proposed_tool(proposal_id)
    if proposal is None:
        return None

    proposal["status"] = status
    proposal["installed_at"] = _utc_now_iso()
    proposal["promoted_by"] = promoted_by
    if target is not None:
        proposal["promotion_target"] = target
    proposal["updated_at"] = _utc_now_iso()
    return save_proposed_tool(proposal)


def reject_proposed_tool(proposal_id: str, rejected_by: str = "admin"):
    proposal = get_proposed_tool(proposal_id)
    if proposal is None:
        return None

    proposal["status"] = "rejected"
    proposal["rejected_at"] = _utc_now_iso()
    proposal["rejected_by"] = rejected_by
    proposal["updated_at"] = _utc_now_iso()
    return save_proposed_tool(proposal)


def update_proposed_tool(proposal_id: str, **changes):
    proposal = get_proposed_tool(proposal_id)
    if proposal is None:
        return None

    proposal.update(changes)
    proposal["updated_at"] = _utc_now_iso()
    result = save_proposed_tool(proposal)
    return result["tool"]
