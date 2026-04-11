import requests
import re
import unicodedata
from requests.auth import HTTPBasicAuth

from config import LOXONE_HOST, LOXONE_USER, LOXONE_PASSWORD
from services.loxone_ws_service import get_cached_loxone_value




BASE_URL = f"http://{LOXONE_HOST}"


def _auth():
    return HTTPBasicAuth(LOXONE_USER, LOXONE_PASSWORD)


ROOM_ALIASES = {
    # Canonical Loxone room names
    "attickroom": "attickroom",
    "bathroom": "bathroom",
    "childroom": "childroom",
    "deskroom": "deskroom",
    "diningroom": "diningroom",
    "entranceroom": "entranceroom",
    "gardenroom": "gardenroom",
    "hallwayroom": "hallwayroom",
    "iotroom": "iotroom",
    "kitchenroom": "kitchenroom",
    "livingroom": "livingroom",
    "masterbedroom": "masterbedroom",
    "powerroom": "powerroom",
    "storageroom": "storageroom",
    "terrasroom": "terrasroom",
    "trapbeneden": "trapbeneden",
    "trapboven": "trapboven",
    "wcroom": "wcroom",
    "not assigned": "Not Assigned",

    # Legacy / human aliases mapped to canonical Loxone names
    "attic": "attickroom",
    "zolder": "attickroom",
    "storage": "storageroom",
    "berging": "storageroom",
    "living": "livingroom",
    "living room": "livingroom",
    "woonkamer": "livingroom",
    "kitchen": "kitchenroom",
    "keuken": "kitchenroom",
    "bath": "bathroom",
    "badkamer": "bathroom",
    "toilet": "wcroom",
    "wc": "wcroom",
    "master bedroom": "masterbedroom",
    "bedroom": "masterbedroom",
    "slaapkamer": "masterbedroom",
    "desk": "deskroom",
    "office": "deskroom",
    "bureau": "deskroom",
    "hallway": "hallwayroom",
    "hal": "hallwayroom",
    "entrance": "entranceroom",
    "garden": "gardenroom",
    "power": "powerroom",
    "terrace": "terrasroom",
    "terras": "terrasroom",
}

def _clean_climate_value(metric: str | None, value):
    if value is None:
        return None

    try:
        numeric = float(value)
    except Exception:
        return value

    if metric in {"outdoor_temperature", "outdoor_temperature_avg"} and numeric <= -999:
        return None

    if metric == "humidity" and numeric < 0:
        return None

    if metric == "co2" and numeric < 0:
        return None

    return numeric



# --------------------------------------------------
# BASIC HELPERS
# --------------------------------------------------

def _normalize_text(value: str) -> str:
    value = str(value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def _contains_any_word(text: str, keywords: list[str]) -> bool:
    text = str(text or "").lower()
    text = text.replace("_", " ").replace("-", " ")
    for keyword in keywords:
        kw = str(keyword or "").lower().strip()
        if not kw:
            continue
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text):
            return True
    return False



def _safe_float(value):
    try:
        if isinstance(value, str):
            cleaned = value.replace("Â°", "").replace("°", "").replace(",", ".").strip()
            return float(cleaned)
        return float(value)
    except Exception:
        return None


def _guess_unit(name: str, cat_name: str, state_key: str | None):
    blob = " ".join([
        _normalize_text(name),
        _normalize_text(cat_name),
        _normalize_text(state_key or ""),
    ])

    if _contains_any(blob, ["temp", "temperatur", "temperature"]):
        return "°C"
    if _contains_any(blob, ["humidity", "feuchte", "luchtvocht", "vocht"]):
        return "%"
    if _contains_any(blob, ["co2"]):
        return "ppm"
    if _contains_any(blob, ["power", "vermogen", "leistung"]):
        return "W"
    if _contains_any(blob, ["energy", "energie"]):
        return "kWh"
    if _contains_any(blob, ["voltage", "spannung"]):
        return "V"
    if _contains_any(blob, ["current", "strom"]):
        return "A"
    if _contains_any(blob, ["brightness", "lux", "illum", "licht"]):
        return "lux"
    if _contains_any(blob, ["position", "shade", "jaloezie", "blind", "rolluik"]):
        return "%"
    return None


def _preferred_state_keys_for_type(control_type: str):
    ct = _normalize_text(control_type)
    if "roomcontroller" in ct:
        return ["tempActual", "value", "active"]
    if "infoonlyanalog" in ct:
        return ["value", "active"]
    if "switch" in ct:
        return ["active", "value"]
    if "dimmer" in ct:
        return ["position", "value", "active"]
    if "lightcontroller" in ct:
        return ["activeMoods", "moodList", "value", "active"]
    if "jalousie" in ct or "blind" in ct:
        return ["position", "shadePosition", "up", "down", "active"]
    return ["value", "active", "tempActual", "position"]


# --------------------------------------------------
# CATEGORY / SENSOR CLASSIFICATION
# --------------------------------------------------

