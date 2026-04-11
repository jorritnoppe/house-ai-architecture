import ast
import os
import tempfile
import traceback
from typing import Any


REQUIRED_TOOL_SPEC_KEYS = ["name", "description", "parameters", "safety"]


def validate_proposed_tool_code(code: str) -> dict[str, Any]:
    code = code or ""

    if not code.strip():
        return {
            "status": "error",
            "ok": False,
            "checks": [],
            "message": "Code is empty.",
        }

    checks = []

    # 1. Syntax check
    try:
        ast.parse(code)
        checks.append({
            "check": "python_syntax",
            "ok": True,
            "message": "Python syntax is valid.",
        })
    except SyntaxError as e:
        return {
            "status": "error",
            "ok": False,
            "checks": [{
                "check": "python_syntax",
                "ok": False,
                "message": f"Syntax error at line {e.lineno}: {e.msg}",
            }],
            "message": f"Syntax error at line {e.lineno}: {e.msg}",
        }

    namespace = {}

    # 2. Execute in isolated namespace
    try:
        exec(code, namespace, namespace)
        checks.append({
            "check": "module_exec",
            "ok": True,
            "message": "Code executed successfully in isolated validation context.",
        })
    except Exception as e:
        return {
            "status": "error",
            "ok": False,
            "checks": checks + [{
                "check": "module_exec",
                "ok": False,
                "message": f"Execution/import failed: {e}",
                "traceback": traceback.format_exc(),
            }],
            "message": f"Execution/import failed: {e}",
        }

    # 3. TOOL_SPEC existence
    tool_spec = namespace.get("TOOL_SPEC")
    if tool_spec is None:
        return {
            "status": "error",
            "ok": False,
            "checks": checks + [{
                "check": "tool_spec_exists",
                "ok": False,
                "message": "TOOL_SPEC is missing.",
            }],
            "message": "TOOL_SPEC is missing.",
        }

    checks.append({
        "check": "tool_spec_exists",
        "ok": True,
        "message": "TOOL_SPEC exists.",
    })

    # 4. TOOL_SPEC type
    if not isinstance(tool_spec, dict):
        return {
            "status": "error",
            "ok": False,
            "checks": checks + [{
                "check": "tool_spec_type",
                "ok": False,
                "message": "TOOL_SPEC must be a dict.",
            }],
            "message": "TOOL_SPEC must be a dict.",
        }

    checks.append({
        "check": "tool_spec_type",
        "ok": True,
        "message": "TOOL_SPEC is a dict.",
    })

    # 5. TOOL_SPEC required keys
    missing_keys = [k for k in REQUIRED_TOOL_SPEC_KEYS if k not in tool_spec]
    if missing_keys:
        return {
            "status": "error",
            "ok": False,
            "checks": checks + [{
                "check": "tool_spec_required_keys",
                "ok": False,
                "message": f"TOOL_SPEC missing required keys: {missing_keys}",
            }],
            "message": f"TOOL_SPEC missing required keys: {missing_keys}",
        }

    checks.append({
        "check": "tool_spec_required_keys",
        "ok": True,
        "message": "TOOL_SPEC contains all required keys.",
    })

    # 6. run function existence
    run_func = namespace.get("run")
    if run_func is None or not callable(run_func):
        return {
            "status": "error",
            "ok": False,
            "checks": checks + [{
                "check": "run_exists",
                "ok": False,
                "message": "run(args) function is missing or not callable.",
            }],
            "message": "run(args) function is missing or not callable.",
        }

    checks.append({
        "check": "run_exists",
        "ok": True,
        "message": "run(args) exists and is callable.",
    })

    return {
        "status": "ok",
        "ok": True,
        "checks": checks,
        "message": "Proposal validation passed.",
        "tool_spec_preview": {
            "name": tool_spec.get("name"),
            "description": tool_spec.get("description"),
            "safety": tool_spec.get("safety"),
        },
    }


def validate_proposal_record(proposal: dict[str, Any]) -> dict[str, Any]:
    if not proposal:
        return {
            "status": "error",
            "ok": False,
            "message": "Proposal not found.",
            "checks": [],
        }

    code = proposal.get("code") or ""
    return validate_proposed_tool_code(code)
