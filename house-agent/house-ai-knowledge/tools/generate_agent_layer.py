#!/usr/bin/env python3
import ast
import json
from pathlib import Path

ROOT = Path("/home/jnoppe/house-agent")
KNOW = ROOT / "house-ai-knowledge"
GEN = KNOW / "generated"
AGENT = KNOW / "agent"

ROUTES_DIR = ROOT / "routes"
SERVICES_DIR = ROOT / "services"
TOOLS_DIR = ROOT / "tools"

AGENT.mkdir(parents=True, exist_ok=True)

def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""

def get_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = get_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return None

def extract_blueprint_vars(tree):
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            fn = get_name(node.value.func)
            if fn == "Blueprint":
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        out.add(t.id)
    return out

def parse_literal(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None

def extract_route_defs(path: Path):
    src = safe_read(path)
    if not src.strip():
        return []
    try:
        tree = ast.parse(src, filename=str(path))
    except Exception:
        return []

    bp_vars = extract_blueprint_vars(tree)
    results = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            dec_name = get_name(dec.func)
            if not dec_name:
                continue

            matched = False
            methods = []
            bp_name = None

            if dec_name.endswith(".route"):
                bp_name = dec_name.split(".")[0]
                if bp_name in bp_vars:
                    matched = True
                    methods = ["GET"]
                    for kw in dec.keywords:
                        if kw.arg == "methods":
                            val = parse_literal(kw.value)
                            if isinstance(val, list):
                                methods = [str(x).upper() for x in val]

            else:
                for m in ("get", "post", "put", "delete", "patch"):
                    suffix = f".{m}"
                    if dec_name.endswith(suffix):
                        bp_name = dec_name[: -len(suffix)].split(".")[0]
                        if bp_name in bp_vars:
                            matched = True
                            methods = [m.upper()]
                            break

            if not matched:
                continue

            route_path = "<dynamic>"
            if dec.args:
                lit = parse_literal(dec.args[0])
                if lit is not None:
                    route_path = lit

            results.append({
                "file": str(path.relative_to(ROOT)),
                "function": node.name,
                "blueprint": bp_name,
                "path": route_path,
                "methods": methods,
                "docstring": ast.get_docstring(node) or ""
            })

    results.sort(key=lambda x: (x["path"], ",".join(x["methods"]), x["function"]))
    return results

def extract_service_functions(path: Path):
    src = safe_read(path)
    if not src.strip():
        return []
    try:
        tree = ast.parse(src, filename=str(path))
    except Exception:
        return []

    funcs = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append({
                "file": str(path.relative_to(ROOT)),
                "name": node.name,
                "docstring": ast.get_docstring(node) or "",
                "args": [a.arg for a in node.args.args]
            })
    return funcs

def extract_tool_modules():
    items = []
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        items.append({
            "tool_name": path.stem,
            "file": str(path.relative_to(ROOT)),
            "call": f"tool_registry.execute('{path.stem}', args)",
            "entrypoint": "run(args)"
        })
    return items

def classify_route(route):
    p = route["path"].lower()
    methods = set(route["methods"])
    if methods == {"GET"}:
        if "/ai/" in p or "/status" in p or "/health" in p:
            return "read_only"
        return "read_only"
    if any(m in methods for m in ("POST", "PUT", "DELETE", "PATCH")):
        if "/tools/audio/" in p or "/music/" in p or "/loxone" in p or "/house/" in p:
            return "write_action"
        return "write_action"
    return "unknown"

def risk_for_route(route):
    p = route["path"].lower()
    if "/tools/audio/" in p or "/loxone" in p or "/music/" in p:
        return "high"
    if "/house/" in p or "/agent/" in p:
        return "medium"
    return "low"

def build_intent_map():
    return [
        {
            "intent": "house_status",
            "keywords": ["house status", "overview", "what is going on in the house", "status summary"],
            "preferred_routes": ["/house/diagnostics", "/status", "/health"],
            "preferred_services": ["services.status_service", "services.agent_house", "services.agent_service"],
            "safety": "safe_read"
        },
        {
            "intent": "power_current",
            "keywords": ["power now", "current power", "house consumption", "import export", "grid power"],
            "preferred_routes": ["/power", "/status"],
            "preferred_services": ["services.power_service", "router_logic.gather_house_data"],
            "preferred_tools": ["pdata_energy_summary", "pdata_full_overview", "sma"],
            "safety": "safe_read"
        },
        {
            "intent": "sma_solar",
            "keywords": ["solar", "inverter", "pv production", "sma"],
            "preferred_routes": ["/sma"],
            "preferred_services": ["services.sma_service"],
            "preferred_tools": ["sma"],
            "safety": "safe_read"
        },
        {
            "intent": "water_status",
            "keywords": ["water softener", "salt level", "water temperature"],
            "preferred_routes": ["/water"],
            "preferred_services": ["services.water_service"],
            "preferred_tools": ["salt_tank_level", "water_temperature_summary", "water_softener_overview"],
            "safety": "safe_read"
        },
        {
            "intent": "price_status",
            "keywords": ["price now", "electricity price", "cheapest hours", "cost today"],
            "preferred_routes": ["/price"],
            "preferred_services": ["services.price_service"],
            "preferred_tools": ["latest_price", "cheapest_hours_today", "electricity_cost_today", "electricity_cost_last_24h"],
            "safety": "safe_read"
        },
        {
            "intent": "pdata_queries",
            "keywords": ["pdata", "gas summary", "all fields", "compare energy"],
            "preferred_routes": ["/pdata"],
            "preferred_services": ["services.pdata_service"],
            "preferred_tools": ["pdata_all_fields", "pdata_compare_energy", "pdata_energy_summary", "pdata_full_overview", "pdata_gas_summary"],
            "safety": "safe_read"
        },
        {
            "intent": "crypto_summary",
            "keywords": ["portfolio", "crypto status", "pnl", "top movers"],
            "preferred_services": ["services.agent_crypto", "services.agent_service"],
            "preferred_tools": [
                "crypto_coin_summary", "crypto_compare_7d", "crypto_compare_now_vs_24h",
                "crypto_concentration_risk", "crypto_contributors_24h", "crypto_daily_pnl_summary",
                "crypto_drawdown_7d", "crypto_excluding_symbol_summary", "crypto_portfolio_health",
                "crypto_portfolio_summary", "crypto_stale_data_check", "crypto_top_movers_24h"
            ],
            "safety": "safe_read"
        },
        {
            "intent": "audio_control",
            "keywords": ["turn on speakers", "audio route", "party mode", "playback on", "music on"],
            "preferred_routes": [
                "/tools/audio/node_power/<state>",
                "/tools/audio/speaker_route/<state>",
                "/tools/audio/party/<state>",
                "/tools/audio/playback/<state>"
            ],
            "preferred_services": ["services.loxone_action_service", "services.loxone_music_controls"],
            "safety": "confirmation_or_policy"
        },
        {
            "intent": "voice_output",
            "keywords": ["say this", "announce", "speak through speakers"],
            "preferred_routes": ["/agent", "/voice"],
            "preferred_services": ["services.voice_service", "services.announcement_service"],
            "safety": "safe_write_limited"
        },
        {
            "intent": "network_scan",
            "keywords": ["scan network", "find hosts", "nmap sweep"],
            "preferred_tools": ["network_scan"],
            "preferred_services": ["services.experimental_tool_matcher", "services.experimental_approval_service"],
            "safety": "approval_required"
        }
    ]

def build_action_policy(routes, tools):
    tool_names = {t["tool_name"] for t in tools}
    return {
        "route_policy": [
            {
                "path": r["path"],
                "methods": r["methods"],
                "classification": classify_route(r),
                "risk": risk_for_route(r),
                "allowed_for_llm": classify_route(r) == "read_only",
                "notes": "Auto-generated baseline; review manually for final policy."
            }
            for r in routes
        ],
        "tool_policy": [
            {
                "tool_name": t["tool_name"],
                "allowed_for_llm": t["tool_name"] not in {"network_scan"},
                "risk": "high" if t["tool_name"] in {"network_scan"} else "low",
                "notes": "Auto-generated baseline; review manually."
            }
            for t in tools
        ],
        "global_rules": [
            "LLM must prefer read-only routes by default.",
            "Write actions require allowlisting and often confirmation.",
            "Loxone/audio actions are high risk compared with pure sensor reads.",
            "Experimental and scanning tools require approval flow.",
            "Do not expose secrets or raw credentials to the model."
        ]
    }

def write_md(routes, services, tools, intents, policy):
    out = []
    out.append("# Agent Capability Map")
    out.append("")
    out.append("This file maps user intents to routes, services, tools, and safety policy.")
    out.append("")
    out.append("## Routes detected")
    out.append("")
    for r in routes:
        out.append(f"- `{', '.join(r['methods'])} {r['path']}` -> `{r['file']}::{r['function']}` [{classify_route(r)} / {risk_for_route(r)}]")
    out.append("")
    out.append("## Production tools detected")
    out.append("")
    for t in tools:
        out.append(f"- `{t['tool_name']}` -> `{t['file']}`")
    out.append("")
    out.append("## Intent map")
    out.append("")
    for item in intents:
        out.append(f"### {item['intent']}")
        out.append(f"- Keywords: {', '.join(item.get('keywords', []))}")
        if item.get("preferred_routes"):
            out.append(f"- Preferred routes: {', '.join(item['preferred_routes'])}")
        if item.get("preferred_services"):
            out.append(f"- Preferred services: {', '.join(item['preferred_services'])}")
        if item.get("preferred_tools"):
            out.append(f"- Preferred tools: {', '.join(item['preferred_tools'])}")
        out.append(f"- Safety: {item['safety']}")
        out.append("")
    out.append("## Global safety rules")
    out.append("")
    for rule in policy["global_rules"]:
        out.append(f"- {rule}")
    (AGENT / "agent_capability_map.md").write_text("\n".join(out), encoding="utf-8")

def main():
    routes = []
    for path in sorted(ROUTES_DIR.glob("*.py")):
        routes.extend(extract_route_defs(path))

    services = []
    for path in sorted(SERVICES_DIR.glob("*.py")):
        services.extend(extract_service_functions(path))

    tools = extract_tool_modules()
    intents = build_intent_map()
    policy = build_action_policy(routes, tools)

    (AGENT / "tool_registry.json").write_text(json.dumps(tools, indent=2), encoding="utf-8")
    (AGENT / "intent_tool_map.json").write_text(json.dumps(intents, indent=2), encoding="utf-8")
    (AGENT / "action_policy.json").write_text(json.dumps(policy, indent=2), encoding="utf-8")
    write_md(routes, services, tools, intents, policy)

    print("Generated:")
    print(AGENT / "tool_registry.json")
    print(AGENT / "intent_tool_map.json")
    print(AGENT / "action_policy.json")
    print(AGENT / "agent_capability_map.md")

if __name__ == "__main__":
    main()
