import hashlib
import os

from flask import Blueprint, jsonify, request

from extensions import tool_registry, experimental_tool_registry
from services.ai_tool_generator import generate_proposed_tool_file


from services.experimental_security import (
    write_experimental_audit,
    check_experimental_cooldown,
    mark_experimental_cooldown,
    write_package_install_audit,
)





from services.proposed_tool_service import (
    list_proposed_tools,
    read_proposed_tool,
    save_proposed_tool,
    approve_proposed_tool,
    reject_proposed_tool,
)
from services.tool_promoter import (
    promote_proposed_to_experimental,
    promote_experimental_to_production,
)
from services.proposed_dependency_service import analyze_python_dependencies

from services.package_install_service import build_install_plan
from services.package_install_executor import install_python_package

from services.package_batch_install_service import install_missing_packages_batch
from services.proposed_tool_validation_service import validate_proposal_record
from services.proposed_promotion_guard_service import preflight_promotion_check

from services.proposed_promotion_audit_service import (
    add_promotion_audit_record,
    list_promotion_audit,
)
from services.proposed_dependency_service import analyze_python_dependencies





tools_bp = Blueprint("tools", __name__)


@tools_bp.get("/tools")
def list_tools():
    return jsonify({
        "status": "ok",
        "count": len(tool_registry.list_tool_specs()),
        "tools": tool_registry.list_tool_specs(),
    })


@tools_bp.post("/tools/execute")
def execute_tool():
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name")
    args = body.get("args", {}) or {}

    if not tool_name:
        return jsonify({
            "status": "error",
            "message": "Missing required field: tool_name",
        }), 400

    try:
        result = tool_registry.execute(tool_name, args)
        return jsonify({
            "status": "ok",
            "tool_name": tool_name,
            "result": result,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "tool_name": tool_name,
            "message": str(e),
        }), 500


@tools_bp.get("/experimental-tools")
def list_experimental_tools():
    return jsonify({
        "status": "ok",
        "count": len(experimental_tool_registry.list_tool_specs()),
        "tools": experimental_tool_registry.list_tool_specs(),
    })


@tools_bp.post("/experimental-tools/execute")
def execute_experimental_tool():
    body = request.get_json(silent=True) or {}

    tool_name = body.get("tool_name")
    args = body.get("args", {}) or {}
    approved = body.get("approved", False)
    admin_password = body.get("admin_password", "")

    if not tool_name:
        return jsonify({
            "status": "error",
            "message": "Missing required field: tool_name",
        }), 400

    tool_spec = next(
        (tool for tool in experimental_tool_registry.list_tool_specs() if tool.get("name") == tool_name),
        None,
    )

    if not tool_spec:
        write_experimental_audit(
            event="experimental_execute_denied",
            tool_name=tool_name,
            args=args,
            source="api",
            status="error",
            details="unknown experimental tool",
        )
        return jsonify({
            "status": "error",
            "tool_name": tool_name,
            "message": f"Unknown experimental tool: {tool_name}",
        }), 404

    if not approved:
        write_experimental_audit(
            event="experimental_execute_blocked",
            tool_name=tool_name,
            args=args,
            source="api",
            status="approval_required",
            details="explicit admin approval required",
        )
        return jsonify({
            "status": "approval_required",
            "tool_name": tool_name,
            "message": f"Experimental tool '{tool_name}' requires explicit admin approval before execution.",
            "args": args,
        }), 403

    expected_hash = os.getenv("EXPERIMENTAL_APPROVAL_PASSWORD_HASH", "").strip()
    if not expected_hash:
        write_experimental_audit(
            event="experimental_execute_denied",
            tool_name=tool_name,
            args=args,
            source="api",
            status="error",
            details="approval password hash not configured",
        )
        return jsonify({
            "status": "error",
            "tool_name": tool_name,
            "message": "Admin approval password hash is not configured. Set EXPERIMENTAL_APPROVAL_PASSWORD_HASH in .env",
        }), 500

    provided_hash = hashlib.sha256(admin_password.encode("utf-8")).hexdigest()
    if provided_hash != expected_hash:
        write_experimental_audit(
            event="experimental_execute_denied",
            tool_name=tool_name,
            args=args,
            source="api",
            status="denied",
            details="invalid admin password",
        )
        return jsonify({
            "status": "denied",
            "tool_name": tool_name,
            "message": "Experimental tool execution denied.",
        }), 403

    cooldown = check_experimental_cooldown(tool_name, cooldown_seconds=10)
    if not cooldown["ok"]:
        write_experimental_audit(
            event="experimental_execute_blocked",
            tool_name=tool_name,
            args=args,
            source="api",
            status="cooldown",
            details=f"cooldown active, wait {cooldown['wait_seconds']} seconds",
        )
        return jsonify({
            "status": "cooldown",
            "tool_name": tool_name,
            "message": f"Experimental tool '{tool_name}' is cooling down. Try again in {cooldown['wait_seconds']} seconds.",
            "wait_seconds": cooldown["wait_seconds"],
        }), 429

    try:
        result = experimental_tool_registry.execute(tool_name, args)
        mark_experimental_cooldown(tool_name)

        write_experimental_audit(
            event="experimental_execute_approved",
            tool_name=tool_name,
            args=args,
            source="api",
            status="ok",
            details="experimental tool executed successfully",
        )

        return jsonify({
            "status": "ok",
            "tool_name": tool_name,
            "result": result,
        })
    except Exception as e:
        write_experimental_audit(
            event="experimental_execute_failed",
            tool_name=tool_name,
            args=args,
            source="api",
            status="error",
            details=str(e),
        )
        return jsonify({
            "status": "error",
            "tool_name": tool_name,
            "message": str(e),
        }), 500


