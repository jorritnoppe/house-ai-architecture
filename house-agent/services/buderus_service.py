import os

from services.buderus_legacy_core import BuderusService
from extensions import app


def _env(name: str, default=None):
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _service():
    existing = app.extensions.get("buderus_service")
    if existing is not None:
        return existing

    influx_url = _env("BUDERUS_INFLUX_URL", _env("INFLUX_URL", "http://127.0.0.1:8086"))
    influx_token = _env("BUDERUS_INFLUX_TOKEN", _env("INFLUX_TOKEN"))
    influx_org = _env("BUDERUS_INFLUX_ORG", _env("INFLUX_ORG"))
    bucket = _env("BUDERUS_INFLUX_BUCKET", "Buderus")
    measurement = _env("BUDERUS_MEASUREMENT", "Buderus")

    if not influx_token or influx_token == "CHANGE_ME":
        raise RuntimeError("Missing valid BUDERUS_INFLUX_TOKEN or INFLUX_TOKEN")

    if not influx_org:
        raise RuntimeError("Missing BUDERUS_INFLUX_ORG or INFLUX_ORG")

    svc = BuderusService(
        influx_url=influx_url,
        influx_token=influx_token,
        influx_org=influx_org,
        bucket=bucket,
        measurement=measurement,
    )

    app.extensions["buderus_service"] = svc
    return svc


def _wrap(intent: str, data: dict, answer: str) -> dict:
    return {
        "status": "ok",
        "answer": answer,
        "intents": [intent],
        "tool_data": {
            intent: data
        },
    }


def get_buderus_current_status_data():
    svc = _service()
    data = svc.current_summary()
    return _wrap(
        "buderus_current_status",
        data,
        svc.build_natural_answer(data, "buderus_current_status"),
    )


def get_buderus_heating_status_data():
    svc = _service()
    data = svc.heating_summary()
    return _wrap(
        "buderus_heating_status",
        data,
        svc.build_natural_answer(data, "buderus_heating_status"),
    )


def get_buderus_hot_water_status_data():
    svc = _service()
    data = svc.dhw_summary()
    return _wrap(
        "buderus_hot_water_status",
        data,
        svc.build_natural_answer(data, "buderus_hot_water_status"),
    )


def get_buderus_pressure_analysis_data():
    svc = _service()
    data = svc.pressure_analysis()
    return _wrap(
        "buderus_pressure_analysis",
        data,
        svc.build_natural_answer(data, "buderus_pressure_analysis"),
    )


def get_buderus_diagnostics_data():
    svc = _service()
    data = svc.diagnostics_summary()
    return _wrap(
        "buderus_diagnostics",
        data,
        svc.build_natural_answer(data, "buderus_diagnostics"),
    )


def get_buderus_boiler_health_summary_data():
    svc = _service()
    data = svc.boiler_health_summary()
    return _wrap(
        "buderus_boiler_health_summary",
        data,
        svc.build_natural_answer(data, "buderus_boiler_health_summary"),
    )
