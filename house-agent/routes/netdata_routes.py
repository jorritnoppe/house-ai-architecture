from flask import Blueprint, jsonify, request

from services.netdata_service import (
    NetdataError,
    get_all_nodes_overview,
    get_alarms,
    get_node_summary,
)

netdata_bp = Blueprint("netdata_bp", __name__)

@netdata_bp.route("/ai/nodes/health", methods=["GET"])
def ai_nodes_health():
    try:
        overview = get_all_nodes_overview()
        result = {}

        for node, entry in overview.items():
            if entry.get("status") != "ok":
                result[node] = {
                    "status": "offline_or_error",
                    "error": entry.get("error")
                }
                continue

            summary = entry.get("summary", {})
            result[node] = {
                "status": summary.get("health_status", "ok"),
                "cpu_total_percent": summary.get("cpu_total_percent"),
                "ram_used_percent": summary.get("ram_used_percent"),
                "load1": summary.get("load1"),
                "active_alarm_count": summary.get("active_alarm_count", 0)
            }

        return jsonify({
            "status": "ok",
            "data": result
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@netdata_bp.route("/ai/node/summary", methods=["GET"])
def ai_node_summary():
    node = request.args.get("node")
    if not node:
        return jsonify({"status": "error", "error": "Missing node parameter"}), 400

    try:
        return jsonify({
            "status": "ok",
            "data": get_node_summary(node)
        })
    except NetdataError as e:
        return jsonify({"status": "error", "error": str(e)}), 502
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@netdata_bp.route("/ai/node/alerts", methods=["GET"])
def ai_node_alerts():
    node = request.args.get("node")
    if not node:
        return jsonify({"status": "error", "error": "Missing node parameter"}), 400

    try:
        return jsonify({
            "status": "ok",
            "data": get_alarms(node)
        })
    except NetdataError as e:
        return jsonify({"status": "error", "error": str(e)}), 502
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@netdata_bp.route("/ai/nodes/overview", methods=["GET"])
def ai_nodes_overview():
    try:
        return jsonify({
            "status": "ok",
            "data": get_all_nodes_overview()
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
