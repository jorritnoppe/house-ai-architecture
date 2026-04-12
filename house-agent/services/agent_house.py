import requests

from config import (
    PRICE_INFLUX_BUCKET,
    PRICE_INFLUX_MEASUREMENT,
    PRICE_INFLUX_FIELD,
)
from services.price_service import (
    query_latest_price,
    get_electricity_cost_today,
    get_electricity_cost_last_24h,
    get_cheapest_hours_today,
)
from services.water_service import (
    get_salt_tank_level,
    get_water_temperature_summary,
)
from services.compare_service import parse_compare_periods_question
from services.pdata_service import (
    get_pdata_energy_summary_data,
    get_pdata_compare_energy_data,
    get_pdata_all_fields_data,
    get_pdata_full_overview_data,
    get_pdata_gas_summary_data,
)
from services.sma_service import (
    get_sma_summary_data,
    get_sma_production_overview_data,
)
from services.energy_service import energy_service


def _loxone_make_response(intent_name, tool_key, tool_data, answer):
    return {
        "status": "ok",
        "mode": "direct_tool",
        "intents": [intent_name],
        "used_tools": [tool_key],
        "tool_data": {tool_key: tool_data},
        "answer": answer,
    }


def _join_top(items, limit=10):
    items = [str(x) for x in items if x is not None]
    if not items:
        return "none"
    if len(items) <= limit:
        return ", ".join(items)
    shown = ", ".join(items[:limit])
    return f"{shown}, and {len(items) - limit} more"


def _fmt_energy(v, unit=""):
    if v is None:
        return "unknown"
    try:
        return f"{float(v):.3f}{unit}"
    except Exception:
        return str(v)


