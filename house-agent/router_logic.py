from router_tools import (
    get_power_now,
    get_energy_today,
    get_energy_yesterday,
    get_energy_compare_today_yesterday,
    get_phase_overview,
    get_energy_summary,
    get_house_overview,
    get_power_peak_today,
    get_phase_imbalance_summary,
    get_power_quality_summary,
    get_anomaly_summary,
    get_load_distribution_summary,
    get_import_export_status_now,
    get_daily_energy_story,
    get_power_last_24h_summary,
    get_compare_last_24h_vs_previous_24h,
    get_reactive_load_summary,
    get_compare_peak_today_yesterday,
    get_compare_last_24h_vs_previous_24h,
    get_reactive_load_summary,
    get_night_baseload_summary,


    get_loxone_structure_summary,
    get_loxone_rooms,
    get_loxone_categories,
    get_loxone_room_names,
    get_loxone_category_names,
    get_loxone_controls_by_room,
    get_loxone_controls_by_category,
    get_loxone_control_names_by_room,
    get_loxone_control_names_by_category,
    get_loxone_control_types_by_room,
    get_loxone_control_types_by_category,
    get_loxone_favorites_by_room,
    get_loxone_favorites_by_category,
    get_loxone_secured_controls_by_room,
    get_loxone_secured_controls_by_category,
    get_loxone_subcontrols_by_room,
    get_loxone_subcontrols_by_category,
    get_loxone_lighting_controls_by_room,
    get_loxone_alarm_controls,
    get_loxone_temperature_controls_by_room,
    get_loxone_presence_controls_by_room,
    get_loxone_audio_controls_by_room,
    get_loxone_controls_search,



)



def detect_intents(question: str) -> list[str]:
    q = question.lower()
    intents = []

    # Snapshot
    if any(x in q for x in [
        "power now", "current power", "using now", "consumption now",
        "house power", "how much power", "how much are we using",
        "current usage", "current consumption"
    ]):
        intents.append("power_now")

    if any(x in q for x in [
        "importing or exporting", "import or export", "drawing from grid",
        "feeding back", "feeding into grid", "grid flow",
        "from grid or to grid", "are we importing", "are we exporting"
    ]):
        intents.append("import_export_status_now")

    if any(x in q for x in [
        "phase", "l1", "l2", "l3", "voltage", "current per phase", "loaded phase"
    ]):
        intents.append("phase_overview")

    if any(x in q for x in [
        "phase imbalance", "imbalanced phases", "load imbalance",
        "which phase is most loaded", "most loaded phase", "least loaded phase"
    ]):
        intents.append("phase_imbalance_summary")

    if any(x in q for x in [
        "load distribution", "distribution across phases", "phase distribution",
        "how balanced is the load", "which phase carries most load",
        "load split", "phase load split"
    ]):
        intents.append("load_distribution_summary")

    if any(x in q for x in [
        "power quality", "quality of power", "frequency normal",
        "power factor", "reactive load", "reactive power",
        "is the power quality okay", "electrical quality"
    ]):
        intents.append("power_quality_summary")

    if any(x in q for x in [
        "summary", "status", "overview", "reactive", "power factor", "frequency"
    ]):
        intents.append("energy_summary")

    if any(x in q for x in [
        "house overview", "house status", "overview of the house",
        "how is the house doing", "home overview", "current house status"
    ]):
        intents.append("house_overview")

    if any(x in q for x in [
        "anomaly", "anything unusual", "anything wrong",
        "electrical issue", "power issue", "house issue",
        "is something wrong", "any problem right now",
        "unusual", "problem", "wrong"
    ]):
        intents.append("anomaly_summary")

    # Daily
    if any(x in q for x in [
        "today", "import today", "export today", "energy today", "used today"
    ]):
        intents.append("energy_today")

    if any(x in q for x in [
        "yesterday", "import yesterday", "export yesterday", "energy yesterday", "used yesterday"
    ]):
        intents.append("energy_yesterday")

    if any(x in q for x in [
        "compared to yesterday", "today and yesterday",
        "today vs yesterday", "difference from yesterday",
        "compare today and yesterday", "compare today vs yesterday"
    ]):

        intents.append("energy_compare_today_yesterday")


    if any(x in q for x in [
        "peak today", "highest power today", "max power today",
        "maximum power today", "power peak today"
    ]):
        intents.append("power_peak_today")

    if any(x in q for x in [
        "daily energy story", "summarize today", "how has today gone",
        "today's energy story", "energy story today", "summarize today's energy"
    ]):
        intents.append("daily_energy_story")

    # Trends
    if any(x in q for x in [
        "last 24h", "last 24 hours", "power trend",
        "consumption trend", "how has power changed",
        "power summary last day", "power over the last day"
    ]):
        intents.append("power_last_24h_summary")

    if any(x in q for x in [
        "compare last 24h", "last 24h vs previous 24h",
        "previous 24h", "compared to previous day",
        "more than previous 24h", "less than previous 24h"
    ]):
        intents.append("compare_last_24h_vs_previous_24h")

    if any(x in q for x in [
        "reactive load summary", "summarize reactive load",
        "reactive load situation", "reactive behavior"
    ]):
        intents.append("reactive_load_summary")

    if any(x in q for x in [
        "compare peak today and yesterday", "peak today vs yesterday",
        "compare peak power", "peak comparison"
    ]):
        intents.append("compare_peak_today_yesterday")




    if any(x in q for x in [
        "compare last 24h", "last 24h vs previous 24h",
        "previous 24h", "compared to previous day",
        "more than previous 24h", "less than previous 24h"
    ]):
        intents.append("compare_last_24h_vs_previous_24h")

    if any(x in q for x in [
        "reactive load summary", "summarize reactive load",
        "reactive load situation", "reactive behavior"
    ]):
        intents.append("reactive_load_summary")

    if any(x in q for x in [
        "night baseload", "night base load", "overnight load",
        "overnight baseload", "base load at night"
    ]):
        intents.append("night_baseload_summary")

    if "compare" in q and " from " in q and " vs " in q and " to " in q:
        intents.append("compare_periods_from_question")




    return list(dict.fromkeys(intents))




