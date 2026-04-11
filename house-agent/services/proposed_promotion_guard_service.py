import os
import py_compile
import tempfile
from typing import Any

from extensions import tool_registry, experimental_tool_registry
from services.proposed_tool_validation_service import validate_proposal_record


def _safe_target_path(base_dir: str, filename: str) -> tuple[bool, str]:
    filename = os.path.basename((filename or "").strip())
    if not filename:
        return False, "Filename is empty."

    if not filename.endswith(".py"):
        return False, "Filename must end with .py."

    full_path = os.path.abspath(os.path.join(base_dir, filename))
    base_dir_abs = os.path.abspath(base_dir)

    if not full_path.startswith(base_dir_abs + os.sep):
        return False, "Target path escapes base directory."

    return True, full_path


def _compile_code_in_tempfile(code: str) -> dict[str, Any]:
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code or "")
            tmp_path = f.name

        py_compile.compile(tmp_path, doraise=True)
        return {
            "ok": True,
            "message": "Temporary compile check passed.",
        }
    except Exception as e:
        return {
            "ok": False,
            "message": f"Temporary compile check failed: {e}",
        }
    finally:
        try:
            if "tmp_path" in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass


def _tool_name_collision(tool_name: str, target: str) -> dict[str, Any]:
    if not tool_name:
        return {
            "ok": False,
            "message": "TOOL_SPEC.name is missing.",
        }

    if target == "experimental":
        if experimental_tool_registry.get(tool_name) is not None:
            return {
                "ok": False,
                "message": f"Experimental tool name already exists: {tool_name}",
            }
    elif target == "production":
        if tool_registry.get(tool_name) is not None:
            return {
                "ok": False,
                "message": f"Production tool name already exists: {tool_name}",
            }

    return {
        "ok": True,
        "message": "No tool name collision detected.",
    }


def preflight_promotion_check(
    proposal: dict[str, Any],
    target: str,
    allow_overwrite: bool = False,
) -> dict[str, Any]:
    if not proposal:
        return {
            "status": "error",
            "ok": False,
            "checks": [],
            "message": "Proposal not found.",
        }

    if target not in {"experimental", "production"}:
        return {
            "status": "error",
            "ok": False,
            "checks": [],
            "message": f"Unknown promotion target: {target}",
        }

    checks = []

    validation = validate_proposal_record(proposal)
    checks.append({
        "check": "proposal_validation",
        "ok": validation.get("ok", False),
        "message": validation.get("message", "Unknown validation result."),
    })
    if not validation.get("ok"):
        return {
            "status": "error",
            "ok": False,
            "checks": checks,
            "message": "Proposal validation failed.",
        }

    tool_name = ((validation.get("tool_spec_preview") or {}).get("name") or "").strip()
    filename = (proposal.get("filename") or "").strip()
    code = proposal.get("code") or ""

    base_dir = (
        "/opt/house-ai/experimental_tools"
        if target == "experimental"
        else "/opt/house-ai/tools"
    )

    path_ok, path_or_msg = _safe_target_path(base_dir, filename)
    checks.append({
        "check": "safe_target_path",
        "ok": path_ok,
        "message": path_or_msg,
    })
    if not path_ok:
        return {
            "status": "error",
            "ok": False,
            "checks": checks,
            "message": path_or_msg,
        }

    target_path = path_or_msg

    exists = os.path.exists(target_path)
    overwrite_ok = (not exists) or allow_overwrite
    checks.append({
        "check": "target_file_overwrite",
        "ok": overwrite_ok,
        "message": (
            "Target file does not exist."
            if not exists else
            ("Target file exists but overwrite is allowed." if allow_overwrite else "Target file already exists.")
        ),
    })
    if not overwrite_ok:
        return {
            "status": "error",
            "ok": False,
            "checks": checks,
            "message": "Target file already exists. Set allow_overwrite=true to continue.",
            "target_path": target_path,
        }

    collision = _tool_name_collision(tool_name, target)
    checks.append({
        "check": "tool_name_collision",
        "ok": collision["ok"],
        "message": collision["message"],
    })
    if not collision["ok"]:
        return {
            "status": "error",
            "ok": False,
            "checks": checks,
            "message": collision["message"],
            "target_path": target_path,
        }

    compile_check = _compile_code_in_tempfile(code)
    checks.append({
        "check": "temporary_compile",
        "ok": compile_check["ok"],
        "message": compile_check["message"],
    })
    if not compile_check["ok"]:
        return {
            "status": "error",
            "ok": False,
            "checks": checks,
            "message": compile_check["message"],
            "target_path": target_path,
        }

    return {
        "status": "ok",
        "ok": True,
        "checks": checks,
        "message": f"Preflight passed for {target} promotion.",
        "target_path": target_path,
        "tool_name": tool_name,
    }
