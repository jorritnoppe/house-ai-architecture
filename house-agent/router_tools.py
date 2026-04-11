import requests

BASE_URL = "http://127.0.0.1:8000"


def call_tool(path, params=None):
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "path": path, "params": params}



# ============================================================
# House / power helpers
# ============================================================

def get_power_now():
    return call_tool("/ai/power_now")


def get_energy_today():
    return call_tool("/ai/energy_today")


def get_energy_yesterday():
    return call_tool("/ai/energy_yesterday")


def get_energy_compare_today_yesterday():
    return call_tool("/ai/energy_compare_today_yesterday")


def get_phase_overview():
    return call_tool("/ai/phase_overview")


def get_energy_summary():
    return call_tool("/ai/energy_summary")


def get_house_overview():
    return call_tool("/ai/house_overview")


def get_power_peak_today():
    return call_tool("/ai/power_peak_today")


def get_phase_imbalance_summary():
    return call_tool("/ai/phase_imbalance_summary")


def get_power_quality_summary():
    return call_tool("/ai/power_quality_summary")


def get_anomaly_summary():
    return call_tool("/ai/anomaly_summary")


def get_load_distribution_summary():
    return call_tool("/ai/load_distribution_summary")


def get_import_export_status_now():
    return call_tool("/ai/import_export_status_now")


def get_daily_energy_story():
    return call_tool("/ai/daily_energy_story")


def get_power_last_24h_summary():
    return call_tool("/ai/power_last_24h_summary")


def get_compare_last_24h_vs_previous_24h():
    return call_tool("/ai/compare_last_24h_vs_previous_24h")


def get_reactive_load_summary():
    return call_tool("/ai/reactive_load_summary")


def get_compare_peak_today_yesterday():
    return call_tool("/ai/compare_peak_today_yesterday")


def get_night_baseload_summary():
    return call_tool("/ai/night_baseload_summary")


# ============================================================
# Water / price / SMA / Pdata helpers
# ============================================================

def get_electricity_price_now():
    return call_tool("/ai/electricity_price_now")


def get_salt_tank_level():
    return call_tool("/ai/salt_tank_level")


def get_water_temperatures():
    return call_tool("/ai/water_temperatures")


def get_water_softener_overview():
    return call_tool("/ai/water_softener_overview")


def get_sma_summary():
    return call_tool("/ai/sma_summary")


def get_sma_production_overview():
    return call_tool("/ai/sma_production_overview")


def get_pdata_energy_summary():
    return call_tool("/ai/pdata_energy_summary")


def get_pdata_compare_energy():
    return call_tool("/ai/pdata_compare_energy")


def get_pdata_all_fields():
    return call_tool("/ai/pdata_all_fields")


def get_pdata_full_overview():
    return call_tool("/ai/pdata_full_overview")


def get_pdata_gas_summary():
    return call_tool("/ai/pdata_gas_summary")


# ============================================================
# Loxone helpers
# ============================================================

def get_loxone_structure_summary():
    return call_tool("/ai/loxone_structure_summary")


def get_loxone_rooms():
    data = call_tool("/ai/loxone_structure_summary")
    return {
        "status": data.get("status", "ok"),
        "room_count": data.get("room_count", 0),
        "rooms": data.get("rooms", []),
    }


def get_loxone_categories():
    data = call_tool("/ai/loxone_structure_summary")
    return {
        "status": data.get("status", "ok"),
        "category_count": data.get("category_count", 0),
        "categories": data.get("categories", []),
    }


def get_loxone_room_names():
    data = call_tool("/ai/loxone_structure_summary")
    return data.get("rooms", [])


def get_loxone_category_names():
    data = call_tool("/ai/loxone_structure_summary")
    return data.get("categories", [])


def get_loxone_controls_by_room(room: str):
    return call_tool("/ai/loxone_controls_by_room", params={"room": room})


def get_loxone_controls_by_category(category: str):
    return call_tool("/ai/loxone_controls_by_category", params={"category": category})


def get_loxone_control_names_by_room(room: str):
    data = call_tool("/ai/loxone_controls_by_room", params={"room": room})
    items = data.get("items", [])
    return {
        "status": data.get("status", "ok"),
        "room_name": data.get("room_name", room),
        "count": data.get("count", 0),
        "control_names": [item.get("name") for item in items if item.get("name")],
    }


def get_loxone_control_names_by_category(category: str):
    data = call_tool("/ai/loxone_controls_by_category", params={"category": category})
    items = data.get("items", [])
    return {
        "status": data.get("status", "ok"),
        "category_name": data.get("category_name", category),
        "count": data.get("count", 0),
        "control_names": [item.get("name") for item in items if item.get("name")],
    }


def get_loxone_control_types_by_room(room: str):
    data = call_tool("/ai/loxone_controls_by_room", params={"room": room})
    items = data.get("items", [])
    return {
        "status": data.get("status", "ok"),
        "room_name": data.get("room_name", room),
        "count": data.get("count", 0),
        "types": sorted(list({item.get("type") for item in items if item.get("type")})),
    }


def get_loxone_control_types_by_category(category: str):
    data = call_tool("/ai/loxone_controls_by_category", params={"category": category})
    items = data.get("items", [])
    return {
        "status": data.get("status", "ok"),
        "category_name": data.get("category_name", category),
        "count": data.get("count", 0),
        "types": sorted(list({item.get("type") for item in items if item.get("type")})),
    }