def classify_control(control: dict) -> dict:
    name = str(control.get("name") or "")
    ctrl_type = str(control.get("type") or "")
    room_name = str(control.get("room_name") or "")
    cat_name = str(control.get("cat_name") or "")

    name_n = _normalize_text(name)
    ctrl_type_n = _normalize_text(ctrl_type)
    room_name_n = _normalize_text(room_name)
    cat_name_n = _normalize_text(cat_name)

    blob = " | ".join([name_n, ctrl_type_n, room_name_n, cat_name_n])

    states = control.get("states", {}) or {}
    state_keys = [_normalize_text(k) for k in states.keys()]

    domain = "unknown"
    sensor_type = "unknown"
    role = "control"
    description = "Unclassified Loxone control."
    tags = []

    # --------------------------------------------------
    # STRONG TYPE / CATEGORY FIRST
    # --------------------------------------------------

    if ctrl_type_n == "iroomcontrollerv2":
        domain = "climate"
        sensor_type = "climate_controller"
        role = "sensor"
        description = "Climate controller or climate state source."
        tags = ["climate", "controller"]

        if "tempactual" in state_keys:
            tags.append("temperature_actual")
        if "temptarget" in state_keys:
            tags.append("temperature_target")
        if "humidityactual" in state_keys or "humidity" in state_keys:
            tags.append("humidity")
        if "co2" in state_keys:
            tags.append("co2")
        if "operatingmode" in state_keys or "currentmode" in state_keys or "activemode" in state_keys:
            tags.append("operating_mode")
        if "openwindow" in state_keys:
            tags.append("open_window")

    elif ctrl_type_n == "climatecontrollerus":
        domain = "climate"
        sensor_type = "climate_hvac_controller"
        role = "sensor"
        description = "Central climate controller block that links all room climate controllers together and requests boiler heating when needed."
        tags = ["climate", "controller", "central", "boiler", "heating_demand", "iotroom"]

    elif ctrl_type_n == "nfccodetouch":
        domain = "access"
        sensor_type = "access_control"
        role = "sensor"
        description = "Read-only NFC and keypad access control block."
        tags = ["access", "nfc", "keypad"]

    elif ctrl_type_n == "intercom":
        domain = "access"
        sensor_type = "access_control"
        role = "sensor"
        description = "Intercom or door communication device."
        tags = ["access", "intercom"]

    elif ctrl_type_n in {"presencedetector", "presence"}:
        domain = "presence"
        sensor_type = "presence"
        role = "sensor"
        description = "Presence-related sensor."
        tags = ["presence"]

    # --------------------------------------------------
    # STRONG NAME PATTERNS BEFORE GENERIC WORD MATCHING
    # --------------------------------------------------

    elif "_access_" in name_n or name_n.startswith("entranceroom_access_") or name_n.endswith("_nfc_access_control"):
        domain = "access"
        sensor_type = "access_control"
        role = "sensor"
        description = "Access-related sensor or control."
        tags = ["access"]

    elif name_n.endswith("_presence_sensor"):
        domain = "presence"
        sensor_type = "presence"
        role = "sensor"
        description = "Presence-related sensor."
        tags = ["presence"]

    elif "doorbird_motion" in name_n or name_n.endswith("_motion_input"):
        domain = "presence"
        sensor_type = "motion"
        role = "sensor"
        description = "Motion-related sensor."
        tags = ["presence", "motion"]

    elif (
        name_n.endswith("_lightingcontroller")
        or name_n.startswith("lightcontroller")
        or name_n.endswith("_lighting_schedule")
        or (
            ctrl_type_n == "daytimer"
            and ("lighting" in name_n or "light" in name_n)
        )
        or ctrl_type_n in {
            "lightcontrollerv2",
            "lightscenergb",
            "centrallightcontroller",
            "colorpickerv2",
            "dimmer",
        }
    ):
        domain = "lighting"
        sensor_type = "lighting"
        role = "control"
        description = "Lighting-related control."
        tags = ["lighting"]

    elif (
        "_power_" in name_n
        or name_n.startswith("picore_")
        or name_n.endswith("_reset_counters_button")
        or name_n.startswith("house_")
        and name_n.endswith("_mode_switch")
    ):
        domain = "power"
        sensor_type = "power_control"
        role = "control"
        description = "Power-related or house mode control."
        tags = ["power"]

    elif (
        name_n.endswith("_heatingcontrol")
        or "heating_towels" in name_n
        or _contains_any(blob, ["heatingcontrol", "floorheat", "floorheating", "radiator", "heater", "warmwater", "boiler", "towelheating"])
    ):
        domain = "heating"
        sensor_type = "heating"
        role = "control"
        description = "Heating-related control."
        tags = ["heating"]

    elif (
        "control_audio" in name_n
        or "audiobathroom" in name_n
        or "audiolivingroom" in name_n
        or "audioparty" in name_n
        or name_n.endswith("_route_switch")
        or name_n in {"picore_allonroom_power_button", "picore_alloffroom_power_button"}
        or (
            _contains_any(blob, ["audio", "music", "speaker", "picore", "party", "playback"])
            and "playlist" not in name_n
        )
    ):
        domain = "audio"
        sensor_type = "audio_control"
        role = "control"
        description = "Audio-related control."
        tags = ["audio"]

    elif (
        ctrl_type_n == "valueselector"
        and _contains_any(name_n, ["luifel", "shade", "blind", "jaloezie", "pattern"])
    ) or _contains_any(blob, ["jalousie", "blind", "shade", "rolluik", "shutter", "sunshade", "luifel"]):
        domain = "shading"
        sensor_type = "cover"
        role = "control"
        description = "Shading or blind-related control."
        tags = ["shading"]

    elif _contains_any(blob, ["climate", "klima", "roomcontroller"]) or cat_name_n == "klima":
        domain = "climate"
        sensor_type = "climate"
        role = "sensor"
        description = "Climate-related sensor or controller."
        tags = ["climate"]

    elif _contains_any(blob, ["presence", "occupancy", "aanwezig"]):
        domain = "presence"
        sensor_type = "presence"
        role = "sensor"
        description = "Presence-related sensor."
        tags = ["presence"]

    elif _contains_any(blob, ["motion", "beweg", "pir"]):
        domain = "presence"
        sensor_type = "motion"
        role = "sensor"
        description = "Motion-related sensor."
        tags = ["motion"]

    elif _contains_any(blob, ["door", "window", "deur", "raam", "contact", "reed"]):
        domain = "access"
        sensor_type = "door_window"
        role = "sensor"
        description = "Door or window contact related sensor."
        tags = ["access", "door_window"]

    elif _contains_any(blob, ["water", "leak", "flood", "softener", "salt"]):
        domain = "water"
        sensor_type = "water"
        role = "sensor"
        description = "Water-related sensor or control."
        tags = ["water"]

    elif ctrl_type_n in {"fronius", "efm", "meter", "spotpriceoptimizer"} or _contains_any(blob, ["power meter", "energy meter", "energy flow", "gasmeter", "solar", "spot price", "fronius", "energie"]):
        domain = "energy"
        sensor_type = "energy"
        role = "sensor"
        description = "Energy-related sensor or monitor."
        tags = ["energy"]

    elif _contains_any(blob, ["alarm", "security", "smoke", "fire", "gas", "co "]):
        domain = "security"
        sensor_type = "security"
        role = "sensor"
        description = "Security-related sensor or control."
        tags = ["security"]

    elif _contains_any(blob, ["switch", "button", "pushbutton"]):
        domain = "switch"
        sensor_type = "switch"
        role = "control"
        description = "Generic switch or button control."
        tags = ["switch"]

    # --------------------------------------------------
    # STATE-KEY SPECIALIZATION
    # --------------------------------------------------

    if domain == "climate":
        if ctrl_type_n == "iroomcontrollerv2":
            sensor_type = "climate_controller"
            role = "sensor"
        elif ctrl_type_n == "climatecontrollerus":
            sensor_type = "climate_hvac_controller"
            role = "sensor"
        elif "tempactual" in state_keys:
            sensor_type = "temperature"
            role = "sensor"
        elif "humidityactual" in state_keys or "humidity" in state_keys:
            sensor_type = "humidity"
            role = "sensor"
        elif "co2" in state_keys:
            sensor_type = "co2"
            role = "sensor"

    if domain == "heating" and "value" in state_keys and "heatingcontrol" in name_n:
        role = "sensor"

    # --------------------------------------------------
    # SPECIFIC ENRICHMENT / OVERRIDES
    # --------------------------------------------------

    if name_n in {"virtualinput_doorbird_motion", "entranceroom_access_doorbird_motion_input"}:
        domain = "presence"
        sensor_type = "motion"
        role = "sensor"
        description = "DoorBird motion event input."
        tags = ["presence", "motion", "doorbird", "entranceroom"]

    elif name_n == "entranceroom_access_doorbird_ir_command":
        domain = "access"
        sensor_type = "access_control"
        role = "sensor"
        description = "DoorBird infrared or related access-side command state."
        tags = ["access", "doorbird", "infrared", "entranceroom"]

    elif name_n == "entranceroom_doorbird_presence_sensor":
        domain = "presence"
        sensor_type = "presence"
        role = "sensor"
        description = "DoorBird presence input."
        tags = ["presence", "doorbird", "entranceroom"]

    elif name_n.endswith("_climate_controller") and ctrl_type_n == "iroomcontrollerv2":
        base_room = room_name_n or name_n.replace("_climate_controller", "")
        description = (
            f"Read-only room climate controller for {base_room}. "
            f"Provides measured and target climate values, operating mode, humidity, "
            f"and related climate state data. Participates in the linked house climate system."
        )
        tags = ["climate", "controller", base_room]

    elif name_n == "iotroom_climate_controller" and ctrl_type_n == "climatecontrollerus":
        description = (
            "Central climate demand controller that links all climate blocks together. "
            "When any linked room climate controller requests heating demand, this controller "
            "outputs the central heating or boiler demand signal."
        )
        tags = ["climate", "controller", "central", "boiler", "heating_demand", "iotroom"]

    elif "heatingcontrol" in name_n:
        base_room = room_name_n or name_n.replace("_heatingcontrol", "")
        description = f"Heating control value for {base_room}."
        tags = ["heating", "control_value", base_room]

    elif name_n in {
        "bathroom_heating_towels_on_button",
        "bathroom_heating_towels_off_button",
        "on - heating towels",
        "off_ heating towels",
        "sequence controller_towelheating",
    }:
        domain = "heating"
        sensor_type = "heating"
        role = "control"
        description = "Towel heating control."
        tags = ["heating", "towel_heating", "bathroom"]

    elif name_n == "warmwater":
        description = "Timed switch related to warm water / heating routine."
        tags = ["heating", "warm_water", "timed_switch"]

    elif name_n in {"livingroom_floorheat_switch", "floorheatingenable_living"}:
        description = "Enables floor heating for the livingroom zone."
        tags = ["heating", "floor_heating", "enable", "livingroom"]

    elif name_n == "picore_bathroom_power_switch":
        description = "Enables power to the bathroom Raspberry Pi audio player."
        tags = ["audio", "power", "bathroom", "picore"]

    elif name_n == "control_audiobathroom_start_button":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Starts playback on the bathroom audio player."
        tags = ["audio", "bathroom", "start", "playback"]

    elif name_n == "control_audiobathroom_stop_button":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Stops playback on the bathroom audio player."
        tags = ["audio", "bathroom", "stop", "playback"]

    elif name_n == "picore_bathroom_power_schedule":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Bathroom PiCore player power schedule."
        tags = ["audio", "bathroom", "schedule", "power"]

    elif name_n == "picore_deskroom_power_switch":
        description = "Enables power to the deskroom Raspberry Pi audio player."
        tags = ["audio", "deskroom", "power", "picore"]

    elif name_n == "picore_livingroom_power_switch":
        description = "Enables power to the living room Raspberry Pi audio player."
        tags = ["audio", "livingroom", "power", "picore"]

    elif name_n == "picore_livingroom_route_switch":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Enables the living room speaker routing module."
        tags = ["audio", "livingroom", "speaker_route"]

    elif name_n == "control_audiolivingroom_start_button":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Starts playback on the living room audio player."
        tags = ["audio", "livingroom", "start", "playback"]

    elif name_n == "control_audiolivingroom_stop_button":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Stops playback on the living room audio player."
        tags = ["audio", "livingroom", "stop", "playback"]

    elif name_n == "control_audioparty_start_button":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Starts party audio mode."
        tags = ["audio", "party_mode", "start", "livingroom", "bass"]

    elif name_n == "control_audioparty_stop_button":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Stops party audio mode."
        tags = ["audio", "party_mode", "stop", "livingroom", "bass"]

    elif name_n == "picore_allonroom_power_button":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Enables power to all Raspberry Pi audio players."
        tags = ["audio", "power", "all_players", "on"]

    elif name_n == "picore_alloffroom_power_button":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Disables power to all Raspberry Pi audio players."
        tags = ["audio", "power", "all_players", "off"]

    elif name_n == "picore_bassroom_power_switch":
        description = "Enables power to the bass Raspberry Pi audio player."
        tags = ["audio", "bass", "power", "picore"]

    elif name_n == "picore_storageroom_route_switch":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Enables the speaker routing module for the bass or storage room audio path."
        tags = ["audio", "bass", "speaker_route"]

    elif name_n == "picore_toiletroom_power_switch":
        description = "Enables power to the toilet Raspberry Pi audio player."
        tags = ["audio", "wcroom", "toilet", "power", "picore"]

    elif name_n == "picore_wcroom_route_switch":
        domain = "audio"
        sensor_type = "audio_control"
        description = "Enables the speaker routing module for the toilet speaker."
        tags = ["audio", "wcroom", "toilet", "speaker_route"]

    elif name_n.endswith("_nfc_access_control"):
        location = room_name_n or name_n.replace("_nfc_access_control", "")
        description = (
            f"Read-only NFC and keypad access control block for the {location} access location. "
            f"Stores access events, tag or code usage history, and device state."
        )
        tags = ["access", "nfc", "keypad", location]

    elif name_n == "lms print playlists":
        domain = "switch"
        sensor_type = "switch"
        role = "control"
        description = "Manual maintenance or debug action."
        tags = ["switch", "maintenance"]

    elif name_n == "powerroom_energy_reset_counters_button":
        domain = "power"
        sensor_type = "power_control"
        role = "control"
        description = "Manual reset action for energy counters."
        tags = ["power", "energy", "reset", "powerroom"]

    elif name_n == "house_night_mode_switch":
        domain = "power"
        sensor_type = "power_control"
        role = "control"
        description = "House-wide night mode switch."
        tags = ["house", "night_mode", "power"]

    elif name_n in {
        "kitchenroom_pattern_wave_on_button",
        "kitchenroom_pattern_wave_off_button",
        "kitchenroom_luifel_pattern_off_button",
        "kitchenroom_luifel_pattern_update_button",
        "kitchenroom_luifel_pattern_selector",
    }:
        domain = "shading"
        sensor_type = "cover"
        role = "control"
        description = "Awning or shading pattern control."
        tags = ["shading", "awning", "pattern", "kitchenroom"]

    elif name_n == "terrasroom_lighting_schedule":
        domain = "lighting"
        sensor_type = "lighting"
        role = "control"
        description = "Terrace lighting schedule."
        tags = ["lighting", "schedule", "terrasroom"]

    # --------------------------------------------------
    # READABLE FLAG
    # --------------------------------------------------

    readable_keys = {
        "value",
        "tempactual",
        "temptarget",
        "humidityactual",
        "humidity",
        "co2",
        "active",
        "position",
        "shadeposition",
        "operatingmode",
        "currentmode",
        "activemode",
        "openwindow",
        "actualoutdoortemp",
        "demandheat",
        "demandcool",
        "mode",
        "currentstatus",
    }

    readable = any(k in state_keys for k in readable_keys)

    if ctrl_type_n in {"nfccodetouch"}:
        readable = False

    seen = set()
    deduped_tags = []
    for tag in tags:
        if tag and tag not in seen:
            seen.add(tag)
            deduped_tags.append(tag)

    return {
        "domain": domain,
        "sensor_type": sensor_type,
        "role": role,
        "readable": readable,
        "state_keys": list(states.keys()),
        "tags": deduped_tags,
        "description": description,
    }

