import hashlib
import os
import subprocess
import sys
from typing import Any


def _check_admin_password(admin_password: str) -> tuple[bool, str | None]:
    expected_hash = os.getenv("EXPERIMENTAL_APPROVAL_PASSWORD_HASH", "").strip()
    if not expected_hash:
        return False, "Admin approval password hash is not configured."

    provided_hash = hashlib.sha256((admin_password or "").encode("utf-8")).hexdigest()
    if provided_hash != expected_hash:
        return False, "Invalid admin password."

    return True, None


def install_python_package(package_name: str, admin_password: str) -> dict[str, Any]:
    package_name = (package_name or "").strip()

    if not package_name:
        return {
            "ok": False,
            "error": "package_name is required",
        }

    ok, error = _check_admin_password(admin_password)
    if not ok:
        return {
            "ok": False,
            "error": error,
        }

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        package_name,
    ]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )

        return {
            "ok": completed.returncode == 0,
            "package_name": package_name,
            "command": " ".join(cmd),
            "returncode": completed.returncode,
            "stdout": (completed.stdout or "").strip(),
            "stderr": (completed.stderr or "").strip(),
            "answer": (
                f"Package {package_name} installed successfully."
                if completed.returncode == 0
                else f"Package install failed for {package_name}."
            ),
        }

    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "package_name": package_name,
            "error": f"Timed out while installing {package_name}.",
        }
