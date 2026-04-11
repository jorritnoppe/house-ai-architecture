from flask import Blueprint, jsonify

from services.influx_helpers import iso_now
from services.pdata_service import (
    get_pdata_energy_summary_data,
    get_pdata_compare_energy_data,
    get_pdata_all_fields_data,
    get_pdata_full_overview_data,
    get_pdata_gas_summary_data,
)

pdata_bp = Blueprint("pdata", __name__)


@pdata_bp.get("/ai/pdata_energy_summary")
def ai_pdata_energy_summary():
    data = get_pdata_energy_summary_data()

    if data["status"] != "ok":
        return jsonify({
            "status": "error",
            "message": "No Pdata energy data found",
            "timestamp": iso_now(),
        }), 404

    return jsonify({
        "status": "ok",
        "timestamp": iso_now(),
        **data,
    })


@pdata_bp.get("/ai/pdata_compare_energy")
def ai_pdata_compare_energy():
    data = get_pdata_compare_energy_data()

    if data["status"] != "ok":
        return jsonify({
            "status": "error",
            "message": "No Pdata comparison data found",
            "timestamp": iso_now(),
        }), 404

    return jsonify({
        "status": "ok",
        "timestamp": iso_now(),
        **data,
    })


@pdata_bp.get("/ai/pdata_all_fields")
def ai_pdata_all_fields():
    data = get_pdata_all_fields_data()

    if data["status"] != "ok":
        return jsonify({
            "status": "error",
            "message": "No Pdata fields found",
            "timestamp": iso_now(),
        }), 404

    return jsonify({
        "status": "ok",
        "timestamp": iso_now(),
        **data,
    })


@pdata_bp.get("/ai/pdata_full_overview")
def ai_pdata_full_overview():
    data = get_pdata_full_overview_data()

    if data["status"] != "ok":
        return jsonify({
            "status": "error",
            "message": "No Pdata overview data found",
            "timestamp": iso_now(),
        }), 404

    return jsonify({
        "status": "ok",
        "timestamp": iso_now(),
        **data,
    })


@pdata_bp.get("/ai/pdata_gas_summary")
def ai_pdata_gas_summary():
    data = get_pdata_gas_summary_data()

    if data["status"] != "ok":
        return jsonify({
            "status": "error",
            "message": "No Pdata gas fields found",
            "timestamp": iso_now(),
        }), 404

    return jsonify({
        "status": "ok",
        "timestamp": iso_now(),
        **data,
    })
