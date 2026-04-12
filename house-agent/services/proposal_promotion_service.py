import importlib
import os
import re

from services.proposed_tool_service import (
    read_proposed_tool,
    mark_proposed_tool_promoted,
)


EXPERIMENTAL_TOOLS_DIR = "/home/jnoppe/house-agent/experimental_tools"


def _safe_filename(filename: str) -> str:
    filename = (filename or "").strip()

    if not filename:
        raise ValueError("filename is missing")

    if not filename.endswith(".py"):
        raise ValueError("filename must end with .py")

    if "/" in filename or "\\" in filename:
        raise ValueError("filename must not contain path separators")

    if not re.fullmatch(r"[a-zA-Z0-9_]+\.py", filename):
        raise ValueError("filename contains invalid characters")

    return filename


def promote_proposed_tool_to_experimental(proposal_id: str):
    proposal = read_proposed_tool(proposal_id)

    if proposal.get("status") != "approved":
        raise ValueError("proposal must be approved before promotion")

    filename = _safe_filename(proposal.get("filename"))
    code = proposal.get("code") or ""

    if not code.strip():
        raise ValueError("proposal code is empty")

    os.makedirs(EXPERIMENTAL_TOOLS_DIR, exist_ok=True)

    package_init = os.path.join(EXPERIMENTAL_TOOLS_DIR, "__init__.py")
    if not os.path.exists(package_init):
        with open(package_init, "w", encoding="utf-8") as f:
            f.write("")

    target_path = os.path.join(EXPERIMENTAL_TOOLS_DIR, filename)

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(code)

    importlib.invalidate_caches()

    try:
        module_name = f"experimental_tools.{filename[:-3]}"
        importlib.import_module(module_name)
    except Exception as e:
        raise RuntimeError(f"tool file written but import failed: {e}")

    updated = mark_proposed_tool_promoted(proposal_id)

    return {
        "status": "ok",
        "message": "Proposed tool promoted to experimental.",
        "proposal": updated,
        "experimental_module": f"experimental_tools.{filename[:-3]}",
        "path": target_path,
    }