# --------------------------------------------------
# BASIC LOXONE FETCH
# --------------------------------------------------

def fetch_loxapp3():
    url = f"{BASE_URL}/data/LoxAPP3.json"
    r = requests.get(url, auth=_auth(), timeout=10)
    r.raise_for_status()
    return r.json()


def extract_loxone_value(raw_text: str):
    if raw_text is None:
        return None

    m = re.search(r'value="([^"]+)"', raw_text)
    if not m:
        return raw_text

    value = m.group(1)
    value = value.replace("Â°", "°")
    return value


def fetch_loxone_state_value(uuid: str):
    url = f"{BASE_URL}/dev/sps/io/{uuid}"
    response = requests.get(url, auth=_auth(), timeout=10)
    response.raise_for_status()

    text = response.text.strip()

    try:
        data = response.json()
    except Exception:
        data = None

    if isinstance(data, dict):
        ll = data.get("LL")
        if isinstance(ll, dict):
            value = ll.get("value")
            if isinstance(value, str):
                value = value.replace("Â°", "°")
            return {
                "status": "ok",
                "uuid": uuid,
                "value": value,
                "raw": data,
            }

    extracted = extract_loxone_value(text)
    numeric = _safe_float(extracted)

    return {
        "status": "ok",
        "uuid": uuid,
        "value": numeric if numeric is not None else extracted,
        "raw": text,
    }




