import os
import shutil

from services.proposed_tool_service import mark_proposed_tool_installed, read_proposed_tool


EXPERIMENTAL_TOOLS_DIR = "/home/jnoppe/house-agent/experimental_tools"
PRODUCTION_TOOLS_DIR = "/home/jnoppe/house-agent/tools"
BACKUP_DIR = "/home/jnoppe/house-agent/backups/tool_promotions"


def _ensure_dirs():
    os.makedirs(EXPERIMENTAL_TOOLS_DIR, exist_ok=True)
    os.makedirs(PRODUCTION_TOOLS_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)


def promote_proposed_to_experimental(proposal_id: str):
    _ensure_dirs()

    proposal = read_proposed_tool(proposal_id)

    if proposal.get("status") != "approved":
        raise ValueError("Only approved proposals can be promoted to experimental.")

    filename = proposal.get("filename") or f"{proposal.get('name')}.py"
    path = os.path.join(EXPERIMENTAL_TOOLS_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(proposal.get("code", ""))

    updated = mark_proposed_tool_installed(
        proposal_id,
        status="promoted_to_experimental",
        promoted_by="admin",
        target="experimental",
    )

    return {
        "status": "ok",
        "message": "Proposed tool promoted to experimental.",
        "path": path,
        "experimental_module": f"experimental_tools.{os.path.splitext(filename)[0]}",
        "proposal": updated,
    }


def promote_experimental_to_production(proposal_id: str):
    _ensure_dirs()

    proposal = read_proposed_tool(proposal_id)

    if proposal.get("status") != "promoted_to_experimental":
        raise ValueError("Only tools promoted to experimental can be promoted to production.")

    filename = proposal.get("filename") or f"{proposal.get('name')}.py"
    experimental_path = os.path.join(EXPERIMENTAL_TOOLS_DIR, filename)
    production_path = os.path.join(PRODUCTION_TOOLS_DIR, filename)

    if not os.path.exists(experimental_path):
        raise FileNotFoundError(f"Experimental file not found: {experimental_path}")

    if os.path.exists(production_path):
        backup_path = os.path.join(BACKUP_DIR, filename)
        shutil.copy2(production_path, backup_path)

    shutil.copy2(experimental_path, production_path)

    updated = mark_proposed_tool_installed(
        proposal_id,
        status="promoted_to_production",
        promoted_by="admin",
        target="production",
    )
    return {
        "status": "ok",
        "message": "Experimental tool promoted to production.",
        "production_path": production_path,
        "proposal": updated,
    }
