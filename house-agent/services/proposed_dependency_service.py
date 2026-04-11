import ast
import importlib.util
import os
from typing import Any


PACKAGE_NAME_MAP = {
    "yaml": "PyYAML",
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "Crypto": "pycryptodome",
    "serial": "pyserial",
    "dns": "dnspython",
    "requests": "requests",
    "flask": "Flask",
    "influxdb_client": "influxdb-client",
    "pymodbus": "pymodbus",
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "scipy": "scipy",
    "psutil": "psutil",
    "paramiko": "paramiko",
    "docker": "docker",
    "redis": "redis",
    "openai": "openai",
    "websockets": "websockets",
    "aiohttp": "aiohttp",
    "lxml": "lxml",
}


def _stdlib_modules() -> set[str]:
    try:
        return set(getattr(__import__("sys"), "stdlib_module_names", set()))
    except Exception:
        return set()


def _extract_imports_from_code(code: str) -> list[str]:
    tree = ast.parse(code)
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    imports.add(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])

    return sorted(imports)


def _local_project_modules() -> set[str]:
    project_root = "/opt/house-ai"
    names = set()

    for entry in os.listdir(project_root):
        if entry.endswith(".py"):
            names.add(entry[:-3])

    for folder in ["services", "tools", "experimental_tools", "routes"]:
        folder_path = os.path.join(project_root, folder)
        if os.path.isdir(folder_path):
            for entry in os.listdir(folder_path):
                if entry.endswith(".py"):
                    names.add(entry[:-3])

    return names


def _is_installed_module(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def analyze_python_dependencies(code: str) -> dict[str, Any]:
    imports = _extract_imports_from_code(code)
    stdlib = _stdlib_modules()
    local_modules = _local_project_modules()

    stdlib_imports = []
    local_imports = []
    third_party_imports = []

    for name in imports:
        if name in stdlib:
            stdlib_imports.append(name)
        elif name in local_modules:
            local_imports.append(name)
        else:
            third_party_imports.append(name)

    installed_packages = []
    missing_packages = []

    for module_name in third_party_imports:
        pip_name = PACKAGE_NAME_MAP.get(module_name, module_name)
        installed = _is_installed_module(module_name)

        item = {
            "module": module_name,
            "package_name": pip_name,
            "installed": installed,
        }

        if installed:
            installed_packages.append(item)
        else:
            missing_packages.append(item)

    return {
        "status": "ok",
        "imports_found": imports,
        "stdlib_imports": stdlib_imports,
        "local_imports": local_imports,
        "third_party_imports": third_party_imports,
        "installed_packages": installed_packages,
        "missing_packages": missing_packages,
        "requires_install": len(missing_packages) > 0,
    }