def _normalize_state_key(key: str) -> str:
    return _normalize_text(key)




def _unit_for_climate_metric(metric: str | None):
    if metric in {"temperature_actual", "temperature_target", "comfort_temperature", "comfort_temperature_cool", "outdoor_temperature", "outdoor_temperature_avg", "minimum_temp_cooling", "maximum_temp_heating"}:
        return "°C"
    if metric == "humidity":
        return "%"
    if metric == "co2":
        return "ppm"
    return None


def _get_state_value_with_ws_fallback(state_uuid: str):
    cached = get_cached_loxone_value(state_uuid)
    if cached is not None:
        return {
            "status": "ok",
            "uuid": state_uuid,
            "value": cached,
            "source": "websocket_cache",
        }

    try:
        result = fetch_loxone_state_value(state_uuid)
        if isinstance(result, dict):
            result["source"] = "http_poll"
        return result
    except Exception as exc:
        return {
            "status": "error",
            "uuid": state_uuid,
            "value": None,
            "source": "http_poll_failed",
            "error": str(exc),
        }





def _normalize_state_key(key: str) -> str:
    return _normalize_text(key)


def _metric_from_climate_state_key(state_key: str) -> str | None:
    key = _normalize_state_key(state_key)

    mapping = {
        "tempactual": "temperature_actual",
        "temptarget": "temperature_target",
        "comforttemperature": "comfort_temperature",
        "comforttemperaturecool": "comfort_temperature_cool",
        "comforttolerance": "comfort_tolerance",
        "humidityactual": "humidity",
        "humidity": "humidity",
        "co2": "co2",
        "openwindow": "open_window",
        "operatingmode": "operating_mode",
        "currentmode": "current_mode",
        "activemode": "active_mode",
        "actualoutdoortemp": "outdoor_temperature",
        "averageoutdoortemp": "outdoor_temperature_avg",
        "shadingout": "shading_out",
        "demandheat": "demand_heat",
        "demandcool": "demand_cool",
        "mode": "mode",
        "currentstatus": "current_status",
        "stage": "stage",
        "minimumtempcooling": "minimum_temp_cooling",
        "maximumtempheating": "maximum_temp_heating",
        "fan": "fan",
        "threshold": "threshold",
        "excessenergy": "excess_energy",
        "servicemode": "service_mode",
        "outdoortempmode": "outdoor_temp_mode",
        "nextmaintenance": "next_maintenance",
    }

    return mapping.get(key)




