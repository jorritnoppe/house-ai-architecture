#!/usr/bin/env python3
import ast
import os
import re
import json
from pathlib import Path

ROOT = Path("/home/jnoppe/house-agent")
KNOW = ROOT / "house-ai-knowledge"
GEN = KNOW / "generated"

ROUTES_DIR = ROOT / "routes"
SERVICES_DIR = ROOT / "services"
TOOLS_DIR = ROOT / "tools"
EXPERIMENTAL_DIR = ROOT / "experimental_tools"

GEN.mkdir(parents=True, exist_ok=True)

HTTP_METHODS = {"get", "post", "put", "delete", "patch"}

def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""

def extract_blueprint_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if isinstance(node.value, ast.Call):
                        func = node.value.func
                        if isinstance(func, ast.Name) and func.id == "Blueprint":
                            names.add(target.id)
    return names

def get_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = get_name(node.value)
        if left:
            return f"{left}.{node.attr}"
        return node.attr
    return None

def call_keywords(call):
    out = {}
    for kw in call.keywords:
        if kw.arg is None:
            continue
        try:
            out[kw.arg] = ast.literal_eval(kw.value)
        except Exception:
            out[kw.arg] = None
    return out

def extract_routes_from_ast(path: Path):
    src = safe_read(path)
    if not src.strip():
        return []

    try:
        tree = ast.parse(src, filename=str(path))
    except Exception:
        return []

    blueprint_names = extract_blueprint_names(tree)
    routes = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue

            dec_name = get_name(dec.func)
            if not dec_name or not dec_name.endswith(".route"):
                continue

            bp_name = dec_name.split(".")[0]
            if bp_name not in blueprint_names:
                continue

            route_path = None
            methods = ["GET"]

            if dec.args:
                try:
                    route_path = ast.literal_eval(dec.args[0])
                except Exception:
                    route_path = "<dynamic>"

            kws = call_keywords(dec)
            if "methods" in kws and isinstance(kws["methods"], list):
                methods = [str(x).upper() for x in kws["methods"]]

            routes.append({
                "function": node.name,
                "blueprint": bp_name,
                "path": route_path or "<missing>",
                "methods": methods,
                "docstring": ast.get_docstring(node) or "",
                "lineno": node.lineno,
            })

    return sorted(routes, key=lambda x: (x["path"], ",".join(x["methods"]), x["function"]))

def extract_imports(tree):
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                full = f"{module}.{alias.name}" if module else alias.name
                imports.append(full)
    return sorted(set(imports))

def extract_calls(tree):
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            n = get_name(node.func)
            if n:
                calls.append(n)
    return sorted(set(calls))

def extract_functions_from_ast(path: Path):
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
            args = []
            for a in node.args.args:
                args.append(a.arg)
            funcs.append({
                "name": node.name,
                "args": args,
                "docstring": ast.get_docstring(node) or "",
                "lineno": node.lineno,
            })
    return funcs

def extract_classes_from_ast(path: Path):
    src = safe_read(path)
    if not src.strip():
        return []

    try:
        tree = ast.parse(src, filename=str(path))
    except Exception:
        return []

    classes = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)
            classes.append({
                "name": node.name,
                "methods": methods,
                "docstring": ast.get_docstring(node) or "",
                "lineno": node.lineno,
            })
    return classes

def summarize_route_file(path: Path):
    src = safe_read(path)
    if not src.strip():
        return {"file": str(path), "routes": [], "imports": [], "calls": []}

    try:
        tree = ast.parse(src, filename=str(path))
    except Exception:
        return {"file": str(path), "routes": [], "imports": [], "calls": []}

    return {
        "file": str(path.relative_to(ROOT)),
        "routes": extract_routes_from_ast(path),
        "imports": extract_imports(tree),
        "calls": extract_calls(tree),
    }

def summarize_service_file(path: Path):
    src = safe_read(path)
    if not src.strip():
        return {"file": str(path), "functions": [], "classes": [], "imports": [], "calls": []}

    try:
        tree = ast.parse(src, filename=str(path))
    except Exception:
        return {"file": str(path.relative_to(ROOT)), "functions": [], "classes": [], "imports": [], "calls": []}

    return {
        "file": str(path.relative_to(ROOT)),
        "functions": extract_functions_from_ast(path),
        "classes": extract_classes_from_ast(path),
        "imports": extract_imports(tree),
        "calls": extract_calls(tree),
    }

def extract_tool_metadata(path: Path):
    src = safe_read(path)
    result = {
        "file": str(path.relative_to(ROOT)),
        "functions": [],
        "docstring": "",
    }
    if not src.strip():
        return result
    try:
        tree = ast.parse(src, filename=str(path))
    except Exception:
        return result

    result["docstring"] = ast.get_docstring(tree) or ""
    result["functions"] = extract_functions_from_ast(path)
    return result