@tools_bp.post("/proposed-tools/generate")
def generate_proposed_tool():
    body = request.get_json(silent=True) or {}

    name = (body.get("name") or "").strip()
    description = (body.get("description") or "").strip()
    code = body.get("code")

    if not name:
        return jsonify({
            "status": "error",
            "message": "Missing required field: name",
        }), 400

    if not description:
        return jsonify({
            "status": "error",
            "message": "Missing required field: description",
        }), 400

    if not code or not str(code).strip():
        return jsonify({
            "status": "error",
            "message": "Missing required field: code",
        }), 400

    try:
        result = generate_proposed_tool_file(
            name=name,
            description=description,
            code=code,
        )

        dependency_analysis = analyze_python_dependencies(code)

        return jsonify({
            "status": "ok",
            "proposal": result,
            "dependency_analysis": dependency_analysis,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500



@tools_bp.get("/proposed-tools")
def list_proposed():
    items = list_proposed_tools()
    return jsonify({
        "status": "ok",
        "count": len(items),
        "tools": items,
    })


@tools_bp.get("/proposed-tools/<proposal_id>")
def get_proposed(proposal_id):
    try:
        item = read_proposed_tool(proposal_id)
        return jsonify({
            "status": "ok",
            "tool": item,
        })
    except FileNotFoundError:
        return jsonify({
            "status": "error",
            "message": f"Proposed tool not found: {proposal_id}",
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 400


@tools_bp.post("/proposed-tools/save")
def save_proposed():
    body = request.get_json(silent=True) or {}

    tool_name = (body.get("tool_name") or "").strip()
    code = body.get("code") or ""
    description = (body.get("description") or "").strip()
    filename = (body.get("filename") or "").strip()
    requested_by = (body.get("requested_by") or "ai").strip()
    notes = body.get("notes")

    if not tool_name:
        return jsonify({
            "status": "error",
            "message": "Missing required field: tool_name",
        }), 400

    if not code.strip():
        return jsonify({
            "status": "error",
            "message": "Missing required field: code",
        }), 400

    try:
        result = save_proposed_tool({
            "tool_name": tool_name,
            "code": code,
            "description": description,
            "requested_by": requested_by,
            "notes": notes,
            "filename": filename or f"{tool_name}.py",
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 400


@tools_bp.post("/proposed-tools/<proposal_id>/approve")
def approve_proposed(proposal_id):
    body = request.get_json(silent=True) or {}
    approved_by = (body.get("approved_by") or "admin").strip()

    result = approve_proposed_tool(proposal_id, approved_by=approved_by)
    if result is None:
        return jsonify({
            "status": "error",
            "message": f"Proposed tool not found: {proposal_id}",
        }), 404

    return jsonify({
        "status": "ok",
        "message": "Proposal approved.",
        "tool": result,
    })



@tools_bp.post("/proposed-tools/<proposal_id>/reject")
def reject_proposed(proposal_id):
    tool = reject_proposed_tool(proposal_id)
    if tool is None:
        return jsonify({
            "status": "error",
            "message": f"Proposed tool not found: {proposal_id}",
        }), 404

    return jsonify({
        "status": "ok",
        "message": "Proposal rejected.",
        "tool": tool,
    })







@tools_bp.post("/proposed-tools/<proposal_id>/promote")
def promote_proposed(proposal_id):
    body = request.get_json(silent=True) or {}
    allow_overwrite = bool(body.get("allow_overwrite", False))

    try:
        proposal = read_proposed_tool(proposal_id)
        if not proposal:
            return jsonify({
                "status": "error",
                "message": f"Proposed tool not found: {proposal_id}",
            }), 404

        if proposal.get("status") != "approved":
            return jsonify({
                "status": "error",
                "message": "Only approved proposals can be promoted to experimental.",
            }), 400

        validation = validate_proposal_record(proposal)
        preflight = preflight_promotion_check(
            proposal=proposal,
            target="experimental",
            allow_overwrite=allow_overwrite,
        )
        dependency_analysis = analyze_python_dependencies(proposal.get("code") or "")


        add_promotion_audit_record(
            proposal_id=proposal_id,
            target="experimental",
            proposal_status=proposal.get("status", ""),
            target_path=preflight.get("target_path"),
            allow_overwrite=allow_overwrite,
            validation=validation,
            preflight=preflight,
            dependency_analysis=dependency_analysis,
            actor="admin",
        )


        if not preflight.get("ok"):
            return jsonify({
                "status": "error",
                "message": "Proposal failed preflight and cannot be promoted to experimental.",
                "proposal_id": proposal_id,
                "preflight": preflight,
            }), 400

        result = promote_proposed_to_experimental(proposal_id)
        return jsonify(result)

    except FileNotFoundError:
        return jsonify({
            "status": "error",
            "message": f"Proposed tool not found: {proposal_id}",
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 400




@tools_bp.post("/proposed-tools/<proposal_id>/promote-to-production")
def promote_to_production(proposal_id):
    body = request.get_json(silent=True) or {}
    allow_overwrite = bool(body.get("allow_overwrite", False))

    try:
        proposal = read_proposed_tool(proposal_id)
        if not proposal:
            return jsonify({
                "status": "error",
                "message": f"Proposed tool not found: {proposal_id}",
            }), 404

        if proposal.get("status") not in {"approved", "promoted_to_experimental"}:
            return jsonify({
                "status": "error",
                "message": "Only approved or experimentally promoted proposals can be promoted to production.",
            }), 400

        validation = validate_proposal_record(proposal)
        preflight = preflight_promotion_check(
            proposal=proposal,
            target="production",
            allow_overwrite=allow_overwrite,
        )
        dependency_analysis = analyze_python_dependencies(proposal.get("code") or "")

        add_promotion_audit_record(
            proposal_id=proposal_id,
            target="production",
            proposal_status=proposal.get("status", ""),
            target_path=preflight.get("target_path"),
            allow_overwrite=allow_overwrite,
            validation=validation,
            preflight=preflight,
            dependency_analysis=dependency_analysis,
            actor="admin",
        )


        if not preflight.get("ok"):
            return jsonify({
                "status": "error",
                "message": "Proposal failed preflight and cannot be promoted to production.",
                "proposal_id": proposal_id,
                "preflight": preflight,
            }), 400

        result = promote_experimental_to_production(proposal_id)
        return jsonify(result)

    except FileNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 400










@tools_bp.post("/proposed-tools/analyze-dependencies")
def analyze_proposed_dependencies():
    body = request.get_json(silent=True) or {}
    code = body.get("code") or ""

    if not code.strip():
        return jsonify({
            "status": "error",
            "message": "Missing required field: code",
        }), 400

    try:
        result = analyze_python_dependencies(code)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 400


@tools_bp.post("/proposed-tools/install-plan")
def proposed_tool_install_plan():
    body = request.get_json(silent=True) or {}
    code = body.get("code") or ""

    if not code.strip():
        return jsonify({
            "status": "error",
            "message": "Missing required field: code",
        }), 400

    try:
        dependency_analysis = analyze_python_dependencies(code)
        install_plan = build_install_plan(dependency_analysis)

        return jsonify({
            "status": "ok",
            "dependency_analysis": dependency_analysis,
            "install_plan": install_plan,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 400





@tools_bp.post("/proposed-tools/install-package")
def install_proposed_package():
    body = request.get_json(silent=True) or {}

    package_name = (body.get("package_name") or "").strip()
    admin_password = body.get("admin_password") or ""

    if not package_name:
        return jsonify({
            "status": "error",
            "message": "Missing required field: package_name",
        }), 400

    result = install_python_package(
        package_name=package_name,
        admin_password=admin_password,
    )

    if result.get("ok"):
        write_package_install_audit(
            package_name=package_name,
            status="ok",
            details=result.get("answer", ""),
            source="api",
        )
        return jsonify({
            "status": "ok",
            "result": result,
        })

    write_package_install_audit(
        package_name=package_name,
        status="error",
        details=result.get("error") or result.get("stderr") or "unknown error",
        source="api",
    )

    return jsonify({
        "status": "error",
        "result": result,
    }), 400



@tools_bp.post("/proposed-tools/<proposal_id>/install-missing-packages")
def install_missing_packages_for_proposal(proposal_id):
    body = request.get_json(silent=True) or {}

    admin_password = body.get("admin_password") or ""
    approved = body.get("approved", False)

    if not approved:
        return jsonify({
            "status": "approval_required",
            "message": "Installing missing packages requires explicit admin approval.",
            "proposal_id": proposal_id,
        }), 403

    proposal = read_proposed_tool(proposal_id)
    if not proposal:
        return jsonify({
            "status": "error",
            "message": f"Proposed tool not found: {proposal_id}",
        }), 404

    code = proposal.get("code") or ""
    if not code.strip():
        return jsonify({
            "status": "error",
            "message": "Proposal has no code to analyze.",
        }), 400

    dependency_analysis = analyze_python_dependencies(code)
    missing_packages = dependency_analysis.get("missing_packages", []) or []

    if not missing_packages:
        return jsonify({
            "status": "ok",
            "proposal_id": proposal_id,
            "dependency_analysis": dependency_analysis,
            "batch_result": {
                "ok": True,
                "installed_count": 0,
                "failed_count": 0,
                "results": [],
                "answer": "No missing packages were found.",
            },
        })

    batch_result = install_missing_packages_batch(
        missing_packages=missing_packages,
        admin_password=admin_password,
    )

    for item in batch_result.get("results", []):
        package_name = item.get("package_name") or "unknown"
        result = item.get("result") or {}
        if result.get("ok"):
            try:
                write_package_install_audit(
                    package_name=package_name,
                    status="ok",
                    details=result.get("answer", ""),
                    source="api_batch",
                )
            except Exception:
                pass
        else:
            try:
                write_package_install_audit(
                    package_name=package_name,
                    status="error",
                    details=result.get("error") or result.get("stderr") or "unknown error",
                    source="api_batch",
                )
            except Exception:
                pass

    refreshed_dependency_analysis = analyze_python_dependencies(code)

    return jsonify({
        "status": "ok" if batch_result.get("ok") else "error",
        "proposal_id": proposal_id,
        "dependency_analysis_before": dependency_analysis,
        "batch_result": batch_result,
        "dependency_analysis_after": refreshed_dependency_analysis,
    }), (200 if batch_result.get("ok") else 400)


@tools_bp.post("/proposed-tools/<proposal_id>/validate")
def validate_proposed_tool(proposal_id):
    proposal = read_proposed_tool(proposal_id)
    if not proposal:
        return jsonify({
            "status": "error",
            "message": f"Proposed tool not found: {proposal_id}",
        }), 404

    result = validate_proposal_record(proposal)

    return jsonify({
        "status": result.get("status", "error"),
        "proposal_id": proposal_id,
        "validation": result,
    }), (200 if result.get("ok") else 400)


@tools_bp.post("/proposed-tools/<proposal_id>/preflight")
def preflight_proposed_tool(proposal_id):
    body = request.get_json(silent=True) or {}
    target = (body.get("target") or "experimental").strip()
    allow_overwrite = bool(body.get("allow_overwrite", False))

    proposal = read_proposed_tool(proposal_id)
    if not proposal:
        return jsonify({
            "status": "error",
            "message": f"Proposed tool not found: {proposal_id}",
        }), 404

    result = preflight_promotion_check(
        proposal=proposal,
        target=target,
        allow_overwrite=allow_overwrite,
    )

    return jsonify({
        "status": result.get("status", "error"),
        "proposal_id": proposal_id,
        "preflight": result,
    }), (200 if result.get("ok") else 400)


@tools_bp.get("/proposed-tools/promotion-audit")
def get_promotion_audit():
    items = list_promotion_audit()
    return jsonify({
        "status": "ok",
        "count": len(items),
        "items": items,
    })