# --------------------------------------------------
# CONTROL EXTRACTION
# --------------------------------------------------

def get_all_controls():
    data = fetch_loxapp3()

    rooms = data.get("rooms", {})
    cats = data.get("cats", {})
    controls = data.get("controls", {})

    results = []

    for uuid, ctrl in controls.items():
        room_uuid = ctrl.get("room")
        cat_uuid = ctrl.get("cat")

        room_name = rooms.get(room_uuid, {}).get("name")
        cat_name = cats.get(cat_uuid, {}).get("name")

        item = {
            "uuid": uuid,
            "name": ctrl.get("name"),
            "type": ctrl.get("type"),
            "room_uuid": room_uuid,
            "room_name": room_name,
            "cat_uuid": cat_uuid,
            "cat_name": cat_name,
            "states": ctrl.get("states", {}),
            "details": ctrl.get("details", {}),
            "is_favorite": ctrl.get("isFavorite"),
            "is_secured": ctrl.get("isSecured"),
        }
        item.update(classify_control(item))
        results.append(item)

    return results


def resolve_room_name(room_name: str) -> str:
    raw = str(room_name or "").strip()
    if not raw:
        return raw

    lower = raw.lower()
    if lower in ROOM_ALIASES:
        return ROOM_ALIASES[lower]

    return raw

def get_controls_by_room(room_name: str, domain: str | None = None):
    resolved_room = resolve_room_name(room_name)

    items = [
        item for item in get_all_controls()
        if str(item.get("room_name") or "").strip().lower() == str(resolved_room or "").strip().lower()
    ]

    if domain:
        domain_n = str(domain).strip().lower()
        items = [
            item for item in items
            if str(item.get("domain") or "").strip().lower() == domain_n
        ]

    return {
        "status": "ok",
        "requested_room_name": room_name,
        "room_name": resolved_room,
        "domain": domain,
        "count": len(items),
        "items": items,
    }

def get_controls_by_category(category_name: str):
    category_name_l = str(category_name or "").lower()

    items = [
        item for item in get_all_controls()
        if str(item.get("cat_name") or "").lower() == category_name_l
    ]

    return {
        "status": "ok",
        "category_name": category_name_l,
        "count": len(items),
        "items": items,
    }


def get_controls_by_domain(domain: str):
    domain_l = _normalize_text(domain)

    domain_aliases = {
        "temp": "climate",
        "temperature": "climate",
        "humid": "climate",
        "humidity": "climate",
        "heatingcontrols": "heating",
    }

    wanted = domain_aliases.get(domain_l, domain_l)

    items = [
        item for item in get_all_controls()
        if _normalize_text(item.get("domain")) == wanted
    ]

    return {
        "status": "ok",
        "requested_domain": domain_l,
        "domain": wanted,
        "count": len(items),
        "items": items,
    }






def get_sensor_inventory(room_name: str | None = None):
    items = get_all_controls()

    if room_name:
        resolved_room = resolve_room_name(room_name)
        items = [item for item in items if str(item.get("room_name") or "").lower() == resolved_room.lower()]
    else:
        resolved_room = None

    sensor_like = []
    for item in items:
        role = item.get("role")
        domain = item.get("domain")
        sensor_type = item.get("sensor_type")
        readable = item.get("readable")

        if role == "sensor" or readable or domain in {"presence", "security", "water", "energy"}:
            sensor_like.append(item)

    grouped = {}
    for item in sensor_like:
        key = item.get("sensor_type") or "unknown"
        grouped.setdefault(key, []).append(item)

    return {
        "status": "ok",
        "room_name": resolved_room,
        "count": len(sensor_like),
        "groups": {k: len(v) for k, v in sorted(grouped.items())},
        "items": sensor_like,
    }



# --------------------------------------------------
# LIVE VALUE HELPERS
# --------------------------------------------------

def get_control_state_uuid(control, preferred_keys=None):
    states = control.get("states", {}) or {}

    if preferred_keys:
        for key in preferred_keys:
            if key in states:
                return {
                    "status": "ok",
                    "state_key": key,
                    "uuid": states[key],
                }

    for k, v in states.items():
        return {
            "status": "ok",
            "state_key": k,
            "uuid": v,
        }

    return {
        "status": "error",
        "message": "No readable state",
    }


def get_control_live_value(control: dict):
    preferred = _preferred_state_keys_for_type(control.get("type"))
    state_info = get_control_state_uuid(control, preferred_keys=preferred)

    if state_info.get("status") != "ok":
        return {
            "status": "error",
            "uuid": control.get("uuid"),
            "name": control.get("name"),
            "message": "No readable state UUID found",
        }

    value_result = fetch_loxone_state_value(state_info["uuid"])

    return {
        "status": "ok",
        "uuid": control.get("uuid"),
        "name": control.get("name"),
        "room_name": control.get("room_name"),
        "type": control.get("type"),
        "domain": control.get("domain"),
        "sensor_type": control.get("sensor_type"),
        "state_key": state_info["state_key"],
        "state_uuid": state_info["uuid"],
        "value": value_result.get("value"),
        "unit": _guess_unit(control.get("name"), control.get("cat_name"), state_info["state_key"]),
        "raw": value_result.get("raw"),
    }


