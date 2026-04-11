import os
import time
import socket
import subprocess
from datetime import datetime, timezone

import requests


DEFAULT_TIMEOUT = 2


def utc_now():
    return datetime.now(timezone.utc).isoformat()


# -----------------------------
# LOW LEVEL CHECKS
# -----------------------------

def ping_check(host: str):
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False


def tcp_check(host: str, port: int, timeout: int = DEFAULT_TIMEOUT):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def check_device(name: str, host: str, port: int = 22):
    start = time.time()

    ping_ok = ping_check(host)
    tcp_ok = False

    if ping_ok:
        tcp_ok = tcp_check(host, port)

    elapsed = round((time.time() - start) * 1000, 1)

    if not ping_ok:
        return {
            "ok": False,
            "severity": "critical",
            "detail": f"{host} not reachable (ping failed)"
        }

    if ping_ok and not tcp_ok:
        return {
            "ok": True,
            "severity": "warning",
            "detail": f"{host} reachable (ping OK, port {port} closed) in {elapsed} ms"
        }

    return {
        "ok": True,
        "severity": "info",
        "detail": f"{host} reachable (ping + port {port}) in {elapsed} ms"
    }


# -----------------------------
# SERVICE CHECKS
# -----------------------------

def http_check(name: str, url: str, severity_if_fail="warning"):
    start = time.time()
    try:
        resp = requests.get(url, timeout=3)
        elapsed = round((time.time() - start) * 1000, 1)
        ok = resp.status_code == 200
        return {
            "ok": ok,
            "severity": "info" if ok else severity_if_fail,
            "detail": f"{url} HTTP {resp.status_code} in {elapsed} ms"
        }
    except Exception as exc:
        return {
            "ok": False,
            "severity": severity_if_fail,
            "detail": f"{url} failed: {exc}"
        }


def ollama_check():
    try:
        url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/tags"
        resp = requests.get(url, timeout=3)
        resp.raise_for_status()
        data = resp.json()
        return {
            "ok": True,
            "severity": "info",
            "detail": f"Ollama OK ({len(data.get('models', []))} models)"
        }
    except Exception as exc:
        return {
            "ok": False,
            "severity": "critical",
            "detail": f"Ollama failed: {exc}"
        }


def influx_check():
    try:
        url = os.getenv("INFLUXDB_HEALTH_URL", "http://127.0.0.1:8086/health")
        resp = requests.get(url, timeout=3)
        resp.raise_for_status()
        return {
            "ok": True,
            "severity": "info",
            "detail": "InfluxDB OK"
        }
    except Exception as exc:
        return {
            "ok": False,
            "severity": "critical",
            "detail": f"InfluxDB failed: {exc}"
        }


# -----------------------------
# SPEECH SUMMARY
# -----------------------------

def build_speech_summary(checks):
    core_names = {"house_agent", "ollama", "influxdb", "open_webui", "voice"}
    core_fail = []
    offline = []
    warnings = []

    for name, c in checks.items():
        readable = name.replace("_", " ")

        if name in core_names and not c["ok"]:
            core_fail.append(readable)
        elif not c["ok"]:
            offline.append(readable)
        elif c["severity"] == "warning":
            warnings.append(readable)

    parts = ["House status report."]

    if not core_fail and not offline and not warnings:
        parts.append("All monitored systems are operational.")
        return " ".join(parts)

    if core_fail:
        if len(core_fail) == 1:
            parts.append(f"Core service issue detected on {core_fail[0]}.")
        else:
            parts.append(f"Core service issues detected on {', '.join(core_fail)}.")

    if offline:
        if len(offline) == 1:
            parts.append(f"{offline[0]} is offline.")
        else:
            parts.append(f"Offline devices: {', '.join(offline)}.")

    if warnings:
        if len(warnings) == 1:
            parts.append(f"{warnings[0]} is online but SSH is unavailable.")
        else:
            parts.append(f"These devices are online but SSH is unavailable: {', '.join(warnings)}.")

    return " ".join(parts)




# -----------------------------
# MAIN STATUS BUILDER
# -----------------------------

def build_status_report():
    checks = {}

    # --- CORE ---
    checks["house_agent"] = {
        "ok": True,
        "severity": "info",
        "detail": "API running"
    }

    checks["ollama"] = ollama_check()

    checks["influxdb"] = influx_check()

    checks["open_webui"] = http_check(
        "open_webui",
        os.getenv("OPEN_WEBUI_URL", "http://127.0.0.1:3000"),
    )

    checks["voice"] = http_check(
        "voice",
        os.getenv("VOICE_STATUS_URL", "http://127.0.0.1:8000/voice/status"),
        severity_if_fail="critical",
    )

    # --- NETWORK DEVICES ---
    devices = [
        ("deskpi", "192.168.9.50", 22),
        ("electricpi", "192.168.9.15", 22),
        ("luifel_pi", "192.168.9.177", 22),
        ("attack_pi", "192.168.1.185", 22),

        ("audio_pi_bass", "192.168.3.243", 22),
        ("audio_pi_living", "192.168.3.172", 22),
        ("audio_pi_toilet", "192.168.3.105", 22),
        ("audio_pi_bathroom", "192.168.9.43", 22),

        ("epson_printer", "192.168.9.227", 80),
        ("desktop", "192.168.1.54", 22),
        ("truenas", "192.168.3.166", 80),

        ("sma_inverter", "192.168.9.24", 502),
    ]

    for name, ip, port in devices:
        checks[name] = check_device(name, ip, port)

    total = len(checks)
    passed = sum(1 for c in checks.values() if c["ok"])
    failed = total - passed
    critical_failed = sum(
        1 for c in checks.values()
        if (not c["ok"]) or c["severity"] == "critical"
    )

    speech = build_speech_summary(checks)

    return {
        "ok": critical_failed == 0,
        "timestamp": utc_now(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "critical": critical_failed,
        },
        "checks": checks,
        "speech_text": speech,
    }
