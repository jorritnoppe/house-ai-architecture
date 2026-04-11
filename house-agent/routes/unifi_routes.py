from flask import Blueprint, jsonify
from services.unifi_collector import collector

unifi_bp = Blueprint("unifi_bp", __name__)


@unifi_bp.route("/ai/network/summary/compact", methods=["GET"])
def network_summary_compact():
    cache = collector.get_cache()
    summary = cache.get("summary", {})
    clients = cache.get("clients", [])

    gw_cpu = None
    gw_mem = None
    wan_latency = None

    for row in summary.get("site_health_rows", []):
        if row.get("subsystem") == "wan":
            gw_stats = row.get("gw_system-stats", {}) or {}
            gw_cpu = gw_stats.get("cpu")
            gw_mem = gw_stats.get("mem")
            wan_info = row.get("uptime_stats", {}).get("WAN", {}) or {}
            wan_latency = wan_info.get("latency_average")

    unknown_count = sum(
        1 for c in clients
        if c.get("role") == "unknown" or c.get("room") == "unknown"
    )

    top_talker = None
    top_clients = summary.get("top_clients", [])
    if top_clients:
        top_talker = top_clients[0].get("name")

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "overall": summary.get("overall", "unknown"),
        "devices_online": summary.get("device_count_online", 0),
        "devices_offline": summary.get("device_count_offline", 0),
        "clients_active": summary.get("client_count_active", 0),
        "gateway_cpu_percent": gw_cpu,
        "gateway_mem_percent": gw_mem,
        "wan_latency_ms": wan_latency,
        "unknown_clients": unknown_count,
        "top_talker": top_talker,
        "last_error": cache.get("last_error"),
    })



@unifi_bp.route("/ai/network/alerts", methods=["GET"])
def network_alerts():
    cache = collector.get_cache()
    summary = cache.get("summary", {})
    devices = cache.get("devices", [])
    clients = cache.get("clients", [])

    alerts = []

    gw_cpu = None
    gw_mem = None

    for row in summary.get("site_health_rows", []):
        if row.get("subsystem") == "wan":
            gw_stats = row.get("gw_system-stats", {}) or {}
            gw_cpu = float(gw_stats.get("cpu", 0) or 0)
            gw_mem = float(gw_stats.get("mem", 0) or 0)

    if gw_mem is not None and gw_mem > 90:
        alerts.append({
            "severity": "warning",
            "type": "gateway_memory_high",
            "message": f"Gateway memory is high at {gw_mem:.1f}%"
        })

    if gw_cpu is not None and gw_cpu > 85:
        alerts.append({
            "severity": "warning",
            "type": "gateway_cpu_high",
            "message": f"Gateway CPU is high at {gw_cpu:.1f}%"
        })

    for d in devices:
        if d.get("critical") and d.get("state") != "online":
            alerts.append({
                "severity": "critical",
                "type": "critical_device_offline",
                "message": f"Critical device offline: {d.get('name')}"
            })

    for c in clients:
        if c.get("role") == "unknown" or c.get("room") == "unknown":
            alerts.append({
                "severity": "info",
                "type": "unknown_client",
                "message": f"Unknown or unmapped client: {c.get('name')} ({c.get('mac')})"
            })

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "count": len(alerts),
        "alerts": alerts,
        "last_error": cache.get("last_error"),
    })



@unifi_bp.route("/ai/network/inventory", methods=["GET"])
def network_inventory():
    cache = collector.get_cache()
    devices = cache.get("devices", [])
    clients = cache.get("clients", [])

    inventory = []

    for d in devices:
        inventory.append({
            "kind": "infrastructure",
            "name": d.get("name"),
            "role": d.get("role"),
            "room": d.get("room"),
            "mac": d.get("mac"),
            "ip": d.get("ip"),
            "state": d.get("state"),
            "critical": d.get("critical"),
            "portable": d.get("portable", False),
            "mapped": d.get("mapped", False),
            "type": d.get("type"),
            "model": d.get("model")
        })

    for c in clients:
        inventory.append({
            "kind": "client",
            "name": c.get("name"),
            "role": c.get("role"),
            "room": c.get("room"),
            "mac": c.get("mac"),
            "ip": c.get("ip"),
            "state": "online" if c.get("ip") else "stale",
            "critical": c.get("critical"),
            "portable": c.get("portable", False),
            "mapped": c.get("mapped", False),
            "type": "wired" if c.get("is_wired") else "wireless",
            "model": None
        })

    inventory = sorted(
        inventory,
        key=lambda x: (
            not bool(x.get("critical")),
            str(x.get("room") or ""),
            str(x.get("name") or "")
        )
    )

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "count": len(inventory),
        "inventory": inventory,
        "last_error": cache.get("last_error"),
    })