def get_live_values_by_room(room_name: str, domain: str | None = None, sensors_only: bool = False):
    result = get_controls_by_room(room_name, domain=domain)
    items = result.get("items", [])

    if sensors_only:
        items = [item for item in items if item.get("readable")]

    values = []
    errors = []

    for item in items:
        if not item.get("readable"):
            continue

        try:
            if str(item.get("domain") or "").lower() == "climate" and str(item.get("type") or "").lower() in {
                "iroomcontrollerv2",
                "climatecontrollerus",
            }:
                climate_result = get_climate_live_values_for_control(item)
                values.extend(climate_result.get("items", []))
                errors.extend(climate_result.get("errors", []))
            else:
                value_result = get_control_live_value(item)
                if isinstance(value_result, dict) and value_result.get("status") == "ok":
                    values.append(value_result)
                else:
                    errors.append({
                        "uuid": item.get("uuid"),
                        "name": item.get("name"),
                        "error": value_result.get("message", "Unknown error") if isinstance(value_result, dict) else "Unknown error",
                    })
        except Exception as exc:
            errors.append({
                "uuid": item.get("uuid"),
                "name": item.get("name"),
                "error": str(exc),
            })

    return {
        "status": "ok",
        "room_name": result.get("room_name"),
        "domain": domain,
        "sensors_only": sensors_only,
        "count": len(values),
        "error_count": len(errors),
        "items": values,
        "errors": errors,
    }








def get_room_climate_summary(room_name: str):
    result = get_controls_by_room(room_name, domain="climate")
    items = result.get("items", []) if isinstance(result, dict) else []

    summary = {
        "status": "ok",
        "room_name": room_name,
        "temperature_actual": None,
        "temperature_target": None,
        "humidity": None,
        "co2": None,
        "operating_mode": None,
        "open_window": None,
        "items": [],
        "errors": [],
        "error_count": 0,
    }

    for item in items:
        if not isinstance(item, dict):
            summary["errors"].append({
                "error": f"Skipped non-dict climate item: {type(item).__name__}",
                "item": str(item),
            })
            continue

        live = get_climate_live_values_for_control(item)

        summary["items"].extend(live.get("items", []))
        summary["errors"].extend(live.get("errors", []))

        for row in live.get("items", []):
            metric = row.get("metric")
            value = row.get("value")

            if metric == "temperature_actual" and summary["temperature_actual"] is None:
                summary["temperature_actual"] = value
            elif metric == "temperature_target" and summary["temperature_target"] is None:
                summary["temperature_target"] = value
            elif metric == "humidity" and summary["humidity"] is None:
                summary["humidity"] = value
            elif metric == "co2" and summary["co2"] is None:
                summary["co2"] = value
            elif metric == "operating_mode" and summary["operating_mode"] is None:
                summary["operating_mode"] = value
            elif metric == "open_window" and summary["open_window"] is None:
                summary["open_window"] = value

    summary["error_count"] = len(summary["errors"])
    return summary








def get_all_live_values(domain: str | None = None, sensors_only: bool = True):
    items = get_all_controls()

    if domain:
        domain = _normalize_text(domain)
        items = [item for item in items if _normalize_text(item.get("domain")) == domain]

    if sensors_only:
        items = [item for item in items if item.get("readable")]

    values = []
    errors = []

    for item in items:
        if not item.get("readable"):
            continue

        try:
            if str(item.get("domain") or "").lower() == "climate" and str(item.get("type") or "").lower() in {
                "iroomcontrollerv2",
                "climatecontrollerus",
            }:
                climate_result = get_climate_live_values_for_control(item)
                values.extend(climate_result.get("items", []))
                errors.extend(climate_result.get("errors", []))
            else:
                values.append(get_control_live_value(item))
        except Exception as exc:
            errors.append({
                "uuid": item.get("uuid"),
                "name": item.get("name"),
                "error": str(exc),
            })

    return {
        "status": "ok",
        "domain": domain,
        "sensors_only": sensors_only,
        "count": len(values),
        "error_count": len(errors),
        "items": values,
        "errors": errors,
    }





# --------------------------------------------------
# SUMMARIES
# --------------------------------------------------

def get_loxone_structure_summary():
    data = fetch_loxapp3()

    rooms = data.get("rooms", {})
    cats = data.get("cats", {})
    controls = data.get("controls", {})

    classified = get_all_controls()
    domain_counts = {}
    sensor_type_counts = {}

    for item in classified:
        domain = item.get("domain") or "unknown"
        sensor_type = item.get("sensor_type") or "unknown"
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        sensor_type_counts[sensor_type] = sensor_type_counts.get(sensor_type, 0) + 1

    return {
        "status": "ok",
        "room_count": len(rooms),
        "category_count": len(cats),
        "control_count": len(controls),
        "rooms": sorted([r.get("name") for r in rooms.values() if r.get("name")]),
        "categories": sorted([c.get("name") for c in cats.values() if c.get("name")]),
        "domain_counts": dict(sorted(domain_counts.items())),
        "sensor_type_counts": dict(sorted(sensor_type_counts.items())),
    }


def get_room_temperature(room_name: str):
    room_name = resolve_room_name(room_name)
    room_values = get_live_values_by_room(room_name, sensors_only=True).get("items", [])

    temp_candidates = [
        item for item in room_values
        if item.get("sensor_type") == "temperature"
    ]

    if not temp_candidates:
        return {
            "status": "error",
            "room_name": room_name,
            "message": "No readable temperature value found for this room",
        }

    best = temp_candidates[0]
    return {
        "status": "ok",
        "room_name": room_name,
        "temperature": best.get("value"),
        "unit": best.get("unit") or "C",
        "source": {
            "uuid": best.get("uuid"),
            "name": best.get("name"),
            "state_key": best.get("state_key"),
        }
    }




def get_room_summary(room_name: str):
    room_name = resolve_room_name(room_name)
    controls = get_controls_by_room(room_name).get("items", [])

    grouped = {}
    for item in controls:
        domain = item.get("domain") or "unknown"
        grouped.setdefault(domain, []).append(item.get("name"))

    return {
        "status": "ok",
        "room_name": room_name,
        "groups": {k: sorted(v) for k, v in sorted(grouped.items())},
        "counts": {k: len(v) for k, v in sorted(grouped.items())},
    }