def _detect_loxone_room(question_lower: str, room_names: list[str]) -> str | None:
    for room in room_names:
        if room.lower() in question_lower:
            return room
    return None


def _detect_loxone_category(question_lower: str, category_names: list[str]) -> str | None:
    for category in category_names:
        if category.lower() in question_lower:
            return category
    return None



def gather_house_data(question: str) -> dict:
    intents = detect_intents(question)
    data = {}

    # Prefer one summary call for overview-style questions
    if "house_overview" in intents:
        data["house_overview"] = get_house_overview()
        return {
            "intents": intents,
            "data": data
        }

    if "power_now" in intents:
        data["power_now"] = get_power_now()

    if "import_export_status_now" in intents:
        data["import_export_status_now"] = get_import_export_status_now()

    if "phase_overview" in intents:
        data["phase_overview"] = get_phase_overview()

    if "phase_imbalance_summary" in intents:
        data["phase_imbalance_summary"] = get_phase_imbalance_summary()

    if "load_distribution_summary" in intents:
        data["load_distribution_summary"] = get_load_distribution_summary()

    if "power_quality_summary" in intents:
        data["power_quality_summary"] = get_power_quality_summary()

    if "energy_summary" in intents:
        data["energy_summary"] = get_energy_summary()

    if "anomaly_summary" in intents:
        data["anomaly_summary"] = get_anomaly_summary()

    if "energy_today" in intents:
        data["energy_today"] = get_energy_today()

    if "energy_yesterday" in intents:
        data["energy_yesterday"] = get_energy_yesterday()

    if "energy_compare_today_yesterday" in intents:
        data["energy_compare_today_yesterday"] = get_energy_compare_today_yesterday()

    if "power_peak_today" in intents:
        data["power_peak_today"] = get_power_peak_today()

    if "daily_energy_story" in intents:
        data["daily_energy_story"] = get_daily_energy_story()

    if "power_last_24h_summary" in intents:
        data["power_last_24h_summary"] = get_power_last_24h_summary()

    if "compare_last_24h_vs_previous_24h" in intents:
        data["compare_last_24h_vs_previous_24h"] = get_compare_last_24h_vs_previous_24h()

    if "reactive_load_summary" in intents:
        data["reactive_load_summary"] = get_reactive_load_summary()

    if "compare_peak_today_yesterday" in intents:
        data["compare_peak_today_yesterday"] = get_compare_peak_today_yesterday()

    if "compare_last_24h_vs_previous_24h" in intents:
        data["compare_last_24h_vs_previous_24h"] = get_compare_last_24h_vs_previous_24h()

    if "reactive_load_summary" in intents:
        data["reactive_load_summary"] = get_reactive_load_summary()

    if "night_baseload_summary" in intents:
        data["night_baseload_summary"] = get_night_baseload_summary()

    # ============================================================
    # Loxone mirror
    # ============================================================
    try:
        ql = question.lower()

        loxone_keywords = [
            "loxone",
            "room",
            "rooms",
            "category",
            "categories",
            "alarm",
            "lighting",
            "light",
            "lights",
            "presence",
            "temperature",
            "audio",
            "favorite",
            "favorites",
            "secured",
            "control",
            "controls",
        ]

        is_loxone_question = any(word in ql for word in loxone_keywords)

        if is_loxone_question:
            structure = get_loxone_structure_summary()
            data["loxone_structure_summary"] = structure

            room_names = structure.get("rooms", [])
            category_names = structure.get("categories", [])

            matched_room = _detect_loxone_room(ql, room_names)
            matched_category = _detect_loxone_category(ql, category_names)

            if "room" in ql or "rooms" in ql:
                if "loxone_rooms" not in intents:
                    intents.append("loxone_rooms")
                data["loxone_rooms"] = get_loxone_rooms()

            if "category" in ql or "categories" in ql:
                if "loxone_categories" not in intents:
                    intents.append("loxone_categories")
                data["loxone_categories"] = get_loxone_categories()

            if matched_room:
                if "loxone_controls_by_room" not in intents:
                    intents.append("loxone_controls_by_room")
                data["loxone_controls_by_room"] = get_loxone_controls_by_room(matched_room)

                if "name" in ql or "list" in ql or "show" in ql or "which" in ql:
                    data["loxone_control_names_by_room"] = get_loxone_control_names_by_room(matched_room)
                    if "loxone_control_names_by_room" not in intents:
                        intents.append("loxone_control_names_by_room")

                if "type" in ql or "types" in ql:
                    data["loxone_control_types_by_room"] = get_loxone_control_types_by_room(matched_room)
                    if "loxone_control_types_by_room" not in intents:
                        intents.append("loxone_control_types_by_room")

                if "favorite" in ql:
                    data["loxone_favorites_by_room"] = get_loxone_favorites_by_room(matched_room)
                    if "loxone_favorites_by_room" not in intents:
                        intents.append("loxone_favorites_by_room")

                if "secured" in ql or "secure" in ql:
                    data["loxone_secured_controls_by_room"] = get_loxone_secured_controls_by_room(matched_room)
                    if "loxone_secured_controls_by_room" not in intents:
                        intents.append("loxone_secured_controls_by_room")

                if "subcontrol" in ql or "subcontrols" in ql:
                    data["loxone_subcontrols_by_room"] = get_loxone_subcontrols_by_room(matched_room)
                    if "loxone_subcontrols_by_room" not in intents:
                        intents.append("loxone_subcontrols_by_room")

                if "light" in ql or "lights" in ql or "lighting" in ql:
                    data["loxone_lighting_controls_by_room"] = get_loxone_lighting_controls_by_room(matched_room)
                    if "loxone_lighting_controls_by_room" not in intents:
                        intents.append("loxone_lighting_controls_by_room")

                if "temperature" in ql or "climate" in ql:
                    data["loxone_temperature_controls_by_room"] = get_loxone_temperature_controls_by_room(matched_room)
                    if "loxone_temperature_controls_by_room" not in intents:
                        intents.append("loxone_temperature_controls_by_room")

                if "presence" in ql:
                    data["loxone_presence_controls_by_room"] = get_loxone_presence_controls_by_room(matched_room)
                    if "loxone_presence_controls_by_room" not in intents:
                        intents.append("loxone_presence_controls_by_room")

                if "audio" in ql or "music" in ql:
                    data["loxone_audio_controls_by_room"] = get_loxone_audio_controls_by_room(matched_room)
                    if "loxone_audio_controls_by_room" not in intents:
                        intents.append("loxone_audio_controls_by_room")

            if matched_category:
                if "loxone_controls_by_category" not in intents:
                    intents.append("loxone_controls_by_category")
                data["loxone_controls_by_category"] = get_loxone_controls_by_category(matched_category)

                if "name" in ql or "list" in ql or "show" in ql or "which" in ql:
                    data["loxone_control_names_by_category"] = get_loxone_control_names_by_category(matched_category)
                    if "loxone_control_names_by_category" not in intents:
                        intents.append("loxone_control_names_by_category")

                if "type" in ql or "types" in ql:
                    data["loxone_control_types_by_category"] = get_loxone_control_types_by_category(matched_category)
                    if "loxone_control_types_by_category" not in intents:
                        intents.append("loxone_control_types_by_category")

                if "favorite" in ql:
                    data["loxone_favorites_by_category"] = get_loxone_favorites_by_category(matched_category)
                    if "loxone_favorites_by_category" not in intents:
                        intents.append("loxone_favorites_by_category")

                if "secured" in ql or "secure" in ql:
                    data["loxone_secured_controls_by_category"] = get_loxone_secured_controls_by_category(matched_category)
                    if "loxone_secured_controls_by_category" not in intents:
                        intents.append("loxone_secured_controls_by_category")

                if "subcontrol" in ql or "subcontrols" in ql:
                    data["loxone_subcontrols_by_category"] = get_loxone_subcontrols_by_category(matched_category)
                    if "loxone_subcontrols_by_category" not in intents:
                        intents.append("loxone_subcontrols_by_category")

            if "alarm" in ql:
                data["loxone_alarm_controls"] = get_loxone_alarm_controls()
                if "loxone_alarm_controls" not in intents:
                    intents.append("loxone_alarm_controls")

            if "search " in ql:
                term = question.strip()
                data["loxone_controls_search"] = get_loxone_controls_search(term)
                if "loxone_controls_search" not in intents:
                    intents.append("loxone_controls_search")

    except Exception as e:
        data["loxone_error"] = {"error": str(e)}



    return {
        "intents": intents,
        "data": data
    }