def write_markdown_routes(route_summaries):
    out = []
    out.append("# Generated Route Map")
    out.append("")
    out.append("Auto-generated from live route files.")
    out.append("")
    for item in route_summaries:
        out.append(f"## {item['file']}")
        out.append("")
        if item["routes"]:
            for r in item["routes"]:
                methods = ", ".join(r["methods"])
                out.append(f"### {methods} {r['path']}")
                out.append(f"- Handler: `{r['function']}`")
                out.append(f"- Blueprint: `{r['blueprint']}`")
                out.append(f"- Line: {r['lineno']}")
                if r["docstring"]:
                    out.append(f"- Docstring: {r['docstring']}")
                out.append("")
        else:
            out.append("- No Flask route decorators detected automatically.")
            out.append("")

        if item["imports"]:
            out.append("#### Imports")
            for imp in item["imports"][:40]:
                out.append(f"- `{imp}`")
            out.append("")

        if item["calls"]:
            out.append("#### Calls seen")
            for c in item["calls"][:50]:
                out.append(f"- `{c}`")
            out.append("")
    (GEN / "route_map.md").write_text("\n".join(out), encoding="utf-8")

def write_markdown_services(service_summaries):
    out = []
    out.append("# Generated Service Map")
    out.append("")
    out.append("Auto-generated from live service files.")
    out.append("")
    for item in service_summaries:
        out.append(f"## {item['file']}")
        out.append("")
        if item["functions"]:
            out.append("### Functions")
            for fn in item["functions"]:
                args = ", ".join(fn["args"])
                out.append(f"- `{fn['name']}({args})`")
                if fn["docstring"]:
                    out.append(f"  - {fn['docstring']}")
            out.append("")
        if item["classes"]:
            out.append("### Classes")
            for cls in item["classes"]:
                out.append(f"- `{cls['name']}`")
                if cls["methods"]:
                    out.append(f"  - Methods: {', '.join(cls['methods'])}")
                if cls["docstring"]:
                    out.append(f"  - {cls['docstring']}")
            out.append("")
        if item["imports"]:
            out.append("### Imports")
            for imp in item["imports"][:40]:
                out.append(f"- `{imp}`")
            out.append("")
        if item["calls"]:
            out.append("### Calls seen")
            for c in item["calls"][:50]:
                out.append(f"- `{c}`")
            out.append("")
    (GEN / "service_map.md").write_text("\n".join(out), encoding="utf-8")

def write_markdown_tools(prod_tools, exp_tools):
    out = []
    out.append("# Generated Tool Map")
    out.append("")
    out.append("Auto-generated from tool files.")
    out.append("")
    out.append("## Production tools")
    out.append("")
    for item in prod_tools:
        out.append(f"### {item['file']}")
        if item["docstring"]:
            out.append(f"- Module docstring: {item['docstring']}")
        if item["functions"]:
            out.append("- Functions:")
            for fn in item["functions"]:
                args = ", ".join(fn["args"])
                out.append(f"  - `{fn['name']}({args})`")
        out.append("")
    out.append("## Experimental tools")
    out.append("")
    for item in exp_tools:
        out.append(f"### {item['file']}")
        if item["docstring"]:
            out.append(f"- Module docstring: {item['docstring']}")
        if item["functions"]:
            out.append("- Functions:")
            for fn in item["functions"]:
                args = ", ".join(fn["args"])
                out.append(f"  - `{fn['name']}({args})`")
        out.append("")
    (GEN / "tool_map.md").write_text("\n".join(out), encoding="utf-8")

def write_json(name, data):
    (GEN / name).write_text(json.dumps(data, indent=2), encoding="utf-8")

def main():
    route_files = sorted(p for p in ROUTES_DIR.glob("*.py") if p.is_file())
    service_files = sorted(p for p in SERVICES_DIR.glob("*.py") if p.is_file())
    prod_tool_files = sorted(p for p in TOOLS_DIR.glob("*.py") if p.is_file())
    exp_tool_files = sorted(p for p in EXPERIMENTAL_DIR.glob("*.py") if p.is_file())

    route_summaries = [summarize_route_file(p) for p in route_files]
    service_summaries = [summarize_service_file(p) for p in service_files]
    prod_tools = [extract_tool_metadata(p) for p in prod_tool_files]
    exp_tools = [extract_tool_metadata(p) for p in exp_tool_files]

    write_json("route_map.json", route_summaries)
    write_json("service_map.json", service_summaries)
    write_json("tool_map.json", {"production": prod_tools, "experimental": exp_tools})

    write_markdown_routes(route_summaries)
    write_markdown_services(service_summaries)
    write_markdown_tools(prod_tools, exp_tools)

    print("Generated:")
    print(GEN / "route_map.json")
    print(GEN / "route_map.md")
    print(GEN / "service_map.json")
    print(GEN / "service_map.md")
    print(GEN / "tool_map.json")
    print(GEN / "tool_map.md")

if __name__ == "__main__":
    main()