# --------------------------------------------------
# AUDIO / LIGHTING COMPATIBILITY HELPERS
# --------------------------------------------------

def get_audio_tool_targets():
    return {
        "living": {
            "node_power_room": "Living",
            "speaker_targets": {
                "living": {"room": "livingroom", "control_name": "picore_livingroute_switch"},
                "bass": {"room": "Living", "control_name": "AUDIO BASS"},
            },
            "party": {
                "room": "Living",
                "on_control": "Party ON",
                "off_control": "Party OFF",
            },
        },
        "bathroom": {
            "node_power_room": "Badkamer",
            "playback": {
                "room": "Badkamer",
                "on_control": "bathroom music ON",
                "off_control": "bathroom music OFF",
            },
        },
        "toilet": {
            "node_power_room": "WC",
            "speaker_targets": {
                "wc": {"room": "WC", "control_name": "AUDIO WC MANUAL"},
            },
        },
    }


def find_control_by_name(room_name: str, control_name: str):
    room_name = resolve_room_name(room_name)
    controls = get_controls_by_room(room_name).get("items", [])
    wanted = str(control_name or "").strip().lower()

    for item in controls:
        raw_name = str(item.get("name") or "").strip()
        raw_name_l = raw_name.lower()

        # Exact full-name match
        if raw_name_l == wanted:
            return {
                "status": "ok",
                "room_name": room_name,
                "control": item,
            }

        # Match normalized base name before any appended description
        base_name = raw_name.split("=", 1)[0].strip().lower()
        if base_name == wanted:
            return {
                "status": "ok",
                "room_name": room_name,
                "control": item,
            }

    return {
        "status": "error",
        "room_name": room_name,
        "message": f"Control not found: {control_name}",
    }

def get_audio_controls_by_room(room_name: str):
    return get_controls_by_room(room_name, domain="audio")


def get_lighting_controls_by_room(room_name: str):
    return get_controls_by_room(room_name, domain="lighting")


def get_best_audio_control_candidates(room_name: str):
    room_name = resolve_room_name(room_name)
    controls = get_audio_controls_by_room(room_name).get("items", [])

    playback_on = []
    playback_off = []
    power_on = []
    power_off = []
    schedules = []
    other = []

    for item in controls:
        name = str(item.get("name") or "")
        name_l = name.lower()

        score = 0
        if "music" in name_l:
            score += 3
        if "picore" in name_l:
            score += 3
        if room_name.lower() in name_l:
            score += 2

        enriched = {
            "uuid": item.get("uuid"),
            "name": item.get("name"),
            "type": item.get("type"),
            "score": score,
            "states": item.get("states", {}),
            "domain": item.get("domain"),
            "sensor_type": item.get("sensor_type"),
        }

        is_picore_power = "picore" in name_l
        is_music_playback = "music" in name_l and "schedule" not in name_l
        is_schedule = "schedule" in name_l or item.get("type") == "Daytimer"

        if is_schedule:
            schedules.append(enriched)
        elif is_picore_power:
            if name_l.endswith("_on") or name_l.endswith(" on"):
                power_on.append(enriched)
            elif name_l.endswith("_off") or name_l.endswith(" off"):
                power_off.append(enriched)
            else:
                other.append(enriched)
        elif is_music_playback:
            if name_l.endswith("_on") or name_l.endswith(" on"):
                playback_on.append(enriched)
            elif name_l.endswith("_off") or name_l.endswith(" off"):
                playback_off.append(enriched)
            else:
                other.append(enriched)
        else:
            other.append(enriched)

    for bucket in [playback_on, playback_off, power_on, power_off, schedules, other]:
        bucket.sort(key=lambda x: (-x["score"], x["name"] or ""))

    return {
        "status": "ok",
        "room_name": room_name,
        "playback_on_candidates": playback_on,
        "playback_off_candidates": playback_off,
        "power_on_candidates": power_on,
        "power_off_candidates": power_off,
        "schedule_candidates": schedules,
        "other": other,
    }


def get_audio_action_map(room_name: str):
    room_name = resolve_room_name(room_name)
    controls = get_audio_controls_by_room(room_name).get("items", [])

    result = {
        "status": "ok",
        "room_name": room_name,
        "node_power": {},
        "speaker_routes": [],
        "party": {},
        "playback": {},
        "schedule": [],
        "other": [],
        "notes": [],
    }

    for item in controls:
        name = str(item.get("name") or "")
        name_l = name.lower()
        typ = str(item.get("type") or "").lower()

        simplified = {
            "uuid": item.get("uuid"),
            "name": item.get("name"),
            "type": item.get("type"),
            "states": item.get("states", {}),
            "domain": item.get("domain"),
            "sensor_type": item.get("sensor_type"),
        }

        if "picore" in name_l or "rpicore" in name_l:
            if typ == "switch":
                result["node_power"][name] = {
                    "mode": "single_switch",
                    "switch": simplified,
                    "state_uuid": (item.get("states") or {}).get("active"),
                }
            elif name_l.endswith("_on") or name_l.endswith(" on"):
                result["node_power"].setdefault("paired_buttons", {})["on"] = simplified
            elif name_l.endswith("_off") or name_l.endswith(" off"):
                result["node_power"].setdefault("paired_buttons", {})["off"] = simplified
            else:
                result["node_power"][name] = simplified
            continue

        if name_l.startswith("audio "):
            target = name[6:].strip() if len(name) > 6 else name
            result["speaker_routes"].append({
                "target": target,
                "role": "speaker_route",
                "mode": "single_switch" if typ == "switch" else "unknown",
                **simplified,
            })
            continue

        if name_l.startswith("party "):
            if name_l.endswith(" on"):
                result["party"]["on"] = simplified
            elif name_l.endswith(" off"):
                result["party"]["off"] = simplified
            else:
                result["party"].setdefault("other", []).append(simplified)
            continue

        if "music" in name_l:
            if name_l.endswith("_on") or name_l.endswith(" on"):
                result["playback"]["on"] = simplified
            elif name_l.endswith("_off") or name_l.endswith(" off"):
                result["playback"]["off"] = simplified
            else:
                result["playback"].setdefault("other", []).append(simplified)
            continue

        if "schedule" in name_l or typ == "daytimer":
            result["schedule"].append(simplified)
            continue

        result["other"].append(simplified)

    if not result["node_power"]:
        result["notes"].append("No PiCore node power control detected.")
    if not result["speaker_routes"]:
        result["notes"].append("No speaker route controls detected.")
    if not result["party"]:
        result["notes"].append("No party controls detected.")
    if not result["playback"]:
        result["notes"].append("No direct music playback controls detected.")

    return result


