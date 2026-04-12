import re
import requests

from router_logic import gather_house_data
from ollama_client import ask_ollama

from config import (
    PRICE_INFLUX_BUCKET,
    PRICE_INFLUX_MEASUREMENT,
    PRICE_INFLUX_FIELD,
)

from extensions import crypto_tools, tool_registry, experimental_tool_registry
from services.experimental_tool_matcher import find_best_experimental_tool_match
from services.experimental_approval_service import (
    parse_experimental_approval_question,
    execute_experimental_approval,
)
from services.sma_service import get_sma_summary_data
from services.influx_helpers import iso_now, query_latest_for_fields
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
from services.intent_detection import enrich_intents
from services.agent_crypto import build_crypto_direct_response
from services.agent_house import build_house_direct_response


def _has_production_tool(tool_name: str) -> bool:
    try:
        return tool_registry.get(tool_name) is not None
    except Exception:
        return False


def _has_experimental_tool(tool_name: str) -> bool:
    try:
        return experimental_tool_registry.get(tool_name) is not None
    except Exception:
        return False


def get_local_energy_summary_data():
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


def handle_agent_question(question: str):
    approval_request = parse_experimental_approval_question(question)
    if approval_request is not None:
        if not approval_request.get("ok"):
            return {
                "status": "approval_required",
                "mode": "experimental_approval_missing_data",
                "intents": ["experimental_tool_approval"],
                "used_tools": [],
                "tool_data": {},
                "answer": approval_request.get("error", "Experimental approval request is incomplete."),
            }

        approval_result = execute_experimental_approval(
            tool_name=approval_request["tool_name"],
            args=approval_request.get("args", {}),
            admin_password=approval_request["admin_password"],
        )

        if not approval_result.get("ok"):
            return {
                "status": "error",
                "mode": "experimental_approval_error",
                "intents": ["experimental_tool_approval"],
                "used_tools": [],
                "tool_data": {},
                "answer": f"Experimental tool approval failed: {approval_result.get('error')}",
            }

        payload = approval_result.get("payload", {}) or {}
        result = payload.get("result", {}) or {}

        return {
            "status": "ok",
            "mode": "experimental_tool_executed",
            "intents": ["experimental_tool_approval"],
            "used_tools": [approval_request["tool_name"]],
            "tool_data": {
                approval_request["tool_name"]: result.get("data", result),
            },
            "answer": result.get(
                "answer",
                f"Experimental tool {approval_request['tool_name']} executed successfully.",
            ),
        }

    gathered = gather_house_data(question)
    intents = gathered["intents"]
    tool_data = gathered["data"]

    q_lower = question.lower()

    # Normalize network scan intent interpretation
    if any(x in q_lower for x in [
        "scan my network",
        "scan network",
        "network scan",
        "ping sweep",
        "which devices are alive",
        "what devices are alive",
        "who is online",
        "who is on my network",
        "scan my lan",
        "scan 192.168.",
        "alive hosts",
    ]):
        if "AI_gen_network_scan" not in intents:
            intents.append("AI_gen_network_scan")

    # Normalize Buderus / boiler intent interpretation
    if "buderus" in q_lower or "boiler" in q_lower or "heating" in q_lower:
        if (
            "boiler health" in q_lower
            or "boiler health summary" in q_lower
            or "is the boiler healthy" in q_lower
            or "boiler summary" in q_lower
        ):
            if "buderus_boiler_health_summary" not in intents:
                intents.append("buderus_boiler_health_summary")

        elif "pressure" in q_lower or "system pressure" in q_lower or "boiler pressure" in q_lower:
            if "buderus_pressure_analysis" not in intents:
                intents.append("buderus_pressure_analysis")

        elif "error code" in q_lower or "fault" in q_lower or "diagnostic" in q_lower or "service code" in q_lower or "maintenance" in q_lower:
            if "buderus_diagnostics" not in intents:
                intents.append("buderus_diagnostics")

        elif "hot water" in q_lower or "tap water" in q_lower or "dhw" in q_lower or "warm water" in q_lower:
            if "buderus_hot_water_status" not in intents:
                intents.append("buderus_hot_water_status")

        elif "heating active" in q_lower or "is heating running" in q_lower or "central heating" in q_lower or "radiator heating" in q_lower or "heating circuit" in q_lower:
            if "buderus_heating_status" not in intents:
                intents.append("buderus_heating_status")

        elif "buderus status" in q_lower or "boiler status" in q_lower or "heating status now" in q_lower or "boiler now" in q_lower or "current buderus" in q_lower:
            if "buderus_current_status" not in intents:
                intents.append("buderus_current_status")

    # Normalize APC / UPS intent interpretation
    if "ups" in q_lower or "apc" in q_lower or "battery backup" in q_lower:
        if (
            "on battery" in q_lower
            or "running on battery" in q_lower
            or "is my ups on battery" in q_lower
        ):
            if "apc_on_battery_status" not in intents:
                intents.append("apc_on_battery_status")

        elif (
            "highest load" in q_lower
            or "most load" in q_lower
            or "highest usage" in q_lower
            or "most heavily loaded" in q_lower
        ):
            if "apc_highest_load" not in intents:
                intents.append("apc_highest_load")

        elif (
            "battery health" in q_lower
            or "battery condition" in q_lower
            or "battery status" in q_lower
            or "healthy is my ups battery" in q_lower
            or "health of my ups battery" in q_lower
            or "how healthy is my ups battery" in q_lower
        ):
            if "apc_battery_health" not in intents:
                intents.append("apc_battery_health")

        elif (
            "lowest runtime" in q_lower
            or "least runtime" in q_lower
            or "shortest runtime" in q_lower
            or "weakest runtime" in q_lower
        ):
            if "apc_lowest_runtime" not in intents:
                intents.append("apc_lowest_runtime")

        elif "summary" in q_lower or "overview" in q_lower:
            if "apc_summary" not in intents:
                intents.append("apc_summary")

    # Normalize crypto single-coin summary questions
    crypto_symbols = [
        "XRP", "BTC", "ETH", "ADA", "DOGE", "SOL", "DOT", "LINK", "AVAX",
        "TAO", "SUI", "WLD", "BONK", "SHIB", "CHZ", "DGB", "AZTEC",
        "BANANA", "ZRO", "AERO", "APE", "AUDIO", "AXS", "CATI", "DIA",
        "HONEY", "ICX", "JASMY", "KAVA", "LRC", "MASK", "MOODENG",
        "PYTH", "RAY", "SAND", "T", "TLM", "W", "ZETA"
    ]

    crypto_summary_words = [
        "summary", "position", "holding", "coin", "token", "bag",
        "worth", "value", "amount", "price"
    ]

    matched_symbol = None
    for sym in crypto_symbols:
        if f" {sym.lower()} " in f" {q_lower} ":
            matched_symbol = sym
            break

    if matched_symbol is not None:
        if any(word in q_lower for word in crypto_summary_words):
            if "crypto_coin_summary" not in intents:
                intents.append("crypto_coin_summary")

    # Normalize electricity cost questions
    cost_words = ["cost", "costs", "spent", "pay", "paid", "kost", "gekost", "betaald"]
    has_cost_word = any(word in q_lower for word in cost_words)

    if has_cost_word:
        if "last 24 hours" in q_lower or "last 24h" in q_lower or "24 hours" in q_lower or "24h" in q_lower:
            if "electricity_cost_last_24h" not in intents:
                intents.append("electricity_cost_last_24h")
        elif "today" in q_lower or "vandaag" in q_lower:
            if "electricity_cost_today" not in intents:
                intents.append("electricity_cost_today")

        intents = [intent for intent in intents if intent != "electricity_price_now"]

    enriched = enrich_intents(question, intents, tool_data)
    q = enriched["question_lower"]
    symbol = enriched["symbol"]

    if not symbol and "matched_symbol" in locals() and matched_symbol is not None:
        symbol = matched_symbol

    is_crypto_question = enriched["is_crypto_question"]
    is_power_question = enriched["is_power_question"]
    intents = enriched["intents"]
    tool_data = enriched["tool_data"]

    # Production-first AI-generated network scan
    if "AI_gen_network_scan" in intents and "AI_gen_network_scan" not in tool_data:
        try:
            target = None

            cidr_match = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})\b", question)
            ip_match = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", question)

            if cidr_match:
                target = cidr_match.group(1)
            elif ip_match:
                target = ip_match.group(1)

            scan_args = {}
            if target:
                scan_args["target"] = target

            if _has_production_tool("AI_gen_network_scan"):
                scan_tool_result = tool_registry.execute("AI_gen_network_scan", scan_args)
                tool_data["AI_gen_network_scan"] = scan_tool_result["data"]

        except Exception as e:
            tool_data["AI_gen_network_scan"] = {"error": str(e)}

    # Registry-backed SMA tool
    if "sma_production_overview" in intents and "sma_production_overview" not in tool_data:
        try:
            sma_tool_result = tool_registry.execute("get_sma_overview")
            tool_data["sma_production_overview"] = sma_tool_result["data"]
        except Exception as e:
            tool_data["sma_production_overview"] = {"error": str(e)}

    # Registry-backed Pdata tools
    if "energy_summary" in intents and "energy_summary" not in tool_data:
        try:
            pdata_tool_result = tool_registry.execute("get_pdata_energy_summary")
            tool_data["energy_summary"] = pdata_tool_result["data"]
        except Exception as e:
            tool_data["energy_summary"] = {"error": str(e)}

    if "compare_energy" in intents and "compare_energy" not in tool_data:
        try:
            pdata_tool_result = tool_registry.execute("get_pdata_compare_energy")
            tool_data["compare_energy"] = pdata_tool_result["data"]
        except Exception as e:
            tool_data["compare_energy"] = {"error": str(e)}

    if "pdata_all_fields" in intents and "pdata_all_fields" not in tool_data:
        try:
            pdata_tool_result = tool_registry.execute("get_pdata_all_fields")
            tool_data["pdata_all_fields"] = pdata_tool_result["data"]
        except Exception as e:
            tool_data["pdata_all_fields"] = {"error": str(e)}

    if "pdata_full_overview" in intents and "pdata_full_overview" not in tool_data:
        try:
            pdata_tool_result = tool_registry.execute("get_pdata_full_overview")
            tool_data["pdata_full_overview"] = pdata_tool_result["data"]
        except Exception as e:
            tool_data["pdata_full_overview"] = {"error": str(e)}

    if "gas_summary" in intents and "gas_summary" not in tool_data:
        try:
            pdata_tool_result = tool_registry.execute("get_pdata_gas_summary")
            tool_data["gas_summary"] = pdata_tool_result["data"]
        except Exception as e:
            tool_data["gas_summary"] = {"error": str(e)}

    # Keep existing non-registry SMA summary path for now
    if "sma_summary" in intents and "sma_summary" not in tool_data:
        try:
            tool_data["sma_summary"] = get_sma_summary_data()
        except Exception as e:
            tool_data["sma_summary"] = {"error": str(e)}

    # Registry-backed water tools
    if "salt_tank_level" in intents and "salt_tank_level" not in tool_data:
        try:
            water_tool_result = tool_registry.execute("get_salt_tank_level")
            tool_data["salt_tank_level"] = water_tool_result["data"]
        except Exception as e:
            tool_data["salt_tank_level"] = {"error": str(e)}

    if "water_temperatures" in intents and "water_temperatures" not in tool_data:
        try:
            water_tool_result = tool_registry.execute("get_water_temperature_summary")
            tool_data["water_temperatures"] = water_tool_result["data"]
        except Exception as e:
            tool_data["water_temperatures"] = {"error": str(e)}

    if "water_softener_overview" in intents and "water_softener_overview" not in tool_data:
        try:
            water_tool_result = tool_registry.execute("get_water_softener_overview")
            tool_data["water_softener_overview"] = water_tool_result["data"]
        except Exception as e:
            tool_data["water_softener_overview"] = {"error": str(e)}

    # Registry-backed price tools
    if "latest_price" in intents and "latest_price" not in tool_data:
        try:
            price_tool_result = tool_registry.execute("get_latest_price")
            tool_data["latest_price"] = price_tool_result["data"]
        except Exception as e:
            tool_data["latest_price"] = {"error": str(e)}

    if "electricity_cost_today" in intents and "electricity_cost_today" not in tool_data:
        try:
            price_tool_result = tool_registry.execute("get_electricity_cost_today")
            tool_data["electricity_cost_today"] = price_tool_result["data"]
        except Exception as e:
            tool_data["electricity_cost_today"] = {"error": str(e)}

    if "electricity_cost_last_24h" in intents and "electricity_cost_last_24h" not in tool_data:
        try:
            price_tool_result = tool_registry.execute("get_electricity_cost_last_24h")
            tool_data["electricity_cost_last_24h"] = price_tool_result["data"]
        except Exception as e:
            tool_data["electricity_cost_last_24h"] = {"error": str(e)}

    if "cheapest_hours_today" in intents and "cheapest_hours_today" not in tool_data:
        try:
            price_tool_result = tool_registry.execute("get_cheapest_hours_today")
            tool_data["cheapest_hours_today"] = price_tool_result["data"]
        except Exception as e:
            tool_data["cheapest_hours_today"] = {"error": str(e)}

    # Direct price returns
    if "electricity_cost_today" in intents and "electricity_cost_today" in tool_data:
        data = tool_data["electricity_cost_today"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["electricity_cost_today"],
            "tool_data": {"electricity_cost_today": data},
            "answer": (
                f"Electricity cost today is {data.get('total_cost_eur', 'unknown')} EUR "
                f"for {data.get('total_import_kwh', 'unknown')} kWh imported."
            ),
        }

    if "electricity_cost_last_24h" in intents and "electricity_cost_last_24h" in tool_data:
        data = tool_data["electricity_cost_last_24h"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["electricity_cost_last_24h"],
            "tool_data": {"electricity_cost_last_24h": data},
            "answer": (
                f"Electricity cost over the last 24 hours is {data.get('total_cost_eur', 'unknown')} EUR "
                f"for {data.get('total_import_kwh', 'unknown')} kWh imported."
            ),
        }

    # Registry-backed APC tools
    if "apc_summary" in intents and "apc_summary" not in tool_data:
        try:
            apc_tool_result = tool_registry.execute("get_apc_summary")
            tool_data["apc_summary"] = apc_tool_result["data"]
        except Exception as e:
            tool_data["apc_summary"] = {"error": str(e)}

    if "apc_on_battery_status" in intents and "apc_on_battery_status" not in tool_data:
        try:
            apc_tool_result = tool_registry.execute("get_apc_on_battery_status")
            tool_data["apc_on_battery_status"] = apc_tool_result["data"]
        except Exception as e:
            tool_data["apc_on_battery_status"] = {"error": str(e)}

    if "apc_highest_load" in intents and "apc_highest_load" not in tool_data:
        try:
            apc_tool_result = tool_registry.execute("get_apc_highest_load")
            tool_data["apc_highest_load"] = apc_tool_result["data"]
        except Exception as e:
            tool_data["apc_highest_load"] = {"error": str(e)}

    if "apc_battery_health" in intents and "apc_battery_health" not in tool_data:
        try:
            apc_tool_result = tool_registry.execute("get_apc_battery_health")
            tool_data["apc_battery_health"] = apc_tool_result["data"]
        except Exception as e:
            tool_data["apc_battery_health"] = {"error": str(e)}

    if "apc_lowest_runtime" in intents and "apc_lowest_runtime" not in tool_data:
        try:
            apc_tool_result = tool_registry.execute("get_apc_lowest_runtime")
            tool_data["apc_lowest_runtime"] = apc_tool_result["data"]
        except Exception as e:
            tool_data["apc_lowest_runtime"] = {"error": str(e)}

    # Direct APC returns
    if "apc_on_battery_status" in intents and "apc_on_battery_status" in tool_data:
        data = tool_data["apc_on_battery_status"]
        answer = data.get("answer") or "APC on-battery status is available."
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["apc_on_battery_status"],
            "tool_data": {"apc_on_battery_status": data},
            "answer": answer,
        }

    if "apc_highest_load" in intents and "apc_highest_load" in tool_data:
        data = tool_data["apc_highest_load"]
        answer = data.get("answer") or "APC highest-load summary is available."
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["apc_highest_load"],
            "tool_data": {"apc_highest_load": data},
            "answer": answer,
        }

    if "apc_battery_health" in intents and "apc_battery_health" in tool_data:
        data = tool_data["apc_battery_health"]
        answer = data.get("answer") or "APC battery health summary is available."
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["apc_battery_health"],
            "tool_data": {"apc_battery_health": data},
            "answer": answer,
        }

    if "apc_lowest_runtime" in intents and "apc_lowest_runtime" in tool_data:
        data = tool_data["apc_lowest_runtime"]
        answer = data.get("answer") or "APC runtime summary is available."
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["apc_lowest_runtime"],
            "tool_data": {"apc_lowest_runtime": data},
            "answer": answer,
        }

    if "apc_summary" in intents and "apc_summary" in tool_data:
        data = tool_data["apc_summary"]
        answer = data.get("answer") or "APC UPS summary is available."
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["apc_summary"],
            "tool_data": {"apc_summary": data},
            "answer": answer,
        }

    # Registry-backed Buderus tools
    if "buderus_current_status" in intents and "buderus_current_status" not in tool_data:
        try:
            buderus_tool_result = tool_registry.execute("get_buderus_current_status")
            tool_data["buderus_current_status"] = buderus_tool_result["data"]
        except Exception as e:
            tool_data["buderus_current_status"] = {"error": str(e)}

    if "buderus_heating_status" in intents and "buderus_heating_status" not in tool_data:
        try:
            buderus_tool_result = tool_registry.execute("get_buderus_heating_status")
            tool_data["buderus_heating_status"] = buderus_tool_result["data"]
        except Exception as e:
            tool_data["buderus_heating_status"] = {"error": str(e)}

    if "buderus_hot_water_status" in intents and "buderus_hot_water_status" not in tool_data:
        try:
            buderus_tool_result = tool_registry.execute("get_buderus_hot_water_status")
            tool_data["buderus_hot_water_status"] = buderus_tool_result["data"]
        except Exception as e:
            tool_data["buderus_hot_water_status"] = {"error": str(e)}

    if "buderus_pressure_analysis" in intents and "buderus_pressure_analysis" not in tool_data:
        try:
            buderus_tool_result = tool_registry.execute("get_buderus_pressure_analysis")
            tool_data["buderus_pressure_analysis"] = buderus_tool_result["data"]
        except Exception as e:
            tool_data["buderus_pressure_analysis"] = {"error": str(e)}

    if "buderus_diagnostics" in intents and "buderus_diagnostics" not in tool_data:
        try:
            buderus_tool_result = tool_registry.execute("get_buderus_diagnostics")
            tool_data["buderus_diagnostics"] = buderus_tool_result["data"]
        except Exception as e:
            tool_data["buderus_diagnostics"] = {"error": str(e)}

    if "buderus_boiler_health_summary" in intents and "buderus_boiler_health_summary" not in tool_data:
        try:
            buderus_tool_result = tool_registry.execute("get_buderus_boiler_health_summary")
            tool_data["buderus_boiler_health_summary"] = buderus_tool_result["data"]
        except Exception as e:
            tool_data["buderus_boiler_health_summary"] = {"error": str(e)}

    # Direct Buderus returns
    if "buderus_current_status" in intents and "buderus_current_status" in tool_data:
        data = tool_data["buderus_current_status"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["buderus_current_status"],
            "tool_data": {"buderus_current_status": data},
            "answer": data.get("answer", "Buderus current status is available."),
        }

    if "buderus_heating_status" in intents and "buderus_heating_status" in tool_data:
        data = tool_data["buderus_heating_status"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["buderus_heating_status"],
            "tool_data": {"buderus_heating_status": data},
            "answer": data.get("answer", "Buderus heating status is available."),
        }

    if "buderus_hot_water_status" in intents and "buderus_hot_water_status" in tool_data:
        data = tool_data["buderus_hot_water_status"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["buderus_hot_water_status"],
            "tool_data": {"buderus_hot_water_status": data},
            "answer": data.get("answer", "Buderus hot water status is available."),
        }

    if "buderus_pressure_analysis" in intents and "buderus_pressure_analysis" in tool_data:
        data = tool_data["buderus_pressure_analysis"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["buderus_pressure_analysis"],
            "tool_data": {"buderus_pressure_analysis": data},
            "answer": data.get("answer", "Buderus pressure analysis is available."),
        }

    if "buderus_diagnostics" in intents and "buderus_diagnostics" in tool_data:
        data = tool_data["buderus_diagnostics"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["buderus_diagnostics"],
            "tool_data": {"buderus_diagnostics": data},
            "answer": data.get("answer", "Buderus diagnostics are available."),
        }

    if "buderus_boiler_health_summary" in intents and "buderus_boiler_health_summary" in tool_data:
        data = tool_data["buderus_boiler_health_summary"]
        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["buderus_boiler_health_summary"],
            "tool_data": {"buderus_boiler_health_summary": data},
            "answer": data.get("answer", "Buderus boiler health summary is available."),
        }

    # Direct AI-generated network scan return
    if "AI_gen_network_scan" in intents and "AI_gen_network_scan" in tool_data:
        data = tool_data["AI_gen_network_scan"]

        if data.get("error"):
            answer = f"Network scan failed: {data['error']}"
        else:
            alive_count = data.get("alive_host_count", 0)
            target = data.get("target", "unknown target")
            hosts = data.get("alive_hosts", []) or []

            if hosts:
                preview = []
                for host in hosts[:8]:
                    hostname = host.get("hostname")
                    ip = host.get("ip")
                    if hostname:
                        preview.append(f"{hostname} ({ip})")
                    else:
                        preview.append(str(ip))

                preview_text = ", ".join(preview)

                if len(hosts) > 8:
                    preview_text += f", and {len(hosts) - 8} more"

                answer = (
                    f"Network scan completed for {target}. "
                    f"I found {alive_count} active hosts: {preview_text}."
                )
            else:
                answer = f"Network scan completed for {target}. No active hosts were found."

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["AI_gen_network_scan"],
            "tool_data": {"AI_gen_network_scan": data},
            "answer": answer,
        }

    if "crypto_portfolio_summary" in intents and "crypto_portfolio_summary" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute("get_crypto_portfolio_summary")
            tool_data["crypto_portfolio_summary"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_portfolio_summary"] = {"error": str(e)}

    if "crypto_daily_pnl_summary" in intents and "crypto_daily_pnl_summary" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute("get_crypto_daily_pnl_summary")
            tool_data["crypto_daily_pnl_summary"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_daily_pnl_summary"] = {"error": str(e)}

    if "crypto_top_movers_24h" in intents and "crypto_top_movers_24h" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute("get_crypto_top_movers_24h")
            tool_data["crypto_top_movers_24h"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_top_movers_24h"] = {"error": str(e)}

    if "crypto_concentration_risk" in intents and "crypto_concentration_risk" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute("get_crypto_concentration_risk")
            tool_data["crypto_concentration_risk"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_concentration_risk"] = {"error": str(e)}

    if "crypto_contributors_24h" in intents and "crypto_contributors_24h" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute("get_crypto_contributors_24h")
            tool_data["crypto_contributors_24h"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_contributors_24h"] = {"error": str(e)}

    if "crypto_portfolio_health" in intents and "crypto_portfolio_health" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute("get_crypto_portfolio_health")
            tool_data["crypto_portfolio_health"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_portfolio_health"] = {"error": str(e)}

    if "crypto_compare_now_vs_24h" in intents and "crypto_compare_now_vs_24h" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute("get_crypto_compare_now_vs_24h")
            tool_data["crypto_compare_now_vs_24h"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_compare_now_vs_24h"] = {"error": str(e)}

    if "crypto_coin_summary" in intents and symbol and "crypto_coin_summary" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute(
                "get_crypto_coin_summary",
                {"symbol": symbol},
            )
            tool_data["crypto_coin_summary"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_coin_summary"] = {"error": str(e)}

    if "crypto_drawdown_7d" in intents and "crypto_drawdown_7d" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute("get_crypto_drawdown_7d")
            tool_data["crypto_drawdown_7d"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_drawdown_7d"] = {"error": str(e)}

    if "crypto_compare_7d" in intents and "crypto_compare_7d" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute("get_crypto_compare_7d")
            tool_data["crypto_compare_7d"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_compare_7d"] = {"error": str(e)}

    if "crypto_stale_data_check" in intents and "crypto_stale_data_check" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute(
                "get_crypto_stale_data_check",
                {"stale_hours": 12},
            )
            tool_data["crypto_stale_data_check"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_stale_data_check"] = {"error": str(e)}

    if "crypto_excluding_symbol_summary" in intents and "crypto_excluding_symbol_summary" not in tool_data:
        try:
            crypto_tool_result = tool_registry.execute(
                "get_crypto_excluding_symbol_summary",
                {"exclude_symbol": "XRP"},
            )
            tool_data["crypto_excluding_symbol_summary"] = crypto_tool_result["data"]
        except Exception as e:
            tool_data["crypto_excluding_symbol_summary"] = {"error": str(e)}

    # Crypto tools
    if "crypto_coin_summary" in intents and symbol:
        try:
            tool_data["crypto_coin_summary"] = crypto_tools.get_coin_summary(symbol)
        except Exception as e:
            tool_data["crypto_coin_summary"] = {"error": str(e)}

    if "crypto_portfolio_summary" in intents:
        try:
            tool_data["crypto_portfolio_summary"] = crypto_tools.get_current_portfolio_summary()
        except Exception as e:
            tool_data["crypto_portfolio_summary"] = {"error": str(e)}

    if "crypto_portfolio_composition" in intents:
        try:
            tool_data["crypto_portfolio_composition"] = crypto_tools.get_portfolio_composition(top_n=5)
        except Exception as e:
            tool_data["crypto_portfolio_composition"] = {"error": str(e)}

    if "crypto_compare_now_vs_24h" in intents:
        try:
            tool_data["crypto_compare_now_vs_24h"] = crypto_tools.compare_portfolio_now_vs_24h()
        except Exception as e:
            tool_data["crypto_compare_now_vs_24h"] = {"error": str(e)}

    if "crypto_top_movers_24h" in intents:
        try:
            tool_data["crypto_top_movers_24h"] = crypto_tools.get_top_movers_24h()
        except Exception as e:
            tool_data["crypto_top_movers_24h"] = {"error": str(e)}

    if "crypto_concentration_risk" in intents:
        try:
            tool_data["crypto_concentration_risk"] = crypto_tools.get_concentration_risk()
        except Exception as e:
            tool_data["crypto_concentration_risk"] = {"error": str(e)}

    if "crypto_stale_data_check" in intents:
        try:
            tool_data["crypto_stale_data_check"] = crypto_tools.get_stale_data_check(stale_hours=12)
        except Exception as e:
            tool_data["crypto_stale_data_check"] = {"error": str(e)}

    if "crypto_daily_pnl_summary" in intents:
        try:
            tool_data["crypto_daily_pnl_summary"] = crypto_tools.get_daily_pnl_summary()
        except Exception as e:
            tool_data["crypto_daily_pnl_summary"] = {"error": str(e)}

    if "crypto_contributors_24h" in intents:
        try:
            tool_data["crypto_contributors_24h"] = crypto_tools.get_contributors_24h()
        except Exception as e:
            tool_data["crypto_contributors_24h"] = {"error": str(e)}

    if "crypto_portfolio_health" in intents:
        try:
            tool_data["crypto_portfolio_health"] = crypto_tools.get_portfolio_health()
        except Exception as e:
            tool_data["crypto_portfolio_health"] = {"error": str(e)}

    if "crypto_drawdown_7d" in intents:
        try:
            tool_data["crypto_drawdown_7d"] = crypto_tools.get_drawdown_7d()
        except Exception as e:
            tool_data["crypto_drawdown_7d"] = {"error": str(e)}

    if "crypto_compare_7d" in intents:
        try:
            tool_data["crypto_compare_7d"] = crypto_tools.get_compare_7d()
        except Exception as e:
            tool_data["crypto_compare_7d"] = {"error": str(e)}

    if "crypto_excluding_symbol_summary" in intents:
        try:
            tool_data["crypto_excluding_symbol_summary"] = crypto_tools.get_excluding_symbol_summary("XRP")
        except Exception as e:
            tool_data["crypto_excluding_symbol_summary"] = {"error": str(e)}

    crypto_response = build_crypto_direct_response(
        intents=intents,
        tool_data=tool_data,
        is_crypto_question=is_crypto_question,
        is_power_question=is_power_question,
    )
    if crypto_response is not None:
        return crypto_response

    try:
        house_response = build_house_direct_response(
            question=question,
            intents=intents,
            tool_data=tool_data,
        )
        if house_response is not None:
            return house_response
    except Exception as e:
        tool_data["house_direct_response_error"] = {"error": str(e)}

    experimental_match = find_best_experimental_tool_match(
        question=question,
        experimental_tool_registry=experimental_tool_registry,
    )

    if experimental_match is not None:
        tool_name = experimental_match["tool_name"]
        description = experimental_match["description"]

        if not _has_production_tool(tool_name):
            return {
                "status": "approval_required",
                "mode": "experimental_suggestion",
                "intents": intents,
                "used_tools": [],
                "tool_data": tool_data,
                "approval": {
                    "required": True,
                    "tool_name": tool_name,
                    "description": description,
                    "matched_tokens": experimental_match["matched_tokens"],
                    "execution_endpoint": "/experimental-tools/execute",
                    "approval_fields": [
                        "tool_name",
                        "args",
                        "approved",
                        "admin_password",
                    ],
                },
                "answer": (
                    f"I found an experimental tool that may help: {tool_name}. "
                    f"It is not approved for automatic execution. "
                    f"Approve execution?"
                ),
            }

    if tool_data:
        prompt = f"""
You are a smart home and portfolio monitoring assistant.

You must answer using only the provided structured tool data.
Do not invent values.
Do not estimate.
Do not mention external sources.
Be concise and practical.

Formatting rules:
- For crypto portfolio composition, show the top 5 holdings and combine the rest as "all others".
- For concentration, say "largest holding", "top 3 holdings", and "top 5 holdings".
- Do not say "top 1% holding" or "top 3% holdings".
- Mention the allocation percentages and the risk level clearly.
- For stale data, mention stale symbols and stale value total.
- For movers and contributors, list the most important 3 to 5 items.
- If a value is negative, describe it as a loss or decline.
- If a value is positive, describe it as a gain or increase.

Question:
{question}

Detected intents:
{intents}

Tool data:
{tool_data}

Return a direct answer for the user.
"""
        answer = ask_ollama(prompt)
        return {
            "status": "ok",
            "mode": "tool_first",
            "intents": intents,
            "used_tools": list(tool_data.keys()),
            "tool_data": tool_data,
            "answer": answer,
        }

    fallback_prompt = f"""
Answer the following user question as a helpful assistant.
No house tool matched this question, so answer normally and be honest about uncertainty.

Question:
{question}
"""
    answer = ask_ollama(fallback_prompt)

    return {
        "status": "ok",
        "mode": "fallback_model",
        "intents": intents,
        "used_tools": [],
        "tool_data": {},
        "answer": answer,
    }
