#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path("/home/jnoppe/house-agent")
AGENT = ROOT / "house-ai-knowledge" / "agent"
POLICY = ROOT / "house-ai-knowledge" / "policy"

POLICY.mkdir(parents=True, exist_ok=True)

tool_registry = json.loads((AGENT / "tool_registry.json").read_text(encoding="utf-8"))

SAFE_ROUTES = {
    "/health",
    "/house/diagnostics",
    "/house/diagnostics/text",
    "/house/help",
    "/house/help/text",
    "/house/status",
    "/house/conversation/<conversation_id>/speaker",
    "/house/speaker/<speaker>/status",
    "/status/full",
    "/tools/ping",
    "/voice/status",
    "/voice/logs",
    "/voice/players",
    "/voice/player_status/<player_key>",
    "/voice/files/<path:filename>",
    "/ai/audio_resolve_control",
    "/ai/audio_tool_targets",

    "/ai/power_now",
    "/ai/energy_summary",
    "/ai/energy_today",
    "/ai/phase_overview",

    "/ai/unified_energy_summary",
    "/ai/unified_energy_snapshot",

    "/ai/pdata_all_fields",
    "/ai/pdata_compare_energy",
    "/ai/pdata_energy_summary",
    "/ai/pdata_full_overview",
    "/ai/pdata_gas_summary",

    "/ai/sma_summary",
    "/ai/sma_production_overview",

    "/ai/cheapest_hours_today",
    "/ai/electricity_cost_last_24h",
    "/ai/electricity_cost_today",
    "/ai/electricity_price_now",

    "/ai/salt_tank_level",
    "/ai/water_softener_overview",
    "/ai/water_temperatures",

    "/ai/house_state",
    "/ai/house_briefing_now",
    "/ai/house_briefing_today",
    "/ai/house_facts_now",
    "/ai/house_facts_today",
    "/ai/loxone_history_room_activity_ai",
    "/ai/loxone_history_telemetry_latest",


    "/ai/playback_state",

    "/ai/nodes/health",
    "/ai/nodes/overview",
    "/ai/node/summary",
    "/ai/node/alerts",

    "/ai/service/health",
    "/ai/service/summary",
    "/ai/services/overview",

    "/ai/loxone_history_presence_ai",
    "/ai/loxone_history_telemetry_latest",
    "/ai/loxone_history_room_activity_ai",

    "/nodes/status",
    "/v1/models",
}



REVIEW_ROUTES = {
    "/ai/loxone_audio_action_map",
    "/ai/loxone_audio_behavior_map",
    "/ai/loxone_audio_control_candidates",
    "/ai/loxone_audio_controls_by_room",
    "/ai/loxone_controls_by_category",
    "/ai/loxone_controls_by_room",
    "/ai/loxone_lighting_controls_by_room",
    "/ai/loxone_room_summary",
    "/ai/loxone_room_temperature",
    "/ai/loxone_structure_summary",
}

BLOCKED_ROUTES = {
    "/agent/query",
    "/house/speak/living",
    "/house/speak/wc",
    "/house/speak/<speaker>",
    "/house/speak/all",
    "/house/speak/default",
    "/house/speak/last",
    "/house/speaker/<speaker>/test",
    "/tools/audio/node_power/<state>",
    "/tools/audio/party/<state>",
    "/tools/audio/playback/<state>",
    "/tools/audio/speaker_route/<state>",
    "/v1/chat/completions",
    "/status/announce",
    "/experimental-tools/execute",
    "/proposed-tools/<proposal_id>/approve",
    "/proposed-tools/<proposal_id>/install-missing-packages",
    "/proposed-tools/<proposal_id>/preflight",
    "/proposed-tools/<proposal_id>/promote",
    "/proposed-tools/<proposal_id>/promote-to-production",
    "/proposed-tools/<proposal_id>/reject",
    "/proposed-tools/<proposal_id>/validate",
    "/proposed-tools/analyze-dependencies",
    "/proposed-tools/generate",
    "/proposed-tools/install-package",
    "/proposed-tools/install-plan",
    "/proposed-tools/save",
    "/tools/execute",
    "/voice/process-last",
    "/voice/query-last",
    "/voice/transcribe-last",
    "/voice/upload",
    "/voice/announce",
    "/voice/announce_once",
    "/voice/player_action",
    "/voice/say",
    "/voice/stop",
    "/voice/volume",
}