def get_audio_behavior_map(room_name: str):
    room_name = resolve_room_name(room_name)
    controls = get_audio_controls_by_room(room_name).get("items", [])

    result = {
        "status": "ok",
        "room_name": room_name,
        "node_power": [],
        "speaker_enable": [],
        "speaker_disable": [],
        "play_modes": [],
        "stop_actions": [],
        "party": [],
        "other_audio": [],
        "notes": [],
    }

    for item in controls:
        name = str(item.get("name") or "")
        name_l = name.lower()

        simplified = {
            "uuid": item.get("uuid"),
            "name": item.get("name"),
            "type": item.get("type"),
            "states": item.get("states", {}),
            "domain": item.get("domain"),
            "sensor_type": item.get("sensor_type"),
        }

        if "picore" in name_l or "rpicore" in name_l:
            result["node_power"].append(simplified)
            continue
        if "enable music" in name_l or name_l.startswith("audio "):
            result["speaker_enable"].append(simplified)
            continue
        if "disable music" in name_l:
            result["speaker_disable"].append(simplified)
            continue
        if "night" in name_l or "normal" in name_l:
            result["play_modes"].append(simplified)
            continue
        if "stop" in name_l:
            result["stop_actions"].append(simplified)
            continue
        if name_l.startswith("party "):
            result["party"].append(simplified)
            continue

        result["other_audio"].append(simplified)

    if not result["node_power"]:
        result["notes"].append("No node power control detected.")

    return result




def _climate_metric_map():
    return {
        "tempActual": {"metric": "temperature_actual", "unit": "C"},
        "tempTarget": {"metric": "temperature_target", "unit": "C"},
        "comfortTemperature": {"metric": "comfort_temperature", "unit": "C"},
        "humidityActual": {"metric": "humidity", "unit": "%"},
        "humidity": {"metric": "humidity", "unit": "%"},
        "co2": {"metric": "co2", "unit": "ppm"},
        "operatingMode": {"metric": "operating_mode", "unit": None},
        "currentMode": {"metric": "current_mode", "unit": None},
        "activeMode": {"metric": "active_mode", "unit": None},
        "openWindow": {"metric": "open_window", "unit": None},
        "actualOutdoorTemp": {"metric": "outdoor_temperature", "unit": "C"},
        "averageOutdoorTemp": {"metric": "outdoor_temperature_avg", "unit": "C"},
        "shadingOut": {"metric": "shading_out", "unit": None},
    }




def get_climate_live_values_for_control(item):
    if not isinstance(item, dict):
        return {
            "status": "error",
            "room_name": None,
            "uuid": None,
            "name": str(item),
            "count": 0,
            "error_count": 1,
            "items": [],
            "errors": [
                {
                    "error": f"Expected dict climate control item, got {type(item).__name__}",
                    "item": str(item),
                }
            ],
        }

    states = item.get("states", {}) or {}

    preferred_keys = [
        "tempActual",
        "tempTarget",
        "comfortTemperature",
        "comfortTemperatureCool",
        "comfortTolerance",
        "co2",
        "humidityActual",
        "humidity",
        "actualOutdoorTemp",
        "averageOutdoorTemp",
        "currentMode",
        "activeMode",
        "operatingMode",
        "openWindow",
        "shadingOut",
        "demandHeat",
        "demandCool",
        "mode",
        "currentStatus",
        "stage",
        "threshold",
        "fan",
        "excessEnergy",
        "minimumTempCooling",
        "maximumTempHeating",
    ]

    values = []
    errors = []
    seen_state_uuids = set()

    for state_key in preferred_keys:
        state_uuid = states.get(state_key)
        if not state_uuid:
            continue

        state_uuid_l = str(state_uuid).lower()
        if state_uuid_l in seen_state_uuids:
            continue
        seen_state_uuids.add(state_uuid_l)

        state_result = _get_state_value_with_ws_fallback(state_uuid)
        metric = _metric_from_climate_state_key(state_key)

        if state_result.get("status") == "ok":
            values.append({
                "uuid": item.get("uuid"),
                "name": item.get("name"),
                "type": item.get("type"),
                "room_name": item.get("room_name"),
                "domain": item.get("domain"),
                "sensor_type": item.get("sensor_type"),
                "state_key": state_key,
                "state_uuid": state_uuid,
                "metric": metric,
                "value": state_result.get("value"),
                "source": state_result.get("source", "unknown"),
            })
        else:
            errors.append({
                "uuid": item.get("uuid"),
                "name": item.get("name"),
                "room_name": item.get("room_name"),
                "state_key": state_key,
                "state_uuid": state_uuid,
                "error": state_result.get("error", "Unknown error"),
            })

    return {
        "status": "ok",
        "room_name": item.get("room_name"),
        "uuid": item.get("uuid"),
        "name": item.get("name"),
        "count": len(values),
        "error_count": len(errors),
        "items": values,
        "errors": errors,
    }






def get_house_state_summary():
    structure = get_loxone_structure_summary()

    room_names = structure.get("rooms", []) or []

    room_summaries = []
    errors = []

    for room_name in room_names:
        try:
            climate = get_room_climate_summary(room_name)
            room_summary = get_room_summary(room_name)

            room_summaries.append({
                "room_name": room_name,
                "climate": climate if isinstance(climate, dict) else {},
                "summary": room_summary if isinstance(room_summary, dict) else {},
            })
        except Exception as exc:
            errors.append({
                "room_name": room_name,
                "error": str(exc),
            })

    return {
        "status": "ok",
        "room_count": len(room_summaries),
        "rooms": room_summaries,
        "error_count": len(errors),
        "errors": errors,
    }
