import ipaddress
import re
import shutil
import subprocess
import time

TOOL_SPEC = {
    "name": "AI_gen_network_scan",
    "description": "AI-generated network scan tool for private LAN ranges using nmap ping sweep.",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Private target network or host, for example 10.0.0.0/24"
            }
        },
        "required": []
    },
    "safety": "read_only"
}


def _is_private_target(target: str) -> bool:
    try:
        if "/" in target:
            net = ipaddress.ip_network(target, strict=False)
            return net.is_private
        ip = ipaddress.ip_address(target)
        return ip.is_private
    except Exception:
        return False


def _parse_nmap_ping_sweep(output: str):
    hosts = []
    current_ip = None

    for line in output.splitlines():
        line = line.strip()

        m = re.match(r"Nmap scan report for (.+) \((\d+\.\d+\.\d+\.\d+)\)", line)
        if m:
            current_ip = m.group(2)
            hosts.append({"hostname": m.group(1), "ip": m.group(2)})
            continue

        m = re.match(r"Nmap scan report for (\d+\.\d+\.\d+\.\d+)", line)
        if m:
            current_ip = m.group(1)
            hosts.append({"hostname": None, "ip": m.group(1)})
            continue

    unique = []
    seen = set()
    for host in hosts:
        key = host["ip"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(host)

    return unique


def run(args):
    args = args or {}
    target = str(args.get("target") or "10.0.0.0/24").strip()

    if not _is_private_target(target):
        return {
            "ok": False,
            "tool_name": "AI_gen_network_scan",
            "answer": f"Refusing scan because target is not a private LAN range: {target}.",
            "data": {
                "target": target,
                "reason": "non_private_target_blocked",
                "origin": "ai_generated",
                "stage": "production"
            }
        }

    nmap_path = shutil.which("nmap")
    if not nmap_path:
        return {
            "ok": False,
            "tool_name": "AI_gen_network_scan",
            "answer": "nmap is not installed on this system.",
            "data": {
                "target": target,
                "reason": "nmap_not_installed",
                "origin": "ai_generated",
                "stage": "production"
            }
        }

    cmd = [nmap_path, "-sn", target]
    started = time.time()

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        duration = round(time.time() - started, 2)

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        hosts = _parse_nmap_ping_sweep(stdout)

        if hosts:
            answer = f"Scan completed for {target}. Found {len(hosts)} active hosts."
        else:
            answer = f"Scan completed for {target}. No active hosts were found."

        return {
            "ok": completed.returncode == 0,
            "tool_name": "AI_gen_network_scan",
            "answer": answer,
            "data": {
                "target": target,
                "command": " ".join(cmd),
                "returncode": completed.returncode,
                "duration_seconds": duration,
                "alive_host_count": len(hosts),
                "alive_hosts": hosts,
                "stderr": stderr.strip(),
                "origin": "ai_generated",
                "stage": "production"
            }
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "tool_name": "AI_gen_network_scan",
            "answer": f"Scan timed out for {target}.",
            "data": {
                "target": target,
                "reason": "timeout",
                "origin": "ai_generated",
                "stage": "production"
            }
        }