@unifi_bp.route("/ai/network/wifi-links", methods=["GET"])
def network_wifi_links():
    cache = collector.get_cache()
    clients = cache.get("clients", [])
    devices = cache.get("devices", [])

    ap_names = {
        d.get("mac"): d.get("name")
        for d in devices
        if d.get("type") == "uap"
    }

    grouped = {}
    for c in clients:
        ap_mac = c.get("ap_mac")
        if not ap_mac:
            continue
        key = ap_mac
        if key not in grouped:
            grouped[key] = {
                "ap_mac": ap_mac,
                "ap_name": ap_names.get(ap_mac, "unknown_ap"),
                "clients": []
            }
        grouped[key]["clients"].append(c)

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "wifi_links": grouped,
        "last_error": cache.get("last_error"),
    })

@unifi_bp.route("/ai/network/switch-ports", methods=["GET"])
def network_switch_ports():
    cache = collector.get_cache()
    clients = cache.get("clients", [])
    devices = cache.get("devices", [])

    switch_names = {
        d.get("mac"): d.get("name")
        for d in devices
        if d.get("type") in ("usw", "udm", "uxg", "ugw")
    }



    grouped = {}
    for c in clients:
        sw_mac = c.get("sw_mac")
        sw_port = c.get("sw_port")
        if not sw_mac or sw_port is None:
            continue

        switch_key = f"{sw_mac}:{sw_port}"
        if switch_key not in grouped:
            grouped[switch_key] = {
                "switch_mac": sw_mac,
                "switch_name": switch_names.get(sw_mac, "unknown_switch"),
                "port": sw_port,
                "clients": []
            }
        grouped[switch_key]["clients"].append(c)

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "switch_ports": grouped,
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/health/report", methods=["GET"])
def network_health_report():
    cache = collector.get_cache()
    summary = cache.get("summary", {})
    devices = cache.get("devices", [])
    clients = cache.get("clients", [])

    critical_devices = [d for d in devices if d.get("critical")]
    critical_clients = [c for c in clients if c.get("critical")]

    offline_critical_devices = [d for d in critical_devices if d.get("state") != "online"]
    stale_critical_clients = [c for c in critical_clients if not c.get("ip")]

    portable_clients = [c for c in clients if c.get("portable") or c.get("room") == "all"]
    unknown_clients = [c for c in clients if c.get("role") == "unknown" or c.get("room") == "unknown"]

    gw_cpu = None
    gw_mem = None
    wan_latency = None
    wan_uptime = None
    wan_download_mbps = None
    wan_upload_mbps = None

    for row in summary.get("site_health_rows", []):
        subsystem = row.get("subsystem")
        if subsystem == "wan":
            gw_stats = row.get("gw_system-stats", {}) or {}
            gw_cpu = gw_stats.get("cpu")
            gw_mem = gw_stats.get("mem")
            wan_info = row.get("uptime_stats", {}).get("WAN", {}) or {}
            wan_latency = wan_info.get("latency_average")
            wan_uptime = wan_info.get("uptime")
        elif subsystem == "www":
            wan_download_mbps = row.get("xput_down")
            wan_upload_mbps = row.get("xput_up")

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "overall": summary.get("overall", "unknown"),
        "counts": {
            "devices_total": summary.get("device_count_total", 0),
            "devices_online": summary.get("device_count_online", 0),
            "devices_offline": summary.get("device_count_offline", 0),
            "clients_active": summary.get("client_count_active", 0),
            "alarms": summary.get("alarm_count", 0),
            "mapped_clients": summary.get("mapped_clients", 0),
            "mapped_devices": summary.get("mapped_devices", 0)
        },
        "gateway": {
            "cpu_percent": gw_cpu,
            "mem_percent": gw_mem
        },
        "wan": {
            "latency_average_ms": wan_latency,
            "uptime_seconds": wan_uptime,
            "download_mbps": wan_download_mbps,
            "upload_mbps": wan_upload_mbps
        },
        "critical": {
            "devices_online": len(critical_devices) - len(offline_critical_devices),
            "devices_offline": len(offline_critical_devices),
            "clients_expected_online": len(critical_clients),
            "clients_stale": len(stale_critical_clients),
            "offline_device_names": [d.get("name") for d in offline_critical_devices],
            "stale_client_names": [c.get("name") for c in stale_critical_clients]
        },
        "portable_clients": [
            {
                "name": c.get("name"),
                "ip": c.get("ip"),
                "role": c.get("role"),
                "room": c.get("room"),
                "signal": c.get("signal"),
                "total_bytes": c.get("total_bytes", 0)
            }
            for c in portable_clients
        ],
        "unknown_clients": [
            {
                "name": c.get("name"),
                "ip": c.get("ip"),
                "mac": c.get("mac"),
                "role": c.get("role"),
                "room": c.get("room")
            }
            for c in unknown_clients
        ],
        "top_talkers": summary.get("top_clients", []),
        "last_error": cache.get("last_error")
    })


