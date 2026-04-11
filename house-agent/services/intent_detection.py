import re


KNOWN_SYMBOLS = [
    "xrp",
    "ada",
    "doge",
    "shib",
    "chz",
    "dgb",
    "zro",
    "tao",
    "sui",
    "bonk",
    "banana",
    "lrc",
    "icx",
    "dia",
    "aero",
    "mask",
    "jasmy",
    "kava",
    "wld",
    "axs",
    "audio",
    "sand",
    "ray",
    "zeta",
    "tlm",
    "pyth",
    "ape",
    "cati",
    "honey",
    "aztec",
    "moodeng",
]

POWER_KEYWORDS = [
    "power",
    "electricity",
    "energy",
    "watt",
    "watts",
    "consumption",
    "usage",
    "load",
    "grid",
    "house load",
    "import",
    "export",
    "baseload",
]


def detect_symbol(question: str):
    q = question.lower()
    q_words = re.findall(r"\b[a-zA-Z0-9_]+\b", q)

    for symbol in KNOWN_SYMBOLS:
        if symbol in q_words:
            return symbol.upper()

    return None


def enrich_intents(question: str, intents: list[str], tool_data: dict):
    q = question.lower()
    symbol = detect_symbol(q)

    is_sma_summary_question = any(
        k in q
        for k in [
            "sma inverter",
            "sma summary",
            "sma status",
            "what does my sma inverter say",
            "what does my inverter say",
            "solar inverter status",
        ]
    )

    is_sma_production_overview_question = any(
        k in q
        for k in [
            "sma production overview",
            "production overview",
            "solar production overview",
            "give me my sma production overview",
            "give me my solar production overview",
            "how much has sma produced",
            "how much did sma produce today",
        ]
    )

    is_sma_question = any(
        k in q
        for k in [
            "sma",
            "inverter",
            "solar inverter",
            "sunny boy",
            "solar production",
            "solar produced",
            "pv voltage",
            "pv current",
            "inverter temperature",
            "inverter temp",
            "daily solar energy",
            "total solar energy",
        ]
    )

    is_sma_overview_question = any(
        k in q
        for k in [
            "sma overview",
            "sma summary",
            "solar inverter summary",
            "solar production summary",
            "give me sma data",
            "give me inverter data",
        ]
    )

    is_pdata_gas_question = any(
        k in q
        for k in [
            "gas reading",
            "gas readings",
            "gas meter",
            "gas summary",
            "gas obis",
            "pdata gas",
            "smart meter gas",
            "provider gas",
            "gas from pdata",
        ]
    )

    is_pdata_question = any(
        k in q
        for k in [
            "pdata",
            "provider meter",
            "utility meter",
            "smart meter",
            "obis",
            "compare meters",
            "compare my meter",
            "compare house meter with provider meter",
            "compare local meter with provider meter",
        ]
    )

    is_pdata_all_fields_question = any(
        k in q
        for k in [
            "all pdata fields",
            "all obis fields",
            "show all obis codes",
            "list all obis codes",
            "decode all obis codes",
            "all smart meter fields",
        ]
    )

    is_pdata_full_overview_question = any(
        k in q
        for k in [
            "pdata full overview",
            "smart meter full overview",
            "full obis overview",
            "provider meter full overview",
        ]
    )

    is_inlet_temp_question = any(
        k in q
        for k in [
            "main water inlet temperature",
            "main water inlet temp",
            "inlet water temperature",
            "inlet water temp",
            "water inlet temperature",
            "water inlet temp",
        ]
    )

    is_salt_tank_temp_question = any(
        k in q
        for k in [
            "salt tank water temperature",
            "salt tank water temp",
            "salt water tank temperature",
            "salt water tank temp",
            "water softener tank temperature",
            "water softener tank temp",
        ]
    )

    is_water_temp_question = any(
        k in q
        for k in [
            "water temperature",
            "water temp",
            "inlet water temperature",
            "main water inlet temperature",
            "salt tank temperature",
            "salt water tank temperature",
            "water sensor temperature",
            "water sensor temperatures",
        ]
    )

    is_salt_question = any(
        k in q
        for k in [
            "salt tank",
            "water softener salt",
            "softener salt",
            "salt level",
            "water softener level",
            "salt reservoir",
            "softener reservoir",
        ]
    )

    is_water_softener_overview_question = any(
        k in q
        for k in [
            "water softener overview",
            "water softener status",
            "water softener summary",
            "softener overview",
            "softener status",
            "softener summary",
            "how is my water softener doing",
            "give me a water softener status summary",
        ]
    )

    is_price_question = any(
        k in q
        for k in [
            "electricity price",
            "power price",
            "grid price",
            "eur/kwh",
            "euro/kwh",
            "price per kwh",
            "price now",
            "cheapest hours",
            "cheapest electricity",
            "cost today",
            "electricity cost",
            "power cost",
        ]
    )

    is_power_question = any(k in q for k in POWER_KEYWORDS)

    is_crypto_question = (
        "crypto" in q
        or "portfolio" in q
        or ("coin" in q and symbol is not None)
        or ("token" in q and symbol is not None)
        or "gainer" in q
        or "loser" in q
        or "mover" in q
        or "concentration" in q
        or "concentrated" in q
        or "diversif" in q
        or "drawdown" in q
        or "pnl" in q
        or "profit" in q
        or "loss" in q
        or "stale" in q
        or "contributor" in q
        or "excluding xrp" in q
        or "without xrp" in q
    )

    if is_crypto_question and not is_power_question:
        intents = [i for i in intents if i != "power_last_24h_summary"]
        tool_data.pop("power_last_24h_summary", None)

    if is_crypto_question:
        if "health" in q or "overall" in q or "portfolio health" in q:
            if "crypto_portfolio_health" not in intents:
                intents.append("crypto_portfolio_health")
        elif "top mover" in q or "top movers" in q or "gainer" in q or "loser" in q or "mover" in q:
            if "crypto_top_movers_24h" not in intents:
                intents.append("crypto_top_movers_24h")
        elif "concentration" in q or "concentrated" in q or "diversified" in q or "dominant" in q:
            if "crypto_concentration_risk" not in intents:
                intents.append("crypto_concentration_risk")
        elif "stale" in q or "old data" in q or "not updating" in q or "outdated" in q:
            if "crypto_stale_data_check" not in intents:
                intents.append("crypto_stale_data_check")
        elif "contributor" in q or "contributed" in q:
            if "crypto_contributors_24h" not in intents:
                intents.append("crypto_contributors_24h")
        elif "daily pnl" in q or "pnl" in q or "profit" in q or "loss" in q:
            if "crypto_daily_pnl_summary" not in intents:
                intents.append("crypto_daily_pnl_summary")
        elif "drawdown" in q:
            if "crypto_drawdown_7d" not in intents:
                intents.append("crypto_drawdown_7d")
        elif "7d" in q or "7 days" in q or "week" in q:
            if "crypto_compare_7d" not in intents:
                intents.append("crypto_compare_7d")
        elif "excluding xrp" in q or "without xrp" in q:
            if "crypto_excluding_symbol_summary" not in intents:
                intents.append("crypto_excluding_symbol_summary")
        elif "allocation" in q or "composition" in q or "breakdown" in q:
            if "crypto_portfolio_composition" not in intents:
                intents.append("crypto_portfolio_composition")
        elif "24h" in q or "yesterday" in q or "compare" in q:
            if "crypto_compare_now_vs_24h" not in intents:
                intents.append("crypto_compare_now_vs_24h")
        elif symbol is not None:
            if "crypto_coin_summary" not in intents:
                intents.append("crypto_coin_summary")
        else:
            if "crypto_portfolio_summary" not in intents:
                intents.append("crypto_portfolio_summary")

    if is_price_question:
        if "cheapest" in q:
            if "cheapest_hours_today" not in intents:
                intents.append("cheapest_hours_today")
        elif "last 24h" in q or "last 24 hours" in q:
            if "electricity_cost_last_24h" not in intents:
                intents.append("electricity_cost_last_24h")
        elif (
            "cost today" in q
            or "today cost" in q
            or "what did electricity cost today" in q
            or "how much did electricity cost today" in q
        ):
            if "electricity_cost_today" not in intents:
                intents.append("electricity_cost_today")
        else:
            if "electricity_price_now" not in intents:
                intents.append("electricity_price_now")

    if is_salt_question and "salt_tank_level" not in intents:
        intents.append("salt_tank_level")

    if is_water_temp_question and "water_temperatures" not in intents:
        intents.append("water_temperatures")

    if is_inlet_temp_question and "water_inlet_temperature" not in intents:
        intents.append("water_inlet_temperature")

    if is_salt_tank_temp_question and "salt_tank_water_temperature" not in intents:
        intents.append("salt_tank_water_temperature")

    if is_water_softener_overview_question and "water_softener_overview" not in intents:
        intents.append("water_softener_overview")

    if is_pdata_question:
        if "compare" in q:
            if "pdata_compare_energy" not in intents:
                intents.append("pdata_compare_energy")
        else:
            if "pdata_energy_summary" not in intents:
                intents.append("pdata_energy_summary")

    if is_pdata_all_fields_question and "pdata_all_fields" not in intents:
        intents.append("pdata_all_fields")

    if is_pdata_full_overview_question and "pdata_full_overview" not in intents:
        intents.append("pdata_full_overview")

    if is_pdata_gas_question and "pdata_gas_summary" not in intents:
        intents.append("pdata_gas_summary")

    if is_sma_overview_question:
        if "sma_production_overview" not in intents:
            intents.append("sma_production_overview")
    elif is_sma_question:
        if "sma_summary" not in intents:
            intents.append("sma_summary")

    if is_sma_production_overview_question:
        if "sma_production_overview" not in intents:
            intents.append("sma_production_overview")
    elif is_sma_summary_question:
        if "sma_summary" not in intents:
            intents.append("sma_summary")

    if "salt_tank_water_temperature" in intents:
        intents = [i for i in intents if i != "salt_tank_level"]
        tool_data.pop("salt_tank_level", None)

    if "water_inlet_temperature" in intents or "salt_tank_water_temperature" in intents:
        intents = [i for i in intents if i != "water_temperatures"]
        tool_data.pop("water_temperatures", None)

    if any(
        i in intents
        for i in [
            "electricity_price_now",
            "electricity_cost_today",
            "electricity_cost_last_24h",
            "cheapest_hours_today",
        ]
    ):
        intents = [
            i
            for i in intents
            if i
            not in {
                "power_now",
                "energy_today",
                "energy_yesterday",
                "energy_compare_today_yesterday",
                "power_last_24h_summary",
            }
        ]
        tool_data.pop("power_now", None)
        tool_data.pop("energy_today", None)
        tool_data.pop("energy_yesterday", None)
        tool_data.pop("energy_compare_today_yesterday", None)
        tool_data.pop("power_last_24h_summary", None)

    if "water_softener_overview" in intents:
        intents = [
            i
            for i in intents
            if i
            not in {
                "energy_summary",
                "power_now",
                "energy_today",
                "energy_yesterday",
                "energy_compare_today_yesterday",
            }
        ]
        tool_data.pop("energy_summary", None)
        tool_data.pop("power_now", None)
        tool_data.pop("energy_today", None)
        tool_data.pop("energy_yesterday", None)
        tool_data.pop("energy_compare_today_yesterday", None)

    if "pdata_gas_summary" in intents:
        intents = [i for i in intents if i != "pdata_energy_summary"]
        tool_data.pop("pdata_energy_summary", None)

    if "pdata_all_fields" in intents or "pdata_full_overview" in intents:
        intents = [i for i in intents if i != "pdata_energy_summary"]
        tool_data.pop("pdata_energy_summary", None)

    node_names = ["house-ai-server", "voice-node-1", "audio-node-1", "aux-node-1", "feedback-node"]

    matched_node = None
    for node_name in node_names:
        if node_name in q:
            matched_node = node_name
            break

    asks_node_overview = (
        ("node" in q or "nodes" in q)
        and any(word in q for word in ["doing", "health", "status", "overview", "ok", "alive"])
    )

    asks_node_detail = (
        matched_node is not None
        and any(word in q for word in ["status", "health", "overloaded", "busy", "load", "ram", "cpu"])
    )

    if asks_node_overview:
        if "node_health_overview" not in intents:
            intents.append("node_health_overview")

    if asks_node_detail:
        if "node_health_detail" not in intents:
            intents.append("node_health_detail")
        tool_data["node_health_detail"] = {
            "node": matched_node
        }



    asks_service_health = (
        ("service" in q or "services" in q or "ollama" in q or "house-agent" in q)
        and any(word in q for word in ["health", "status", "running", "alive", "up", "doing"])
    )

    if asks_service_health:
        if "service_health" not in intents:
            intents.append("service_health")



    return {
        "question_lower": q,
        "symbol": symbol,
        "is_crypto_question": is_crypto_question,
        "is_power_question": is_power_question,
        "intents": intents,
        "tool_data": tool_data,
    }
