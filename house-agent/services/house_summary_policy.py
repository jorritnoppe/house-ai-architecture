# services/house_summary_policy.py

from __future__ import annotations

from typing import Any, Dict, List


MAX_FACTS_BY_MODE = {
    "overview": 4,
    "briefing": 5,
    "system": 6,
}

SOLAR_MENTION_THRESHOLD_KW = 0.15
IMPORT_EXPORT_MENTION_THRESHOLD_KW = 0.20


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _append_fact(
    facts: List[Dict[str, Any]],
    *,
    category: str,
    message: str,
    priority: int,
    severity: int = 1,
    technical: bool = False,
) -> None:
    if not message:
        return
    facts.append(
        {
            "category": category,
            "message": message.strip(),
            "priority": priority,
            "severity": severity,
            "technical": technical,
        }
    )


def _join_natural(items: List[str]) -> str:
    items = [str(x).strip() for x in items if str(x).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _human_room_label(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return "unknown room"

    aliases = {
        "masterbedroom": "master bedroom",
        "deskroom": "desk room",
        "entranceroom": "entrance room",
        "livingroom": "living room",
        "childroom": "child room",
        "bathroom": "bathroom",
        "attickroom": "attic room",
        "iotroom": "iot room",
        "hallwayroom": "hallway",
        "storageroom": "storage room",
        "kitchenroom": "kitchen",
        "wcroom": "WC",
        "powerroom": "power room",
        "terrasroom": "terrace",
        "trapbeneden": "downstairs stairs",
        "trapboven": "upstairs stairs",
        "gardenroom": "garden room",
        "diningroom": "dining room",
    }
    return aliases.get(raw.lower(), raw.replace("_", " "))


def _build_energy_facts(house_state: Dict[str, Any], facts: List[Dict[str, Any]], mode: str) -> None:
    summary = (house_state.get("summary") or {})
    interpreted_house_load_kw = _safe_float(summary.get("interpreted_house_load_kw"))
    interpreted_grid_import_kw = _safe_float(summary.get("interpreted_grid_import_kw"))
    interpreted_grid_export_kw = _safe_float(summary.get("interpreted_grid_export_kw"))
    interpreted_solar_power_kw = _safe_float(summary.get("interpreted_solar_power_kw"))
    excess_energy_available_kw = _safe_float(summary.get("excess_energy_available_kw"))
    excess_energy_state = summary.get("excess_energy_state") or "none"

    energy_mode = summary.get("energy_mode")
    solar_active = bool(summary.get("solar_active"))
    importing_from_grid = bool(summary.get("importing_from_grid"))
    exporting_excess = bool(summary.get("exporting_excess"))

    if mode == "system":
        if interpreted_house_load_kw is not None:
            _append_fact(
                facts,
                category="energy",
                message=f"Current interpreted house load is {interpreted_house_load_kw:.2f} kilowatts.",
                priority=52,
                technical=True,
            )

        if solar_active and interpreted_solar_power_kw is not None and interpreted_solar_power_kw >= SOLAR_MENTION_THRESHOLD_KW:
            _append_fact(
                facts,
                category="energy",
                message=f"Solar production is around {interpreted_solar_power_kw:.2f} kilowatts right now.",
                priority=48,
                technical=True,
            )

        if importing_from_grid and interpreted_grid_import_kw is not None and interpreted_grid_import_kw >= IMPORT_EXPORT_MENTION_THRESHOLD_KW:
            _append_fact(
                facts,
                category="energy",
                message=f"Grid import is about {interpreted_grid_import_kw:.2f} kilowatts.",
                priority=46,
                technical=True,
            )

        if exporting_excess and interpreted_grid_export_kw is not None and interpreted_grid_export_kw >= IMPORT_EXPORT_MENTION_THRESHOLD_KW:
            _append_fact(
                facts,
                category="energy",
                message=f"Grid export is about {interpreted_grid_export_kw:.2f} kilowatts.",
                priority=46,
                technical=True,
            )

        if excess_energy_available_kw is not None and excess_energy_available_kw >= 0.5:
            _append_fact(
                facts,
                category="energy",
                message=f"There is about {excess_energy_available_kw:.2f} kilowatts of excess electricity available right now.",
                priority=44,
                technical=True,
            )

            _append_fact(
                facts,
                category="energy",
                message=f"Excess energy state is {excess_energy_state}.",
                priority=42,
                technical=True,
            )

        return

    if interpreted_house_load_kw is not None:
        base = f"The house is currently using {interpreted_house_load_kw:.2f} kilowatts"

        if energy_mode == "exporting_excess" and interpreted_grid_export_kw is not None:
            msg = f"{base}, and solar is producing enough to export some excess."
        elif energy_mode == "solar_covering_load" and solar_active:
            msg = f"{base}, with solar covering most of the current demand."
        elif energy_mode == "grid_assisted" and interpreted_grid_import_kw is not None:
            msg = f"{base}, and a modest amount is being imported from the grid."
        else:
            msg = f"{base}."

        _append_fact(facts, category="energy", message=msg, priority=100)

    if mode in ("briefing",):
        if solar_active and interpreted_solar_power_kw is not None and interpreted_solar_power_kw >= SOLAR_MENTION_THRESHOLD_KW:
            _append_fact(
                facts,
                category="energy",
                message=f"Solar production is around {interpreted_solar_power_kw:.2f} kilowatts right now.",
                priority=72,
            )


def _build_climate_facts(house_state: Dict[str, Any], facts: List[Dict[str, Any]], mode: str = "overview") -> None:
    if mode == "system":
        return

    climate = house_state.get("climate_summary") or house_state.get("climate") or {}
    min_temp = _safe_float(climate.get("min_temp_c"))
    max_temp = _safe_float(climate.get("max_temp_c"))

    if min_temp is not None and max_temp is not None:
        _append_fact(
            facts,
            category="comfort",
            message=f"Temperatures across the house look normal, roughly {min_temp:.1f} to {max_temp:.1f} degrees.",
            priority=70,
        )


def _build_activity_facts(house_state: Dict[str, Any], facts: List[Dict[str, Any]], mode: str = "overview") -> None:
    if mode == "system":
        return

    summary = house_state.get("summary") or {}
    quiet_now = summary.get("quiet_now")

    occupied_rooms = summary.get("occupied_rooms") or []
    lighting_active_rooms = summary.get("lighting_active_rooms") or []
    rooms_with_sensor_data_count = summary.get("rooms_with_sensor_data_count")
    rooms_idle_count = summary.get("rooms_idle_count")
    rooms_unknown_count = summary.get("rooms_unknown_count")

    occupied_labels = [_human_room_label(x) for x in occupied_rooms]
    lighting_labels = [_human_room_label(x) for x in lighting_active_rooms]

    if occupied_labels:
        _append_fact(
            facts,
            category="activity",
            message=f"Presence is currently detected in {_join_natural(occupied_labels[:5])}.",
            priority=110,
        )

    if lighting_labels:
        _append_fact(
            facts,
            category="activity",
            message=f"Lights appear active in {_join_natural(lighting_labels[:5])}.",
            priority=62,
        )

    if rooms_with_sensor_data_count:
        if rooms_idle_count and rooms_idle_count >= max(2, rooms_with_sensor_data_count // 2):
            _append_fact(
                facts,
                category="activity",
                message="Most monitored rooms are idle right now.",
                priority=58,
            )

        _append_fact(
            facts,
            category="activity",
            message=f"Sensor coverage is available for {rooms_with_sensor_data_count} rooms.",
            priority=40,
        )

    if rooms_unknown_count and rooms_unknown_count > 0:
        _append_fact(
            facts,
            category="activity",
            message=f"{rooms_unknown_count} rooms currently have limited or no sensor data.",
            priority=35,
        )

    if quiet_now is True and not occupied_labels:
        _append_fact(
            facts,
            category="activity",
            message="The house is quiet right now.",
            priority=55,
        )
    elif quiet_now is False and not occupied_labels:
        _append_fact(
            facts,
            category="activity",
            message="There is some activity in the house right now.",
            priority=55,
        )


def _build_infra_facts(house_state: Dict[str, Any], facts: List[Dict[str, Any]], mode: str) -> None:
    summary = house_state.get("summary") or {}

    offline_nodes = summary.get("offline_nodes") or []
    warning_nodes_count = summary.get("warning_nodes_count")
    service_warning_hosts = summary.get("service_warning_hosts") or []
    monitoring_unavailable_nodes = summary.get("monitoring_unavailable_nodes") or []
    voice_nodes_online = summary.get("voice_nodes_online")

    offline_set = {str(x).strip() for x in offline_nodes if str(x).strip()}
    monitoring_only = [
        node for node in monitoring_unavailable_nodes
        if str(node).strip() and str(node).strip() not in offline_set
    ]

    if mode == "overview":
        if offline_nodes:
            names = ", ".join(offline_nodes[:2])
            extra = ""
            if len(offline_nodes) > 2:
                extra = f", and {len(offline_nodes) - 2} more"
            _append_fact(
                facts,
                category="infra",
                message=f"One or more nodes are offline, including {names}{extra}.",
                priority=50,
                severity=2,
            )
        return

    if mode == "briefing":
        if offline_nodes:
            names = ", ".join(offline_nodes[:2])
            _append_fact(
                facts,
                category="infra",
                message=f"Some infrastructure still needs attention, including offline nodes such as {names}.",
                priority=52,
                severity=2,
            )
        elif warning_nodes_count:
            _append_fact(
                facts,
                category="infra",
                message=f"{warning_nodes_count} node warnings are currently present.",
                priority=45,
                severity=1,
            )
        return

    if offline_nodes:
        _append_fact(
            facts,
            category="infra",
            message=f"Offline nodes: {', '.join(offline_nodes)}.",
            priority=100,
            severity=2,
            technical=True,
        )

    if warning_nodes_count:
        _append_fact(
            facts,
            category="infra",
            message=f"Nodes with warnings: {warning_nodes_count}.",
            priority=92,
            technical=True,
        )

    if service_warning_hosts:
        _append_fact(
            facts,
            category="infra",
            message=f"Service warnings are present on: {', '.join(service_warning_hosts)}.",
            priority=88,
            technical=True,
        )

    if monitoring_only:
        _append_fact(
            facts,
            category="infra",
            message=f"Service monitoring is unavailable on: {', '.join(monitoring_only)}.",
            priority=84,
            technical=True,
        )

    if voice_nodes_online is not None:
        try:
            voice_nodes_online = int(voice_nodes_online)
            if voice_nodes_online == 1:
                _append_fact(
                    facts,
                    category="infra",
                    message="One voice node is currently online.",
                    priority=70,
                    technical=True,
                )
            elif voice_nodes_online > 1:
                _append_fact(
                    facts,
                    category="infra",
                    message=f"{voice_nodes_online} voice nodes are currently online.",
                    priority=70,
                    technical=True,
                )
        except Exception:
            pass


def _dedupe_facts(facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for fact in facts:
        key = (fact.get("category"), fact.get("message"))
        if key in seen:
            continue
        seen.add(key)
        out.append(fact)
    return out


def build_house_summary_facts(house_state: Dict[str, Any], mode: str = "overview") -> List[Dict[str, Any]]:
    facts: List[Dict[str, Any]] = []

    _build_energy_facts(house_state, facts, mode)
    _build_climate_facts(house_state, facts, mode)
    _build_activity_facts(house_state, facts, mode)
    _build_infra_facts(house_state, facts, mode)

    return _dedupe_facts(facts)


def rank_house_summary_facts(facts: List[Dict[str, Any]], mode: str = "overview") -> List[Dict[str, Any]]:
    ranked = sorted(
        facts,
        key=lambda f: (
            int(f.get("priority", 0)),
            int(f.get("severity", 0)),
        ),
        reverse=True,
    )

    max_facts = MAX_FACTS_BY_MODE.get(mode, 4)
    return ranked[:max_facts]


def render_house_summary(facts: List[Dict[str, Any]], mode: str = "overview") -> str:
    messages = [f.get("message", "").strip() for f in facts if f.get("message")]
    return " ".join(messages).strip()


def summarize_house_state(house_state: Dict[str, Any], mode: str = "overview") -> str:
    facts = build_house_summary_facts(house_state, mode=mode)
    facts = rank_house_summary_facts(facts, mode=mode)
    return render_house_summary(facts, mode=mode)
