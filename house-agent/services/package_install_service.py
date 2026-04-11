from typing import Any


def build_install_plan(dependency_analysis: dict[str, Any]) -> dict[str, Any]:
    missing = dependency_analysis.get("missing_packages", []) or []

    packages = []
    for item in missing:
        pkg = item.get("package_name")
        mod = item.get("module")
        if pkg:
            packages.append({
                "module": mod,
                "package_name": pkg,
                "apt_guess": None,
                "pip_command": f"pip install {pkg}",
            })

    return {
        "status": "ok",
        "requires_install": len(packages) > 0,
        "missing_count": len(packages),
        "packages": packages,
        "summary": (
            "No extra packages are required."
            if not packages
            else f"{len(packages)} package(s) appear to be missing."
        ),
    }