def build_loxone_direct_response(intents, tool_data):
    if "loxone_lighting_controls_by_room" in intents and "loxone_lighting_controls_by_room" in tool_data:
        data = tool_data["loxone_lighting_controls_by_room"]
        room_name = data.get("room_name", "unknown room")
        items = data.get("items", [])
        count = data.get("count", len(items))
        names = [item.get("name") for item in items if item.get("name")]

        return _loxone_make_response(
            "loxone_lighting_controls_by_room",
            "loxone_lighting_controls_by_room",
            data,
            f"Loxone lighting controls in {room_name}: {count}. Names: {_join_top(names, limit=15)}.",
        )

    if "loxone_temperature_controls_by_room" in intents and "loxone_temperature_controls_by_room" in tool_data:
        data = tool_data["loxone_temperature_controls_by_room"]
        room_name = data.get("room_name", "unknown room")
        items = data.get("items", [])
        count = data.get("count", len(items))
        names = [item.get("name") for item in items if item.get("name")]

        return _loxone_make_response(
            "loxone_temperature_controls_by_room",
            "loxone_temperature_controls_by_room",
            data,
            f"Loxone temperature-related controls in {room_name}: {count}. Names: {_join_top(names, limit=15)}.",
        )

    if "loxone_audio_controls_by_room" in intents and "loxone_audio_controls_by_room" in tool_data:
        data = tool_data["loxone_audio_controls_by_room"]
        room_name = data.get("room_name", "unknown room")
        items = data.get("items", [])
        count = data.get("count", len(items))
        names = [item.get("name") for item in items if item.get("name")]

        return _loxone_make_response(
            "loxone_audio_controls_by_room",
            "loxone_audio_controls_by_room",
            data,
            f"Loxone audio-related controls in {room_name}: {count}. Names: {_join_top(names, limit=15)}.",
        )

    if "loxone_presence_controls_by_room" in intents and "loxone_presence_controls_by_room" in tool_data:
        data = tool_data["loxone_presence_controls_by_room"]
        room_name = data.get("room_name", "unknown room")
        items = data.get("items", [])
        count = data.get("count", len(items))
        names = [item.get("name") for item in items if item.get("name")]

        return _loxone_make_response(
            "loxone_presence_controls_by_room",
            "loxone_presence_controls_by_room",
            data,
            f"Loxone presence-related controls in {room_name}: {count}. Names: {_join_top(names, limit=15)}.",
        )

    if "loxone_alarm_controls" in intents and "loxone_alarm_controls" in tool_data:
        data = tool_data["loxone_alarm_controls"]
        items = data.get("items", [])
        count = data.get("count", len(items))
        names = [item.get("name") for item in items if item.get("name")]
        room_names = sorted(set(item.get("room_name") for item in items if item.get("room_name")))

        answer = f"Loxone alarm controls: {count}. Names: {_join_top(names, limit=15)}."
        if room_names:
            answer += f" Found in rooms: {_join_top(room_names, limit=10)}."

        return _loxone_make_response(
            "loxone_alarm_controls",
            "loxone_alarm_controls",
            data,
            answer,
        )

    if "loxone_rooms" in intents and "loxone_rooms" in tool_data:
        data = tool_data["loxone_rooms"]
        rooms = data.get("rooms", [])
        count = data.get("room_count", len(rooms))

        return _loxone_make_response(
            "loxone_rooms",
            "loxone_rooms",
            data,
            f"Loxone has {count} rooms configured: {_join_top(rooms, limit=25)}.",
        )

    if "loxone_categories" in intents and "loxone_categories" in tool_data:
        data = tool_data["loxone_categories"]
        categories = data.get("categories", [])
        count = data.get("category_count", len(categories))

        return _loxone_make_response(
            "loxone_categories",
            "loxone_categories",
            data,
            f"Loxone has {count} categories configured: {_join_top(categories, limit=25)}.",
        )

    if "loxone_structure_summary" in intents and "loxone_structure_summary" in tool_data:
        data = tool_data["loxone_structure_summary"]

        room_count = data.get("room_count")
        category_count = data.get("category_count")
        control_count = data.get("control_count")

        return _loxone_make_response(
            "loxone_structure_summary",
            "loxone_structure_summary",
            data,
            f"Loxone structure summary: {room_count} rooms, {category_count} categories, and {control_count} controls.",
        )

    if "loxone_controls_by_room" in intents and "loxone_controls_by_room" in tool_data:
        data = tool_data["loxone_controls_by_room"]
        room_name = data.get("room_name", "unknown room")
        items = data.get("items", [])
        count = data.get("count", len(items))

        names = [item.get("name") for item in items if item.get("name")]
        types = sorted(set(item.get("type") for item in items if item.get("type")))

        answer = (
            f"Loxone room {room_name} has {count} controls. "
            f"Main control names: {_join_top(names, limit=12)}."
        )
        if types:
            answer += f" Control types include: {_join_top(types, limit=10)}."

        return _loxone_make_response(
            "loxone_controls_by_room",
            "loxone_controls_by_room",
            data,
            answer,
        )

    if "loxone_control_names_by_room" in intents and "loxone_control_names_by_room" in tool_data:
        data = tool_data["loxone_control_names_by_room"]
        room_name = data.get("room_name", "unknown room")
        names = data.get("control_names", [])
        count = data.get("count", len(names))

        return _loxone_make_response(
            "loxone_control_names_by_room",
            "loxone_control_names_by_room",
            data,
            f"Loxone control names in {room_name} ({count}): {_join_top(names, limit=20)}.",
        )

    if "loxone_control_types_by_room" in intents and "loxone_control_types_by_room" in tool_data:
        data = tool_data["loxone_control_types_by_room"]
        room_name = data.get("room_name", "unknown room")
        types = data.get("control_types", [])
        count = data.get("count", len(types))

        return _loxone_make_response(
            "loxone_control_types_by_room",
            "loxone_control_types_by_room",
            data,
            f"Loxone control types in {room_name} ({count}): {_join_top(types, limit=20)}.",
        )

    if "loxone_favorites_by_room" in intents and "loxone_favorites_by_room" in tool_data:
        data = tool_data["loxone_favorites_by_room"]
        room_name = data.get("room_name", "unknown room")
        items = data.get("items", [])
        count = data.get("count", len(items))
        names = [item.get("name") for item in items if item.get("name")]

        return _loxone_make_response(
            "loxone_favorites_by_room",
            "loxone_favorites_by_room",
            data,
            f"Loxone favorites in {room_name}: {count}. Names: {_join_top(names, limit=15)}.",
        )

    if "loxone_secured_controls_by_room" in intents and "loxone_secured_controls_by_room" in tool_data:
        data = tool_data["loxone_secured_controls_by_room"]
        room_name = data.get("room_name", "unknown room")
        items = data.get("items", [])
        count = data.get("count", len(items))
        names = [item.get("name") for item in items if item.get("name")]

        return _loxone_make_response(
            "loxone_secured_controls_by_room",
            "loxone_secured_controls_by_room",
            data,
            f"Loxone secured controls in {room_name}: {count}. Names: {_join_top(names, limit=15)}.",
        )

    if "loxone_subcontrols_by_room" in intents and "loxone_subcontrols_by_room" in tool_data:
        data = tool_data["loxone_subcontrols_by_room"]
        room_name = data.get("room_name", "unknown room")
        items = data.get("items", [])
        count = data.get("count", len(items))

        names = []
        for item in items:
            control_name = item.get("name")
            subcontrols = item.get("subcontrols", [])
            if control_name and subcontrols:
                names.append(f"{control_name} ({len(subcontrols)} subcontrols)")

        return _loxone_make_response(
            "loxone_subcontrols_by_room",
            "loxone_subcontrols_by_room",
            data,
            f"Loxone controls with subcontrols in {room_name}: {count}. {_join_top(names, limit=12)}.",
        )

    if "loxone_controls_by_category" in intents and "loxone_controls_by_category" in tool_data:
        data = tool_data["loxone_controls_by_category"]
        category_name = data.get("category_name", "unknown category")
        items = data.get("items", [])
        count = data.get("count", len(items))

        names = [item.get("name") for item in items if item.get("name")]
        room_names = sorted(set(item.get("room_name") for item in items if item.get("room_name")))

        answer = (
            f"Loxone category {category_name} has {count} controls. "
            f"Main names: {_join_top(names, limit=12)}."
        )
        if room_names:
            answer += f" Present in rooms: {_join_top(room_names, limit=10)}."

        return _loxone_make_response(
            "loxone_controls_by_category",
            "loxone_controls_by_category",
            data,
            answer,
        )

    if "loxone_control_names_by_category" in intents and "loxone_control_names_by_category" in tool_data:
        data = tool_data["loxone_control_names_by_category"]
        category_name = data.get("category_name", "unknown category")
        names = data.get("control_names", [])
        count = data.get("count", len(names))

        return _loxone_make_response(
            "loxone_control_names_by_category",
            "loxone_control_names_by_category",
            data,
            f"Loxone control names in category {category_name} ({count}): {_join_top(names, limit=20)}.",
        )

    if "loxone_control_types_by_category" in intents and "loxone_control_types_by_category" in tool_data:
        data = tool_data["loxone_control_types_by_category"]
        category_name = data.get("category_name", "unknown category")
        types = data.get("control_types", [])
        count = data.get("count", len(types))

        return _loxone_make_response(
            "loxone_control_types_by_category",
            "loxone_control_types_by_category",
            data,
            f"Loxone control types in category {category_name} ({count}): {_join_top(types, limit=20)}.",
        )

    if "loxone_favorites_by_category" in intents and "loxone_favorites_by_category" in tool_data:
        data = tool_data["loxone_favorites_by_category"]
        category_name = data.get("category_name", "unknown category")
        items = data.get("items", [])
        count = data.get("count", len(items))
        names = [item.get("name") for item in items if item.get("name")]

        return _loxone_make_response(
            "loxone_favorites_by_category",
            "loxone_favorites_by_category",
            data,
            f"Loxone favorites in category {category_name}: {count}. Names: {_join_top(names, limit=15)}.",
        )

    if "loxone_secured_controls_by_category" in intents and "loxone_secured_controls_by_category" in tool_data:
        data = tool_data["loxone_secured_controls_by_category"]
        category_name = data.get("category_name", "unknown category")
        items = data.get("items", [])
        count = data.get("count", len(items))
        names = [item.get("name") for item in items if item.get("name")]

        return _loxone_make_response(
            "loxone_secured_controls_by_category",
            "loxone_secured_controls_by_category",
            data,
            f"Loxone secured controls in category {category_name}: {count}. Names: {_join_top(names, limit=15)}.",
        )

    if "loxone_subcontrols_by_category" in intents and "loxone_subcontrols_by_category" in tool_data:
        data = tool_data["loxone_subcontrols_by_category"]
        category_name = data.get("category_name", "unknown category")
        items = data.get("items", [])
        count = data.get("count", len(items))

        names = []
        for item in items:
            control_name = item.get("name")
            subcontrols = item.get("subcontrols", [])
            if control_name and subcontrols:
                names.append(f"{control_name} ({len(subcontrols)} subcontrols)")

        return _loxone_make_response(
            "loxone_subcontrols_by_category",
            "loxone_subcontrols_by_category",
            data,
            f"Loxone controls with subcontrols in category {category_name}: {count}. {_join_top(names, limit=12)}.",
        )

    if "loxone_controls_search" in intents and "loxone_controls_search" in tool_data:
        data = tool_data["loxone_controls_search"]
        term = data.get("search_term", "unknown")
        items = data.get("items", [])
        count = data.get("count", len(items))
        names = [item.get("name") for item in items if item.get("name")]

        return _loxone_make_response(
            "loxone_controls_search",
            "loxone_controls_search",
            data,
            f"Loxone search for '{term}' returned {count} controls: {_join_top(names, limit=15)}.",
        )

    return None


