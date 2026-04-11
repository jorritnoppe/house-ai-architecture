import requests

API = "http://127.0.0.1:8000"


def get_house_power_now():
    r = requests.get(f"{API}/ai/power_now", timeout=10)
    r.raise_for_status()
    return r.json()


def get_energy_summary():
    r = requests.get(f"{API}/ai/energy_summary", timeout=10)
    r.raise_for_status()
    return r.json()


def get_phase_overview():
    r = requests.get(f"{API}/ai/phase_overview", timeout=10)
    r.raise_for_status()
    return r.json()


def get_tools():
    r = requests.get(f"{API}/tools", timeout=10)
    r.raise_for_status()
    return r.json()