SAFE_TOOLS = {
    "apc_battery_health",
    "apc_highest_load",
    "apc_lowest_runtime",
    "apc_on_battery_status",
    "apc_summary",
    "buderus_boiler_health_summary",
    "buderus_current_status",
    "buderus_diagnostics",
    "buderus_heating_status",
    "buderus_hot_water_status",
    "buderus_pressure_analysis",
    "cheapest_hours_today",
    "crypto_coin_summary",
    "crypto_compare_7d",
    "crypto_compare_now_vs_24h",
    "crypto_concentration_risk",
    "crypto_contributors_24h",
    "crypto_daily_pnl_summary",
    "crypto_drawdown_7d",
    "crypto_excluding_symbol_summary",
    "crypto_portfolio_health",
    "crypto_portfolio_summary",
    "crypto_stale_data_check",
    "crypto_top_movers_24h",
    "electricity_cost_last_24h",
    "electricity_cost_today",
    "latest_price",
    "pdata_all_fields",
    "pdata_compare_energy",
    "pdata_energy_summary",
    "pdata_full_overview",
    "pdata_gas_summary",
    "salt_tank_level",
    "sma",
    "water_softener_overview",
    "water_temperature_summary",
}

BLOCKED_TOOLS = {
    "network_scan",
    "valid_test_tool",
}

# Route policy generation no longer depends on action_policy.json.
# action_policy.json is an intent policy file, not a route inventory.
safe_route_allowlist = sorted(
    [
        {
            "path": path,
            "classification": "read_only",
            "risk": "low",
        }
        for path in SAFE_ROUTES
    ],
    key=lambda x: x["path"],
)

review_route_list = sorted(
    [
        {
            "path": path,
            "classification": "review_required",
            "risk": "medium",
        }
        for path in REVIEW_ROUTES
    ],
    key=lambda x: x["path"],
)

blocked_route_list = sorted(
    [
        {
            "path": path,
            "classification": "blocked",
            "risk": "high",
        }
        for path in BLOCKED_ROUTES
    ],
    key=lambda x: x["path"],
)

safe_tool_allowlist = []
blocked_tool_list = []
review_tool_list = []

for t in tool_registry:
    name = t["tool_name"]
    item = {
        "tool_name": name,
        "file": t["file"],
        "entrypoint": t["entrypoint"],
    }
    if name in SAFE_TOOLS:
        safe_tool_allowlist.append(item)
    elif name in BLOCKED_TOOLS:
        blocked_tool_list.append(item)
    else:
        review_tool_list.append(item)

safe_tool_allowlist = sorted(safe_tool_allowlist, key=lambda x: x["tool_name"])
review_tool_list = sorted(review_tool_list, key=lambda x: x["tool_name"])
blocked_tool_list = sorted(blocked_tool_list, key=lambda x: x["tool_name"])

(POLICY / "safe_route_allowlist.json").write_text(
    json.dumps(
        {
            "version": "2026-04-12",
            "notes": [
                "Safe routes are read-oriented and suitable for autonomous AI use.",
                "They should not create uncontrolled physical side effects.",
            ],
            "routes": [x["path"] for x in safe_route_allowlist],
        },
        indent=2,
    ),
    encoding="utf-8",
)

(POLICY / "review_route_list.json").write_text(
    json.dumps(review_route_list, indent=2),
    encoding="utf-8",
)

(POLICY / "blocked_route_list.json").write_text(
    json.dumps(blocked_route_list, indent=2),
    encoding="utf-8",
)

(POLICY / "safe_tool_allowlist.json").write_text(
    json.dumps(safe_tool_allowlist, indent=2),
    encoding="utf-8",
)

(POLICY / "review_tool_list.json").write_text(
    json.dumps(review_tool_list, indent=2),
    encoding="utf-8",
)

(POLICY / "blocked_tool_list.json").write_text(
    json.dumps(blocked_tool_list, indent=2),
    encoding="utf-8",
)

md = []
md.append("# Executor Policy")
md.append("")
md.append("This is the final baseline policy for the local house AI executor.")
md.append("")
md.append("## Allowed without confirmation")
md.append("")
md.append("- Read-only sensor and status routes in `safe_route_allowlist.json`")
md.append("- Read-only data tools in `safe_tool_allowlist.json`")
md.append("")
md.append("## Requires manual review before broader AI use")
md.append("")
md.append("- Loxone structure/introspection routes")
md.append("- Any route/tool not explicitly allowlisted")
md.append("")
md.append("## Blocked from normal autonomous execution")
md.append("")
md.append("- Audio switching routes")
md.append("- Speak/announce routes")
md.append("- Generic tool execution routes")
md.append("- Proposed tool generation / promotion / package install routes")
md.append("- Experimental execution routes")
md.append("- Network scanning tools")
md.append("")
md.append("## Important project rule")
md.append("")
md.append(
    "As the project expands, regenerate the policy files and review all new routes and tools before exposing them to the LLM."
)
md.append("")
md.append("## Suggested runtime behavior")
md.append("")
md.append("1. LLM first tries allowlisted read routes.")
md.append("2. If not found, LLM may use allowlisted read tools.")
md.append("3. If action is outside allowlist, return explanation instead of executing.")
md.append("4. High-risk actions must go through a separate approval workflow.")

(POLICY / "executor_policy.md").write_text("\n".join(md), encoding="utf-8")

print("Generated policy files in", POLICY)
