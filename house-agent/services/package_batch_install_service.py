from typing import Any

from services.package_install_executor import install_python_package


def install_missing_packages_batch(
    missing_packages: list[dict[str, Any]],
    admin_password: str,
) -> dict[str, Any]:
    results = []
    installed = 0
    failed = 0

    seen = set()

    for item in missing_packages or []:
        package_name = (item.get("package_name") or "").strip()
        module_name = (item.get("module") or "").strip()

        if not package_name:
            continue

        if package_name in seen:
            continue
        seen.add(package_name)

        result = install_python_package(
            package_name=package_name,
            admin_password=admin_password,
        )

        results.append({
            "module": module_name,
            "package_name": package_name,
            "result": result,
        })

        if result.get("ok"):
            installed += 1
        else:
            failed += 1

    return {
        "ok": failed == 0,
        "installed_count": installed,
        "failed_count": failed,
        "results": results,
        "answer": (
            f"Installed {installed} package(s) successfully."
            if failed == 0
            else f"Installed {installed} package(s), {failed} failed."
        ),
    }
