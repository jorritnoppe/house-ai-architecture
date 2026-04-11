import json
import os
import subprocess
from typing import Dict, List

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "service_nodes.json")


def _load_config() -> Dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _run_systemctl_status(service_name: str) -> Dict:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        state = (result.stdout or "").strip() or "unknown"
        return {
            "service": service_name,
            "status": state,
        }
    except Exception as e:
        return {
            "service": service_name,
            "status": "error",
            "error": str(e),
        }


def _get_remote_http_health(url: str, node: str) -> Dict:
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        payload = r.json()

        return {
            "node": node,
            "mode": "remote_http",
            "overall_status": payload.get("overall_status", "unknown"),
            "services": payload.get("services", []),
            "warnings": payload.get("warnings", []),
        }
    except Exception as e:
        return {
            "node": node,
            "mode": "remote_http",
            "overall_status": "error",
            "services": [],
            "warnings": [f"remote_http_failed: {e}"],
        }


def get_service_health_for_node(node: str) -> Dict:
    config = _load_config()
    node_cfg = config.get(node)

    if not node_cfg:
        return {
            "node": node,
            "overall_status": "error",
            "services": [],
            "warnings": [f"unknown node {node}"],
        }

    mode = node_cfg.get("mode", "unknown")
    services = node_cfg.get("services", [])

    if mode == "local_systemctl":
        results: List[Dict] = []
        warnings: List[str] = []

        for service_name in services:
            entry = _run_systemctl_status(service_name)
            results.append(entry)
            if entry.get("status") != "active":
                warnings.append(service_name)

        return {
            "node": node,
            "mode": mode,
            "overall_status": "ok" if not warnings else "warning",
            "services": results,
            "warnings": warnings,
        }

    if mode == "remote_http":
        url = node_cfg.get("url")
        if not url:
            return {
                "node": node,
                "mode": mode,
                "overall_status": "error",
                "services": [],
                "warnings": ["missing remote_http url"],
            }
        return _get_remote_http_health(url, node)

    return {
        "node": node,
        "mode": mode,
        "overall_status": "unknown",
        "services": [{"service": s, "status": "not_checked_yet"} for s in services],
        "warnings": ["remote checks not implemented yet"],
    }


def get_services_overview() -> Dict:
    config = _load_config()
    result = {}

    for node in config.keys():
        result[node] = get_service_health_for_node(node)

    return result


def get_local_service_health() -> Dict:
    return get_service_health_for_node("house-ai-server")