def get_loxone_favorites_by_room(room: str):
    data = call_tool("/ai/loxone_controls_by_room", params={"room": room})
    items = data.get("items", [])
    favorites = [item for item in items if item.get("is_favorite")]

    return {
        "status": data.get("status", "ok"),
        "room_name": data.get("room_name", room),
        "count": len(favorites),
        "items": favorites,
    }


def get_loxone_secured_controls_by_room(room: str):
    data = call_tool("/ai/loxone_controls_by_room", params={"room": room})
    items = data.get("items", [])
    secured = [item for item in items if item.get("is_secured")]

    return {
        "status": data.get("status", "ok"),
        "room_name": data.get("room_name", room),
        "count": len(secured),
        "items": secured,
    }


def get_loxone_favorites_by_category(category: str):
    data = call_tool("/ai/loxone_controls_by_category", params={"category": category})
    items = data.get("items", [])
    favorites = [item for item in items if item.get("is_favorite")]

    return {
        "status": data.get("status", "ok"),
        "category_name": data.get("category_name", category),
        "count": len(favorites),
        "items": favorites,
    }


def get_loxone_secured_controls_by_category(category: str):
    data = call_tool("/ai/loxone_controls_by_category", params={"category": category})
    items = data.get("items", [])
    secured = [item for item in items if item.get("is_secured")]

    return {
        "status": data.get("status", "ok"),
        "category_name": data.get("category_name", category),
        "count": len(secured),
        "items": secured,
    }


def get_loxone_subcontrols_by_room(room: str):
    data = call_tool("/ai/loxone_controls_by_room", params={"room": room})
    items = data.get("items", [])

    result = []
    for item in items:
        subs = item.get("subcontrols", [])
        if subs:
            result.append(
                {
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "uuid": item.get("uuid"),
                    "subcontrols": subs,
                }
            )

    return {
        "status": data.get("status", "ok"),
        "room_name": data.get("room_name", room),
        "count": len(result),
        "items": result,
    }


def get_loxone_subcontrols_by_category(category: str):
    data = call_tool("/ai/loxone_controls_by_category", params={"category": category})
    items = data.get("items", [])

    result = []
    for item in items:
        subs = item.get("subcontrols", [])
        if subs:
            result.append(
                {
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "uuid": item.get("uuid"),
                    "subcontrols": subs,
                }
            )

    return {
        "status": data.get("status", "ok"),
        "category_name": data.get("category_name", category),
        "count": len(result),
        "items": result,
    }


def get_loxone_lighting_controls_by_room(room: str):
    data = call_tool("/ai/loxone_controls_by_room", params={"room": room})
    items = data.get("items", [])

    lighting_types = {
        "LightControllerV2",
        "Dimmer",
        "Switch",
        "ColorPickerV2",
        "LightsceneRGB",
        "CentralLightController",
    }

    result = [
        item for item in items
        if item.get("cat_name") == "Beleuchtung" or item.get("type") in lighting_types
    ]

    return {
        "status": data.get("status", "ok"),
        "room_name": data.get("room_name", room),
        "count": len(result),
        "items": result,
    }


def get_loxone_alarm_controls():
    return call_tool("/ai/loxone_controls_by_category", params={"category": "Alarm"})


def get_loxone_temperature_controls_by_room(room: str):
    data = call_tool("/ai/loxone_controls_by_room", params={"room": room})
    items = data.get("items", [])

    result = [
        item for item in items
        if item.get("sensor_type") == "temperature"
        or item.get("name", "").lower().endswith("_climate_controller")
        or item.get("type") in {"InfoOnlyAnalog", "IRoomControllerV2", "ClimateControllerUS"}
    ]

    return {
        "status": data.get("status", "ok"),
        "room_name": data.get("room_name", room),
        "count": len(result),
        "items": result,
    }



def get_loxone_presence_controls_by_room(room: str):
    data = call_tool("/ai/loxone_controls_by_room", params={"room": room})
    items = data.get("items", [])

    result = [
        item for item in items
        if item.get("sensor_type") in {"presence", "motion"}
        or item.get("type") in {"Presence", "PresenceDetector", "Pushbutton"}
    ]

    return {
        "status": data.get("status", "ok"),
        "room_name": data.get("room_name", room),
        "count": len(result),
        "items": result,
    }





def get_loxone_audio_controls_by_room(room: str):
    data = call_tool("/ai/loxone_controls_by_room", params={"room": room})
    items = data.get("items", [])

    result = [
        item for item in items
        if item.get("domain") == "audio"
    ]

    return {
        "status": data.get("status", "ok"),
        "room_name": data.get("room_name", room),
        "count": len(result),
        "items": result,
    }





def get_loxone_controls_search(term: str):
    summary = call_tool("/ai/loxone_structure_summary")
    rooms = summary.get("rooms", [])

    matches = []
    needle = term.lower()

    for room in rooms:
        try:
            data = call_tool("/ai/loxone_controls_by_room", params={"room": room})
            for item in data.get("items", []):
                haystack = " ".join(
                    [
                        str(item.get("name", "")),
                        str(item.get("type", "")),
                        str(item.get("room_name", "")),
                        str(item.get("cat_name", "")),
                    ]
                ).lower()

                if needle in haystack:
                    matches.append(item)
        except Exception:
            pass

    return {
        "status": "ok",
        "search_term": term,
        "count": len(matches),
        "items": matches,
    }



def get_loxone_room_temperature(room: str):
    return call_tool(f"/ai/loxone_room_temperature?room={room}")