def build_house_direct_response(question, intents, tool_data):
    loxone_response = build_loxone_direct_response(intents, tool_data)
    if loxone_response:
        return loxone_response

    if "compare_periods_from_question" in intents:
        parsed = parse_compare_periods_question(question)

        if parsed:
            compare_result = requests.post(
                "http://127.0.0.1:8000/ai/compare_periods",
                json=parsed,
                timeout=20,
            ).json()

            p1 = compare_result["period_1"]
            p2 = compare_result["period_2"]

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["compare_periods_from_question"],
                "tool_data": {
                    "compare_periods_from_question": compare_result,
                },
                "answer": (
                    f"For field {compare_result['field']}, period 1 average was {p1['avg']:.2f} "
                    f"and period 2 average was {p2['avg']:.2f}. "
                    f"The comparison result is {compare_result['status']}, with an average delta of "
                    f"{compare_result['avg_delta']:.2f}."
                ),
            }

    if "compare_last_24h_vs_previous_24h" in intents and "compare_last_24h_vs_previous_24h" in tool_data:
        s = tool_data["compare_last_24h_vs_previous_24h"]
        p1 = s["period_1"]
        p2 = s["period_2"]

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["compare_last_24h_vs_previous_24h"],
            "tool_data": tool_data,
            "answer": (
                f"Over the last 24 hours, average power was {p1['avg']:.2f} watts. "
                f"In the previous 24-hour window, average power was {p2['avg']:.2f} watts. "
                f"The last 24 hours were {s['status']}, with an average delta of {s['avg_delta']:.2f} watts."
            ),
        }

    if "electricity_price_now" in intents:
        try:
            latest = query_latest_price(range_window="-7d")
            if latest:
                tool_data["electricity_price_now"] = {
                    "price_eur_per_kwh": latest["value"],
                    "price_time": latest["time"],
                    "source": {
                        "bucket": PRICE_INFLUX_BUCKET,
                        "measurement": PRICE_INFLUX_MEASUREMENT,
                        "field": PRICE_INFLUX_FIELD,
                    },
                }

                return {
                    "status": "ok",
                    "mode": "direct_tool",
                    "intents": intents,
                    "used_tools": ["electricity_price_now"],
                    "tool_data": tool_data,
                    "answer": f"The current electricity price is {latest['value']:.3f} EUR/kWh.",
                }
        except Exception as e:
            tool_data["electricity_price_now"] = {"error": str(e)}

    if "electricity_cost_today" in intents:
        try:
            data = get_electricity_cost_today()
            tool_data["electricity_cost_today"] = data

            if data["status"] == "ok":
                return {
                    "status": "ok",
                    "mode": "direct_tool",
                    "intents": intents,
                    "used_tools": ["electricity_cost_today"],
                    "tool_data": tool_data,
                    "answer": (
                        f"Estimated electricity import cost today is "
                        f"{data['total_cost_eur']:.2f} EUR for "
                        f"{data['total_import_kwh']:.3f} kWh. "
                        f"The average paid price is "
                        f"{data['average_price_eur_per_kwh']:.3f} EUR/kWh."
                    ),
                }
        except Exception as e:
            tool_data["electricity_cost_today"] = {"error": str(e)}

    if "electricity_cost_last_24h" in intents:
        try:
            data = get_electricity_cost_last_24h()
            tool_data["electricity_cost_last_24h"] = data

            if data["status"] == "ok":
                return {
                    "status": "ok",
                    "mode": "direct_tool",
                    "intents": intents,
                    "used_tools": ["electricity_cost_last_24h"],
                    "tool_data": tool_data,
                    "answer": (
                        f"Estimated electricity import cost over the last 24 hours is "
                        f"{data['total_cost_eur']:.2f} EUR for "
                        f"{data['total_import_kwh']:.3f} kWh. "
                        f"The average paid price is "
                        f"{data['average_price_eur_per_kwh']:.3f} EUR/kWh."
                    ),
                }
        except Exception as e:
            tool_data["electricity_cost_last_24h"] = {"error": str(e)}

    if "cheapest_hours_today" in intents:
        try:
            data = get_cheapest_hours_today(limit=3)
            tool_data["cheapest_hours_today"] = data

            if data["status"] == "ok" and data["items"]:
                parts = [
                    f"{item['time']} at {item['price_eur_per_kwh']:.3f} EUR/kWh"
                    for item in data["items"]
                ]

                return {
                    "status": "ok",
                    "mode": "direct_tool",
                    "intents": intents,
                    "used_tools": ["cheapest_hours_today"],
                    "tool_data": tool_data,
                    "answer": "The cheapest electricity price windows today are: " + "; ".join(parts) + ".",
                }
        except Exception as e:
            tool_data["cheapest_hours_today"] = {"error": str(e)}

    if "water_inlet_temperature" in intents:
        try:
            data = get_water_temperature_summary()
            tool_data["water_inlet_temperature"] = data

            if data["status"] == "ok" and data["inlet_water_temp_c"] is not None:
                return {
                    "status": "ok",
                    "mode": "direct_tool",
                    "intents": intents,
                    "used_tools": ["water_inlet_temperature"],
                    "tool_data": tool_data,
                    "answer": (
                        f"The main water inlet temperature is "
                        f"{data['inlet_water_temp_c']:.1f} C. "
                        f"Status is {data['inlet_water_temp_status']}."
                    ),
                }

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["water_inlet_temperature"],
                "tool_data": tool_data,
                "answer": "I could not find the main water inlet temperature.",
            }
        except Exception as e:
            tool_data["water_inlet_temperature"] = {"error": str(e)}
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["water_inlet_temperature"],
                "tool_data": tool_data,
                "answer": f"I found the inlet temperature intent, but reading the data failed: {str(e)}",
            }

    if "salt_tank_water_temperature" in intents:
        try:
            data = get_water_temperature_summary()
            tool_data["salt_tank_water_temperature"] = data

            if data["status"] == "ok" and data["salt_tank_water_temp_c"] is not None:
                return {
                    "status": "ok",
                    "mode": "direct_tool",
                    "intents": intents,
                    "used_tools": ["salt_tank_water_temperature"],
                    "tool_data": tool_data,
                    "answer": (
                        f"The salt tank water temperature is "
                        f"{data['salt_tank_water_temp_c']:.1f} C. "
                        f"Status is {data['salt_tank_water_temp_status']}."
                    ),
                }

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["salt_tank_water_temperature"],
                "tool_data": tool_data,
                "answer": "I could not find the salt tank water temperature.",
            }
        except Exception as e:
            tool_data["salt_tank_water_temperature"] = {"error": str(e)}
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["salt_tank_water_temperature"],
                "tool_data": tool_data,
                "answer": f"I found the salt tank temperature intent, but reading the data failed: {str(e)}",
            }

    if "pdata_compare_energy" in intents:
        try:
            data = get_pdata_compare_energy_data()

            def fmt(v, unit=""):
                if v is None:
                    return "unknown"
                return f"{v:.3f}{unit}"

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["pdata_compare_energy"],
                "used_tools": ["pdata_compare_energy"],
                "tool_data": {"pdata_compare_energy": data},
                "answer": (
                    f"Meter comparison: local meter import total is "
                    f"{fmt(data['local_meter'].get('import_kwh_total'), ' kWh')} and provider meter import total is "
                    f"{fmt(data['provider_meter'].get('total_import_kwh'), ' kWh')}. "
                    f"Local export total is {fmt(data['local_meter'].get('export_kwh_total'), ' kWh')} and "
                    f"provider export total is {fmt(data['provider_meter'].get('total_export_kwh'), ' kWh')}. "
                    f"Import delta is {fmt(data['deltas'].get('import_kwh'), ' kWh')} and "
                    f"export delta is {fmt(data['deltas'].get('export_kwh'), ' kWh')}."
                ),
            }
        except Exception as e:
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["pdata_compare_energy"],
                "used_tools": ["pdata_compare_energy"],
                "tool_data": {"pdata_compare_energy": {"error": str(e)}},
                "answer": f"I found the Pdata comparison intent, but reading the data failed: {str(e)}",
            }

    if "pdata_all_fields" in intents:
        try:
            data = get_pdata_all_fields_data()
            count = data.get("count", 0)

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["pdata_all_fields"],
                "used_tools": ["pdata_all_fields"],
                "tool_data": {"pdata_all_fields": data},
                "answer": f"I found {count} available Pdata OBIS fields and decoded them for use by the AI.",
            }
        except Exception as e:
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["pdata_all_fields"],
                "used_tools": ["pdata_all_fields"],
                "tool_data": {"pdata_all_fields": {"error": str(e)}},
                "answer": f"I found the all-OBIS-fields intent, but reading the data failed: {str(e)}",
            }

    if "pdata_full_overview" in intents:
        try:
            data = get_pdata_full_overview_data()
            s = data["summary"]

            def fmt(v, unit=""):
                if v is None:
                    return "unknown"
                return f"{v:.3f}{unit}"

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["pdata_full_overview"],
                "used_tools": ["pdata_full_overview"],
                "tool_data": {"pdata_full_overview": data},
                "answer": (
                    f"Pdata full overview: total import is {fmt(s.get('total_import_kwh'), ' kWh')}, "
                    f"total export is {fmt(s.get('total_export_kwh'), ' kWh')}, "
                    f"current import power is {fmt(s.get('current_import_kw'), ' kW')}, "
                    f"current export power is {fmt(s.get('current_export_kw'), ' kW')}. "
                    f"Phase voltages are L1 {fmt(s.get('l1_voltage_v'), ' V')}, "
                    f"L2 {fmt(s.get('l2_voltage_v'), ' V')}, "
                    f"L3 {fmt(s.get('l3_voltage_v'), ' V')}. "
                    f"Gas status is {data['gas'].get('gas_status_text', 'unknown')}."
                ),
            }
        except Exception as e:
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["pdata_full_overview"],
                "used_tools": ["pdata_full_overview"],
                "tool_data": {"pdata_full_overview": {"error": str(e)}},
                "answer": f"I found the full Pdata overview intent, but reading the data failed: {str(e)}",
            }

    if "pdata_gas_summary" in intents:
        try:
            data = get_pdata_gas_summary_data()

            gas_total = data.get("gas_total_m3")
            gas_total_txt = "unknown"
            if gas_total is not None:
                gas_total_txt = f"{gas_total:.3f} m3"

            meter_id_txt = data.get("gas_meter_id") or "unknown"
            gas_status_txt = data.get("gas_status_text") or "unknown"

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["pdata_gas_summary"],
                "used_tools": ["pdata_gas_summary"],
                "tool_data": {"pdata_gas_summary": data},
                "answer": (
                    f"Gas summary from Pdata: gas meter id is {meter_id_txt}, "
                    f"gas status is {gas_status_txt}, and detected gas total is {gas_total_txt}."
                ),
            }
        except Exception as e:
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["pdata_gas_summary"],
                "used_tools": ["pdata_gas_summary"],
                "tool_data": {"pdata_gas_summary": {"error": str(e)}},
                "answer": f"I found the Pdata gas intent, but reading the data failed: {str(e)}",
            }

    if "pdata_energy_summary" in intents:
        try:
            data = get_pdata_energy_summary_data()

            def fmt(v, unit=""):
                if v is None:
                    return "unknown"
                return f"{v:.3f}{unit}"

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["pdata_energy_summary"],
                "used_tools": ["pdata_energy_summary"],
                "tool_data": {"pdata_energy_summary": data},
                "answer": (
                    f"Provider smart meter summary: import tariff 1 is {fmt(data.get('import_t1_kwh'), ' kWh')}, "
                    f"import tariff 2 is {fmt(data.get('import_t2_kwh'), ' kWh')}, "
                    f"export tariff 1 is {fmt(data.get('export_t1_kwh'), ' kWh')}, "
                    f"export tariff 2 is {fmt(data.get('export_t2_kwh'), ' kWh')}. "
                    f"Total import is {fmt(data.get('total_import_kwh'), ' kWh')} and "
                    f"total export is {fmt(data.get('total_export_kwh'), ' kWh')}."
                ),
            }
        except Exception as e:
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["pdata_energy_summary"],
                "used_tools": ["pdata_energy_summary"],
                "tool_data": {"pdata_energy_summary": {"error": str(e)}},
                "answer": f"I found the Pdata summary intent, but reading the data failed: {str(e)}",
            }

    if "energy_compare_today_yesterday" in intents and "energy_compare_today_yesterday" in tool_data:
        cmp_data = tool_data["energy_compare_today_yesterday"]
        today = cmp_data["today"]
        yesterday = cmp_data["yesterday"]

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["energy_compare_today_yesterday"],
            "tool_data": tool_data,
            "answer": (
                f"Today the house imported {today['import_kwh']:.3f} kWh and exported {today['export_kwh']:.3f} kWh "
                f"(net {today['net_kwh']:.3f} kWh). "
                f"Yesterday it imported {yesterday['import_kwh']:.3f} kWh and exported {yesterday['export_kwh']:.3f} kWh "
                f"(net {yesterday['net_kwh']:.3f} kWh)."
            ),
        }

    if "daily_energy_story" in intents and "daily_energy_story" in tool_data:
        try:
            flow = energy_service.get_power_flow_summary()
            today = tool_data["daily_energy_story"]["energy_today"]
            peak = tool_data["daily_energy_story"]["power_peak_today"]

            answer = (
                f"Today the house imported {today['import_kwh_today']:.3f} kWh and exported "
                f"{today['export_kwh_today']:.3f} kWh, for a net of {today['net_kwh_today']:.3f} kWh. "
                f"The peak power today was {peak['peak_power_watts']:.2f} watts at {peak['peak_time']}. "
            )

            grid_in = flow.get("grid_import_kw")
            grid_out = flow.get("grid_export_kw")
            load = flow.get("estimated_house_load_kw")
            solar = flow.get("solar_power_kw")

            if grid_out is not None and grid_out > 0:
                answer += (
                    f"Right now the house load is {_fmt_energy(load, ' kW')}, "
                    f"solar production is {_fmt_energy(solar, ' kW')}, and "
                    f"about {_fmt_energy(grid_out, ' kW')} is being exported."
                )
            else:
                answer += (
                    f"Right now the house load is {_fmt_energy(load, ' kW')}, "
                    f"solar production is {_fmt_energy(solar, ' kW')}, and "
                    f"about {_fmt_energy(grid_in, ' kW')} is being imported from the grid."
                )

            tool_data["daily_energy_story_unified_flow"] = flow

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["daily_energy_story"],
                "tool_data": tool_data,
                "answer": answer,
            }
        except Exception as e:
            tool_data["daily_energy_story_unified_flow"] = {"error": str(e)}

    if "house_overview" in intents and "house_overview" in tool_data:
        try:
            overview = tool_data["house_overview"]
            flow = energy_service.get_power_flow_summary()

            freq = overview["energy_summary"].get("frequency_hz")
            pf = overview["energy_summary"].get("power_factor")

            phases = overview["phases"]
            currents = {
                "L1": phases["L1"]["current_a"],
                "L2": phases["L2"]["current_a"],
                "L3": phases["L3"]["current_a"],
            }
            max_phase = max(currents, key=currents.get)
            max_current = currents[max_phase]

            grid_in = flow.get("grid_import_kw")
            grid_out = flow.get("grid_export_kw")
            load = flow.get("estimated_house_load_kw")
            solar = flow.get("solar_power_kw")
            excess = flow.get("excess_energy_available_kw")
            excess_state = flow.get("excess_energy_state")

            if grid_out is not None and grid_out > 0:
                grid_text = f"The house is exporting {_fmt_energy(grid_out, ' kW')} to the grid."
            elif grid_in is not None and grid_in > 0:
                grid_text = f"The house is importing {_fmt_energy(grid_in, ' kW')} from the grid."
            else:
                grid_text = "The house is currently near grid balance."

            excess_text = ""
            if excess is not None and excess > 0:
                excess_text = (
                    f" Automation-safe excess energy available is {_fmt_energy(excess, ' kW')} "
                    f"with state {excess_state}."
                )

            tool_data["house_overview_unified_flow"] = flow

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["house_overview"],
                "tool_data": tool_data,
                "answer": (
                    f"The estimated house load is {_fmt_energy(load, ' kW')}. "
                    f"Solar production is {_fmt_energy(solar, ' kW')}. "
                    f"{grid_text}"
                    f"{excess_text} "
                    f"Grid frequency is {freq:.3f} Hz and total power factor is {pf:.3f}. "
                    f"The most loaded phase right now is {max_phase} at {max_current:.3f} A."
                ),
            }
        except Exception as e:
            tool_data["house_overview_unified_flow"] = {"error": str(e)}

    if "power_peak_today" in intents and "power_peak_today" in tool_data:
        peak = tool_data["power_peak_today"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["power_peak_today"],
            "tool_data": tool_data,
            "answer": (
                f"The highest measured house power today was "
                f"{peak['peak_power_watts']:.2f} watts at {peak['peak_time']}."
            ),
        }

    if "power_last_24h_summary" in intents and "power_last_24h_summary" in tool_data:
        s = tool_data["power_last_24h_summary"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["power_last_24h_summary"],
            "tool_data": tool_data,
            "answer": (
                f"Over the last 24 hours, minimum power was {s['min_power_watts']:.2f} watts, "
                f"maximum power was {s['max_power_watts']:.2f} watts, and average power was "
                f"{s['avg_power_watts']:.2f} watts. The latest measured power is "
                f"{s['latest_power_watts']:.2f} watts, which is {s['relative_status']}."
            ),
        }

    if "night_baseload_summary" in intents and "night_baseload_summary" in tool_data:
        s = tool_data["night_baseload_summary"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["night_baseload_summary"],
            "tool_data": tool_data,
            "answer": (
                f"Night baseload average was {s['avg_power_watts']:.2f} watts, with a minimum of "
                f"{s['min_power_watts']:.2f} watts and a maximum of {s['max_power_watts']:.2f} watts. "
                f"Baseload status is {s['baseload_status']}."
            ),
        }

    if "load_distribution_summary" in intents and "load_distribution_summary" in tool_data:
        d = tool_data["load_distribution_summary"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["load_distribution_summary"],
            "tool_data": tool_data,
            "answer": (
                f"The dominant phase is {d['dominant_phase']} carrying "
                f"{d['dominant_share_percent']:.1f}% of the total measured current. "
                f"Load distribution status is {d['balance_status']}."
            ),
        }

    if "phase_imbalance_summary" in intents and "phase_imbalance_summary" in tool_data:
        s = tool_data["phase_imbalance_summary"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["phase_imbalance_summary"],
            "tool_data": tool_data,
            "answer": (
                f"The most loaded phase is {s['most_loaded_phase']} and the least loaded phase is "
                f"{s['least_loaded_phase']}. Current imbalance is {s['imbalance_amps']:.3f} A."
            ),
        }

    if "reactive_load_summary" in intents and "reactive_load_summary" in tool_data:
        s = tool_data["reactive_load_summary"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["reactive_load_summary"],
            "tool_data": tool_data,
            "answer": (
                f"Reactive power is {s['reactive_power_var']:.3f} var, active power is "
                f"{s['active_power_watts']:.3f} watts, and apparent power is {s['apparent_power_va']:.3f} VA. "
                f"Reactive load status is {s['reactive_load_status']}."
            ),
        }

    if "power_quality_summary" in intents and "power_quality_summary" in tool_data:
        pq = tool_data["power_quality_summary"]

        frequency = pq.get("frequency_hz")
        frequency_status = pq.get("frequency_status", "unknown")
        power_factor = pq.get("power_factor")
        power_factor_status = pq.get("power_factor_status", "unknown")
        reactive_power = pq.get("reactive_power_var")
        reactive_status = pq.get("reactive_power_status", "unknown")

        frequency_txt = f"{frequency:.3f} Hz" if frequency is not None else "unknown"
        pf_txt = f"{power_factor:.3f}" if power_factor is not None else "unknown"
        reactive_txt = f"{reactive_power:.3f} var" if reactive_power is not None else "unknown"

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["power_quality_summary"],
            "tool_data": tool_data,
            "answer": (
                f"Grid frequency is {frequency_txt} ({frequency_status}). "
                f"Power factor is {pf_txt} ({power_factor_status}). "
                f"Reactive power is {reactive_txt} ({reactive_status})."
            ),
        }

    if "anomaly_summary" in intents and "anomaly_summary" in tool_data:
        a = tool_data["anomaly_summary"]

        if a["status"] == "ok":
            answer = "No clear electrical anomalies are detected right now."
        else:
            answer = "Current anomalies detected: " + " ".join(a["anomalies"])

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["anomaly_summary"],
            "tool_data": tool_data,
            "answer": answer,
        }

    if "import_export_status_now" in intents:
        try:
            flow = energy_service.get_power_flow_summary()
            tool_data["import_export_status_now_unified"] = flow

            grid_in = flow.get("grid_import_kw")
            grid_out = flow.get("grid_export_kw")
            solar = flow.get("solar_power_kw")
            load = flow.get("estimated_house_load_kw")
            excess = flow.get("excess_energy_available_kw")
            excess_state = flow.get("excess_energy_state")
            reason = flow.get("excess_energy_reason")

            if excess is not None and excess > 0:
                answer = (
                    f"Yes. There is about {_fmt_energy(excess, ' kW')} of excess electricity available right now. "
                    f"Excess energy state is {excess_state}. "
                    f"Solar production is {_fmt_energy(solar, ' kW')}, "
                    f"house load is {_fmt_energy(load, ' kW')}, "
                    f"and grid export is {_fmt_energy(grid_out, ' kW')}."
                )
            elif grid_out is not None and grid_out > 0:
                answer = (
                    f"The house is exporting {_fmt_energy(grid_out, ' kW')} to the grid, "
                    f"but automation-safe excess energy is currently effectively zero after reserve. "
                    f"Solar production is {_fmt_energy(solar, ' kW')} and house load is "
                    f"{_fmt_energy(load, ' kW')}."
                )
            elif grid_in is not None and grid_in > 0:
                answer = (
                    f"No. The house is importing about {_fmt_energy(grid_in, ' kW')} from the grid right now. "
                    f"Solar production is {_fmt_energy(solar, ' kW')} and house load is "
                    f"{_fmt_energy(load, ' kW')}."
                )
            else:
                answer = (
                    f"There is no meaningful excess electricity available right now. "
                    f"Solar production is {_fmt_energy(solar, ' kW')}, "
                    f"house load is {_fmt_energy(load, ' kW')}, "
                    f"and excess reason is {reason or 'unknown'}."
                )

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["import_export_status_now"],
                "tool_data": tool_data,
                "answer": answer,
            }
        except Exception as e:
            tool_data["import_export_status_now_unified"] = {"error": str(e)}

    if "energy_yesterday" in intents and "energy_yesterday" in tool_data:
        y = tool_data["energy_yesterday"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["energy_yesterday"],
            "tool_data": tool_data,
            "answer": (
                f"Yesterday the house imported {y['import_kwh_yesterday']:.3f} kWh and exported "
                f"{y['export_kwh_yesterday']:.3f} kWh. Net energy yesterday was {y['net_kwh_yesterday']:.3f} kWh."
            ),
        }

    if "energy_today" in intents and "energy_today" in tool_data:
        t = tool_data["energy_today"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["energy_today"],
            "tool_data": tool_data,
            "answer": (
                f"Today the house imported {t['import_kwh_today']:.3f} kWh and exported "
                f"{t['export_kwh_today']:.3f} kWh. Net energy today is {t['net_kwh_today']:.3f} kWh."
            ),
        }

    if "phase_overview" in intents and "phase_overview" in tool_data:
        phases = tool_data["phase_overview"]
        currents = {
            "L1": phases["L1"]["current_a"],
            "L2": phases["L2"]["current_a"],
            "L3": phases["L3"]["current_a"],
        }
        max_phase = max(currents, key=currents.get)
        max_current = currents[max_phase]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["phase_overview"],
            "tool_data": tool_data,
            "answer": f"The most loaded phase right now is {max_phase} at {max_current:.3f} A.",
        }

    if "power_now" in intents and "power_now" in tool_data:
        try:
            flow = energy_service.get_power_flow_summary()
            tool_data["power_now_unified_flow"] = flow

            load = flow.get("estimated_house_load_kw")
            solar = flow.get("solar_power_kw")
            grid_in = flow.get("grid_import_kw")
            grid_out = flow.get("grid_export_kw")
            excess = flow.get("excess_energy_available_kw")
            excess_state = flow.get("excess_energy_state")

            if grid_out is not None and grid_out > 0:
                grid_text = f"The house is exporting {_fmt_energy(grid_out, ' kW')} to the grid."
            elif grid_in is not None and grid_in > 0:
                grid_text = f"The house is importing {_fmt_energy(grid_in, ' kW')} from the grid."
            else:
                grid_text = "The house is currently near grid balance."

            excess_text = ""
            if excess is not None and excess > 0:
                excess_text = (
                    f" There is about {_fmt_energy(excess, ' kW')} of automation-safe excess energy "
                    f"available right now, state {excess_state}."
                )

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["power_now"],
                "tool_data": tool_data,
                "answer": (
                    f"The estimated house load is {_fmt_energy(load, ' kW')}. "
                    f"Solar is producing {_fmt_energy(solar, ' kW')}. "
                    f"{grid_text}"
                    f"{excess_text}"
                ),
            }
        except Exception as e:
            tool_data["power_now_unified_flow"] = {"error": str(e)}
            watts = tool_data["power_now"]["power_watts"]
            kw = watts / 1000.0

            if kw < 0:
                answer = f"The meter currently shows net export of {abs(kw):.2f} kilowatts."
            else:
                answer = f"The meter currently shows net import of {kw:.2f} kilowatts."

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["power_now"],
                "tool_data": tool_data,
                "answer": answer,
            }

    if "salt_tank_level" in intents:
        try:
            data = get_salt_tank_level()
            tool_data["salt_tank_level"] = data

            if data["status"] == "ok":
                return {
                    "status": "ok",
                    "mode": "direct_tool",
                    "intents": intents,
                    "used_tools": ["salt_tank_level"],
                    "tool_data": tool_data,
                    "answer": (
                        f"The water softener salt tank is at {data['salt_level_percent']:.1f}% "
                        f"with a measured distance of {data['distance_cm']:.1f} cm. "
                        f"Status is {data['salt_level_status']}."
                    ),
                }

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["salt_tank_level"],
                "tool_data": tool_data,
                "answer": data.get("message", "I could not find salt tank data."),
            }

        except Exception as e:
            tool_data["salt_tank_level"] = {"error": str(e)}
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["salt_tank_level"],
                "tool_data": tool_data,
                "answer": f"I found the salt tank intent, but reading the data failed: {str(e)}",
            }

    if "water_temperatures" in intents:
        try:
            data = get_water_temperature_summary()
            tool_data["water_temperatures"] = data

            if data["status"] == "ok":
                inlet_txt = (
                    f"{data['inlet_water_temp_c']:.1f} C"
                    if data["inlet_water_temp_c"] is not None
                    else "unknown"
                )
                salt_txt = (
                    f"{data['salt_tank_water_temp_c']:.1f} C"
                    if data["salt_tank_water_temp_c"] is not None
                    else "unknown"
                )

                answer = (
                    f"The main water inlet temperature is {inlet_txt} "
                    f"and the salt tank water temperature is {salt_txt}."
                )

                if data["temp_delta_c"] is not None:
                    answer += f" The salt tank is {data['temp_delta_c']:+.1f} C relative to the inlet."

                return {
                    "status": "ok",
                    "mode": "direct_tool",
                    "intents": intents,
                    "used_tools": ["water_temperatures"],
                    "tool_data": tool_data,
                    "answer": answer,
                }

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["water_temperatures"],
                "tool_data": tool_data,
                "answer": data.get("message", "I could not find water temperature data."),
            }

        except Exception as e:
            tool_data["water_temperatures"] = {"error": str(e)}
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": intents,
                "used_tools": ["water_temperatures"],
                "tool_data": tool_data,
                "answer": f"I found the water temperature intent, but reading the data failed: {str(e)}",
            }

    if "water_softener_overview" in intents:
        try:
            salt = get_salt_tank_level()
            temps = get_water_temperature_summary()

            refill_warning = None
            refill_text = ""

            if salt.get("status") == "ok":
                pct = salt.get("salt_level_percent")
                if pct is not None:
                    if pct <= 10:
                        refill_warning = "urgent_refill"
                        refill_text = " Refill is urgent."
                    elif pct <= 25:
                        refill_warning = "refill_recommended"
                        refill_text = " Refill is recommended soon."
                    else:
                        refill_warning = "ok"

            salt_txt = "unknown"
            salt_status_txt = "unknown"
            if salt.get("status") == "ok":
                salt_txt = f"{salt['salt_level_percent']:.1f}%"
                salt_status_txt = salt["salt_level_status"]

            inlet_txt = "unknown"
            tank_txt = "unknown"
            if temps.get("status") == "ok":
                if temps.get("inlet_water_temp_c") is not None:
                    inlet_txt = f"{temps['inlet_water_temp_c']:.1f} C"
                if temps.get("salt_tank_water_temp_c") is not None:
                    tank_txt = f"{temps['salt_tank_water_temp_c']:.1f} C"

            overview_data = {
                "salt": salt,
                "temperatures": temps,
                "refill_warning": refill_warning,
            }

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["water_softener_overview"],
                "used_tools": ["water_softener_overview"],
                "tool_data": {
                    "water_softener_overview": overview_data,
                },
                "answer": (
                    f"Water softener overview: salt level is {salt_txt} "
                    f"with status {salt_status_txt}. "
                    f"Main inlet water temperature is {inlet_txt} and "
                    f"salt tank water temperature is {tank_txt}."
                    f"{refill_text}"
                ),
            }

        except Exception as e:
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["water_softener_overview"],
                "used_tools": ["water_softener_overview"],
                "tool_data": {
                    "water_softener_overview": {"error": str(e)},
                },
                "answer": f"I found the water softener overview intent, but reading the data failed: {str(e)}",
            }

    if "sma_production_overview" in intents:
        try:
            data = get_sma_production_overview_data()

            ac_power_txt = "unknown"
            if data.get("ac_power_w") is not None:
                ac_power_txt = f"{data['ac_power_w']:.0f} W"

            daily_energy_txt = "unknown"
            if data.get("daily_energy_kwh") is not None:
                daily_energy_txt = f"{data['daily_energy_kwh']:.3f} kWh"

            total_energy_txt = "unknown"
            if data.get("total_energy_kwh") is not None:
                total_energy_txt = f"{data['total_energy_kwh']:.3f} kWh"

            pv_voltage_txt = "unknown"
            if data.get("pv_voltage_v") is not None:
                pv_voltage_txt = f"{data['pv_voltage_v']:.1f} V"

            pv_current_txt = "unknown"
            if data.get("pv_current_a") is not None:
                pv_current_txt = f"{data['pv_current_a']:.1f} A"

            grid_voltage_txt = "unknown"
            if data.get("grid_voltage_v") is not None:
                grid_voltage_txt = f"{data['grid_voltage_v']:.1f} V"

            inverter_temp_txt = "unknown"
            if data.get("inverter_temp_c") is not None:
                inverter_temp_txt = f"{data['inverter_temp_c']:.1f} C"

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["sma_production_overview"],
                "used_tools": ["sma_production_overview"],
                "tool_data": {"sma_production_overview": data},
                "answer": (
                    f"SMA production overview: AC output is {ac_power_txt}, "
                    f"today's solar energy is {daily_energy_txt}, total lifetime production is {total_energy_txt}, "
                    f"PV voltage is {pv_voltage_txt}, PV current is {pv_current_txt}, "
                    f"grid voltage is {grid_voltage_txt}, and inverter temperature is {inverter_temp_txt}."
                ),
            }
        except Exception as e:
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["sma_production_overview"],
                "used_tools": ["sma_production_overview"],
                "tool_data": {"sma_production_overview": {"error": str(e)}},
                "answer": f"I found the SMA overview intent, but reading the data failed: {str(e)}",
            }

    if "sma_summary" in intents:
        try:
            data = get_sma_summary_data()

            ac_power_txt = f"{data['ac_power_w']:.0f} W" if data.get("ac_power_w") is not None else "unknown"
            daily_energy_txt = (
                f"{data['daily_energy_kwh']:.3f} kWh" if data.get("daily_energy_kwh") is not None else "unknown"
            )
            total_energy_txt = (
                f"{data['total_energy_kwh']:.3f} kWh" if data.get("total_energy_kwh") is not None else "unknown"
            )
            grid_voltage_txt = (
                f"{data['grid_voltage_v']:.1f} V" if data.get("grid_voltage_v") is not None else "unknown"
            )
            pv_current_txt = f"{data['pv_current_a']:.1f} A" if data.get("pv_current_a") is not None else "unknown"
            pv_voltage_txt = f"{data['pv_voltage_v']:.1f} V" if data.get("pv_voltage_v") is not None else "unknown"
            inverter_temp_txt = (
                f"{data['inverter_temp_c']:.1f} C" if data.get("inverter_temp_c") is not None else "unknown"
            )

            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["sma_summary"],
                "used_tools": ["sma_summary"],
                "tool_data": {"sma_summary": data},
                "answer": (
                    f"SMA summary: AC power is {ac_power_txt}, "
                    f"daily energy is {daily_energy_txt}, "
                    f"total energy is {total_energy_txt}, "
                    f"grid voltage is {grid_voltage_txt}, "
                    f"PV current is {pv_current_txt}, "
                    f"PV voltage is {pv_voltage_txt}, "
                    f"and inverter temperature is {inverter_temp_txt}."
                ),
            }
        except Exception as e:
            return {
                "status": "ok",
                "mode": "direct_tool",
                "intents": ["sma_summary"],
                "used_tools": ["sma_summary"],
                "tool_data": {"sma_summary": {"error": str(e)}},
                "answer": f"I found the SMA summary intent, but reading the data failed: {str(e)}",
            }

    return None