@unifi_bp.route("/ai/network/summary", methods=["GET"])
def network_summary():
    cache = collector.get_cache()
    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "summary": cache.get("summary"),
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/devices", methods=["GET"])
def network_devices():
    cache = collector.get_cache()
    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "devices": cache.get("devices", []),
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/clients", methods=["GET"])
def network_clients():
    cache = collector.get_cache()
    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "clients": cache.get("clients", []),
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/events", methods=["GET"])
def network_events():
    cache = collector.get_cache()
    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "events": cache.get("events", []),
        "alarms": cache.get("alarms", []),
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/topology-lite", methods=["GET"])
def network_topology_lite():
    cache = collector.get_cache()
    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "topology_lite": cache.get("topology_lite", {}),
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/reload-assets", methods=["POST"])
def network_reload_assets():
    collector.reload_asset_map()
    collector.refresh()
    cache = collector.get_cache()
    return jsonify({
        "status": "ok",
        "message": "UniFi asset map reloaded",
        "timestamp": cache.get("timestamp"),
    })


@unifi_bp.route("/ai/network/critical", methods=["GET"])
def network_critical():
    cache = collector.get_cache()
    devices = cache.get("devices", [])
    clients = cache.get("clients", [])

    critical_devices = [d for d in devices if d.get("critical")]
    critical_clients = [c for c in clients if c.get("critical")]

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "critical_devices": critical_devices,
        "critical_clients": critical_clients,
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/offline", methods=["GET"])
def network_offline():
    cache = collector.get_cache()
    devices = cache.get("devices", [])
    clients = cache.get("clients", [])

    offline_devices = [d for d in devices if d.get("state") != "online"]
    stale_clients = [c for c in clients if not c.get("ip")]

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "offline_devices": offline_devices,
        "stale_clients": stale_clients,
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/portable", methods=["GET"])
def network_portable():
    cache = collector.get_cache()
    clients = cache.get("clients", [])

    portable_clients = [
        c for c in clients
        if c.get("portable") or c.get("room") == "all"
    ]

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "portable_clients": portable_clients,
        "count": len(portable_clients),
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/unknown", methods=["GET"])
def network_unknown():
    cache = collector.get_cache()
    devices = cache.get("devices", [])
    clients = cache.get("clients", [])

    unknown_devices = [d for d in devices if not d.get("mapped")]
    unknown_clients = [
        c for c in clients
        if (not c.get("mapped")) or c.get("role") in ("unknown", "client")
    ]

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "unknown_devices": unknown_devices,
        "unknown_clients": unknown_clients,
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/top-talkers", methods=["GET"])
def network_top_talkers():
    cache = collector.get_cache()
    clients = cache.get("clients", [])

    ranked = sorted(
        clients,
        key=lambda x: x.get("total_bytes", 0),
        reverse=True
    )[:20]

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "top_talkers": ranked,
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/rooms", methods=["GET"])
def network_rooms():
    cache = collector.get_cache()
    devices = cache.get("devices", [])
    clients = cache.get("clients", [])

    rooms = {}

    def add_item(room_name, item_type, item):
        room_key = room_name or "unknown"
        if room_key not in rooms:
            rooms[room_key] = {
                "devices": [],
                "clients": []
            }
        rooms[room_key][item_type].append(item)

    for d in devices:
        add_item(d.get("room"), "devices", d)

    for c in clients:
        add_item(c.get("room"), "clients", c)

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "rooms": rooms,
        "last_error": cache.get("last_error"),
    })


@unifi_bp.route("/ai/network/device/<path:query>", methods=["GET"])
def network_device_lookup(query):
    cache = collector.get_cache()
    devices = cache.get("devices", [])
    clients = cache.get("clients", [])

    q = str(query).strip().lower()

    matched_devices = [
        d for d in devices
        if q in str(d.get("name", "")).lower() or q == str(d.get("mac", "")).lower()
    ]
    matched_clients = [
        c for c in clients
        if q in str(c.get("name", "")).lower()
        or q in str(c.get("hostname", "")).lower()
        or q == str(c.get("mac", "")).lower()
        or q == str(c.get("ip", "")).lower()
    ]

    return jsonify({
        "status": cache.get("status"),
        "timestamp": cache.get("timestamp"),
        "query": query,
        "devices": matched_devices,
        "clients": matched_clients,
        "last_error": cache.get("last_error"),
    })
