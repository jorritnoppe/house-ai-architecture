from config import INFLUX_BUCKET
from extensions import query_api
from services.influx_helpers import iso_now, query_latest_for_fields


def get_power_now_data():
    data = query_latest_for_fields(["total_power", "power_demand"], range_window="-24h")

    power = None
    source_field = None

    if data.get("total_power") and data["total_power"] is not None:
        power = data["total_power"]["value"]
        source_field = "total_power"
    elif data.get("power_demand") and data["power_demand"] is not None:
        power = data["power_demand"]["value"]
        source_field = "power_demand"

    return {
        "status": "ok",
        "power_watts": power,
        "source_field": source_field,
        "timestamp": iso_now(),
    }


def get_energy_summary_data():
    fields = [
        "total_power",
        "power_demand",
        "import_kWh",
        "export_kWh",
        "frequency",
        "total_pf",
        "total_va",
        "total_var",
    ]

    data = query_latest_for_fields(fields, range_window="-30d")

    current_power = None
    if data.get("total_power") and data["total_power"] is not None:
        current_power = data["total_power"]["value"]
    elif data.get("power_demand") and data["power_demand"] is not None:
        current_power = data["power_demand"]["value"]

    return {
        "status": "ok",
        "timestamp": iso_now(),
        "power_watts": current_power,
        "import_kwh_total": data["import_kWh"]["value"] if data.get("import_kWh") else None,
        "export_kwh_total": data["export_kWh"]["value"] if data.get("export_kWh") else None,
        "frequency_hz": data["frequency"]["value"] if data.get("frequency") else None,
        "power_factor": data["total_pf"]["value"] if data.get("total_pf") else None,
        "apparent_power_va": data["total_va"]["value"] if data.get("total_va") else None,
        "reactive_power_var": data["total_var"]["value"] if data.get("total_var") else None,
    }


def get_phase_overview_data():
    fields = [
        "voltage_L1_N",
        "voltage_L2_N",
        "voltage_L3_N",
        "current_L1",
        "current_L2",
        "current_L3",
        "pf_L1",
        "pf_L2",
        "pf_L3",
    ]

    data = query_latest_for_fields(fields, range_window="-24h")

    return {
        "status": "ok",
        "timestamp": iso_now(),
        "L1": {
            "voltage_v": data["voltage_L1_N"]["value"] if data.get("voltage_L1_N") else None,
            "current_a": data["current_L1"]["value"] if data.get("current_L1") else None,
            "pf": data["pf_L1"]["value"] if data.get("pf_L1") else None,
        },
        "L2": {
            "voltage_v": data["voltage_L2_N"]["value"] if data.get("voltage_L2_N") else None,
            "current_a": data["current_L2"]["value"] if data.get("current_L2") else None,
            "pf": data["pf_L2"]["value"] if data.get("pf_L2") else None,
        },
        "L3": {
            "voltage_v": data["voltage_L3_N"]["value"] if data.get("voltage_L3_N") else None,
            "current_a": data["current_L3"]["value"] if data.get("current_L3") else None,
            "pf": data["pf_L3"]["value"] if data.get("pf_L3") else None,
        },
    }


def get_energy_today_data():
    flux_start = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: today(), stop: now())
  |> filter(fn: (r) => r._field == "import_kWh" or r._field == "export_kWh")
  |> first()
'''
    start_tables = query_api.query(flux_start)
    start_values = {}

    for table in start_tables:
        for record in table.records:
            start_values[record.get_field()] = float(record.get_value())

    latest = query_latest_for_fields(["import_kWh", "export_kWh"], range_window="-30d")

    import_total = latest["import_kWh"]["value"] if latest.get("import_kWh") else None
    export_total = latest["export_kWh"]["value"] if latest.get("export_kWh") else None

    import_start = start_values.get("import_kWh")
    export_start = start_values.get("export_kWh")

    today_import = (
        import_total - import_start
        if (import_total is not None and import_start is not None)
        else None
    )
    today_export = (
        export_total - export_start
        if (export_total is not None and export_start is not None)
        else None
    )

    return {
        "status": "ok",
        "timestamp": iso_now(),
        "import_kwh_today": today_import,
        "export_kwh_today": today_export,
        "net_kwh_today": (
            today_import - today_export
            if (today_import is not None and today_export is not None)
            else None
        ),
    }


