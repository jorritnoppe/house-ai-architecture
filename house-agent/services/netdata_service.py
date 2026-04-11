import json
import os
from typing import Any, Dict, Optional

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "netdata_nodes.json")


class NetdataError(Exception):
    pass


def load_nodes() -> Dict[str, str]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_node_base_url(node: str) -> str:
    nodes = load_nodes()
    if node not in nodes:
        raise NetdataError(f"Unknown node: {node}")
    return nodes[node].rstrip("/")


def netdata_get(node: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    base_url = get_node_base_url(node)
    url = f"{base_url}{path}"
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise NetdataError(f"Netdata request failed for {node}: {e}") from e


def get_info(node: str) -> Dict[str, Any]:
    return netdata_get(node, "/api/v1/info")


def get_alarms(node: str) -> Dict[str, Any]:
    return netdata_get(node, "/api/v1/alarms", {"all": "true"})


def get_chart_latest(node: str, chart: str) -> Dict[str, Any]:
    return netdata_get(
        node,
        "/api/v1/data",
        {
            "chart": chart,
            "format": "json",
            "points": 1,
            "after": -1,
            "options": "jsonwrap"
        }
    )


def _extract_latest_dimension_value(chart_data: Dict[str, Any], preferred_dimension: Optional[str] = None) -> Optional[float]:
    result = chart_data.get("result", {})
    labels = result.get("labels", [])
    data = result.get("data", [])

    if not labels or not data:
        return None

    row = data[-1]
    if not isinstance(row, list) or len(row) < 2:
        return None

    if preferred_dimension and preferred_dimension in labels:
        idx = labels.index(preferred_dimension)
        if idx < len(row):
            try:
                return float(row[idx])
            except (TypeError, ValueError):
                return None

    for idx in range(1, len(row)):
        try:
            return float(row[idx])
        except (TypeError, ValueError):
            continue

    return None




def get_node_summary(node: str) -> Dict[str, Any]:
    info = get_info(node)
    alarms = get_alarms(node)

    cpu_user = None
    cpu_system = None
    ram_used = None
    load1 = None

    cpu_error = None
    ram_error = None
    load_error = None

    try:
        cpu_data = get_chart_latest(node, "system.cpu")
        cpu_user = _extract_latest_dimension_value(cpu_data, "user")
        cpu_system = _extract_latest_dimension_value(cpu_data, "system")
    except Exception as e:
        cpu_error = str(e)

    try:
        ram_data = get_chart_latest(node, "system.ram")
        ram_used = _extract_latest_dimension_value(ram_data, "used")
    except Exception as e:
        ram_error = str(e)

    try:
        load_data = get_chart_latest(node, "system.load")
        load1 = _extract_latest_dimension_value(load_data, "load1")
    except Exception as e:
        load_error = str(e)

    active_alarms = []
    for _, alarm in alarms.get("alarms", {}).items():
        status = alarm.get("status")
        if status in ("WARNING", "CRITICAL"):
            active_alarms.append({
                "name": alarm.get("name"),
                "chart": alarm.get("chart"),
                "status": status,
                "summary": alarm.get("summary")
            })

    mirrored_hosts = info.get("mirrored_hosts", [])
    hostname = mirrored_hosts[0] if mirrored_hosts else None


    ram_total_mb = None
    ram_free_mb = None

    try:
        ram_free_mb = _extract_latest_dimension_value(ram_data, "free") if 'ram_data' in locals() else None
        if ram_free_mb is not None and ram_used is not None:
            ram_total_mb = ram_free_mb + ram_used
    except Exception:
        pass

    cpu_total_percent = None
    if cpu_user is not None or cpu_system is not None:
        cpu_total_percent = round((cpu_user or 0) + (cpu_system or 0), 3)

    ram_used_percent = None
    if ram_total_mb and ram_used is not None and ram_total_mb > 0:
        ram_used_percent = round((ram_used / ram_total_mb) * 100, 2)

    health_status = "ok"
    if active_alarms:
        statuses = {a.get("status") for a in active_alarms}
        if "CRITICAL" in statuses:
            health_status = "critical"
        elif "WARNING" in statuses:
            health_status = "warning"

    warnings = []

    if cpu_total_percent is not None and cpu_total_percent > 70:
        warnings.append("high_cpu")

    if ram_used_percent is not None and ram_used_percent > 75:
        warnings.append("high_ram")

    if load1 is not None and load1 > 2.0:
        warnings.append("high_load")

    if active_alarms:
        warnings.append("netdata_alarm")

    if warnings:
        health_status = "warning"



    return {
        "node": node,
        "hostname": hostname,
        "version": info.get("version"),
        "os": info.get("os"),
        "cpu_user_percent": cpu_user,
        "cpu_system_percent": cpu_system,
        "ram_used_mb": ram_used,
        "load1": load1,
        "active_alarm_count": len(active_alarms),
        "active_alarms": active_alarms[:10],

        "cpu_total_percent": cpu_total_percent,
        "ram_used_mb": ram_used,
        "ram_free_mb": ram_free_mb,
        "ram_total_mb": ram_total_mb,
        "ram_used_percent": ram_used_percent,
        "health_status": health_status,

        "warnings": warnings,

        "debug": {
            "cpu_error": cpu_error,
            "ram_error": ram_error,
            "load_error": load_error
        }
    }



def get_all_nodes_overview() -> Dict[str, Any]:
    nodes = load_nodes()
    overview = {}

    for node in nodes:
        try:
            overview[node] = {
                "status": "ok",
                "summary": get_node_summary(node)
            }
        except Exception as e:
            overview[node] = {
                "status": "error",
                "error": str(e)
            }

    return overview
