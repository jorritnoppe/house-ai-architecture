import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from services.unifi_metrics_logger import unifi_metrics_logger
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)




log = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


class UniFiClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("UNIFI_BASE_URL", "").rstrip("/")
        self.site = os.getenv("UNIFI_SITE", "default")
        self.username = os.getenv("UNIFI_USERNAME", "")
        self.password = os.getenv("UNIFI_PASSWORD", "")
        self.verify_ssl = as_bool(os.getenv("UNIFI_VERIFY_SSL", "false"))
        self.timeout = int(os.getenv("UNIFI_TIMEOUT_SECONDS", "20"))

        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        self.logged_in = False

    def login(self) -> None:
        if not self.base_url:
            raise RuntimeError("UNIFI_BASE_URL is not configured")
        if not self.username or not self.password:
            raise RuntimeError("UNIFI_USERNAME or UNIFI_PASSWORD is not configured")

        url = f"{self.base_url}/api/auth/login"
        payload = {
            "username": self.username,
            "password": self.password,
        }

        r = self.session.post(url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        self.logged_in = True
        log.info("UniFi login successful")

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        if not self.logged_in:
            self.login()

        url = f"{self.base_url}{path}"
        r = self.session.request(method, url, timeout=self.timeout, **kwargs)

        if r.status_code in (401, 403):
            log.warning("UniFi session expired, re-authenticating")
            self.login()
            r = self.session.request(method, url, timeout=self.timeout, **kwargs)

        r.raise_for_status()
        if not r.text.strip():
            return {}
        return r.json()

    def get(self, path: str) -> Dict[str, Any]:
        return self._request("GET", path)

    def get_health(self) -> Dict[str, Any]:
        return self.get(f"/proxy/network/api/s/{self.site}/stat/health")

    def get_sysinfo(self) -> Dict[str, Any]:
        return self.get(f"/proxy/network/api/s/{self.site}/stat/sysinfo")

    def get_devices(self) -> Dict[str, Any]:
        return self.get(f"/proxy/network/api/s/{self.site}/stat/device")

    def get_clients(self) -> Dict[str, Any]:
        return self.get(f"/proxy/network/api/s/{self.site}/stat/sta")

    def get_events(self) -> Dict[str, Any]:
        return self.get(f"/proxy/network/api/s/{self.site}/stat/event")

    def get_alarms(self) -> Dict[str, Any]:
        return self.get(f"/proxy/network/api/s/{self.site}/stat/alarm")


class UniFiCollector:
    def __init__(self) -> None:
        self.client = UniFiClient()
        self.poll_seconds = int(os.getenv("UNIFI_POLL_SECONDS", "60"))
        self.lock = threading.Lock()

        self.asset_map_path = Path(
            os.getenv(
                "UNIFI_ASSET_MAP_PATH",
                "/home/jnoppe/house-agent/house-ai-knowledge/devices/unifi_asset_map.json"
            )
        )
        self.asset_map = self._load_asset_map()

        self.cache: Dict[str, Any] = {
            "status": "init",
            "timestamp": None,
            "summary": {},
            "devices": [],
            "clients": [],
            "events": [],
            "alarms": [],
            "topology_lite": {},
            "last_error": None,
        }

        self._thread: Optional[threading.Thread] = None
        self._stop = False

    def _load_asset_map(self) -> Dict[str, Any]:
        try:
            if self.asset_map_path.exists():
                with open(self.asset_map_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    log.info("Loaded UniFi asset map from %s", self.asset_map_path)
                    return data
        except Exception as exc:
            log.warning("Failed to load UniFi asset map: %s", exc)
        return {"clients": {}, "infrastructure": {}}

    def reload_asset_map(self) -> None:
        self.asset_map = self._load_asset_map()

    def _get_asset_meta(self, category: str, mac: Optional[str]) -> Dict[str, Any]:
        if not mac:
            return {}
        mac_norm = str(mac).strip().lower()
        items = self.asset_map.get(category, {})
        for key, value in items.items():
            if str(key).strip().lower() == mac_norm:
                return value or {}
        return {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("UniFi collector thread started")

    def stop(self) -> None:
        self._stop = True

    def _loop(self) -> None:
        while not self._stop:
            try:
                self.refresh()
            except Exception as exc:
                log.exception("UniFi refresh failed")
                with self.lock:
                    self.cache["status"] = "error"
                    self.cache["last_error"] = str(exc)
                    self.cache["timestamp"] = utc_now_iso()
            time.sleep(self.poll_seconds)








    def refresh(self) -> None:
        health_raw = self.client.get_health()
        sysinfo_raw = self.client.get_sysinfo()
        devices_raw = self.client.get_devices()
        clients_raw = self.client.get_clients()

        # Keep these disabled for now while stabilizing refresh timing
        events = []
        alarms = []

        devices = self._normalize_devices(devices_raw.get("data", []))
        clients = self._normalize_clients(clients_raw.get("data", []))

        summary = self._build_summary(
            health_raw.get("data", []),
            sysinfo_raw.get("data", []),
            devices,
            clients,
            alarms,
        )

        topology_lite = self._build_topology_lite(devices, clients)

        cache_snapshot = {
            "status": "ok",
            "timestamp": utc_now_iso(),
            "summary": summary,
            "devices": devices,
            "clients": clients,
            "events": events,
            "alarms": alarms,
            "topology_lite": topology_lite,
            "last_error": None,
        }

        with self.lock:
            self.cache = dict(cache_snapshot)

        log.info("UniFi metrics logger about to write snapshot")
        try:
            unifi_metrics_logger.write_snapshot(cache_snapshot)
            log.info("UniFi metrics logger write_snapshot call finished")
        except Exception as exc:
            log.warning("UniFi metrics logging failed: %s", exc)






    def _normalize_devices(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for row in rows:
            mac = row.get("mac")
            meta = self._get_asset_meta("infrastructure", mac)

            out.append({
                "name": meta.get("name") or row.get("name") or row.get("hostname") or row.get("model", "unknown"),
                "mac": mac,
                "ip": row.get("ip"),
                "model": row.get("model"),
                "type": row.get("type"),
                "state": "online" if row.get("state") == 1 else "offline",
                "disabled": row.get("disabled", False),
                "version": row.get("version"),
                "uptime": row.get("uptime"),
                "adopted": row.get("adopted"),
                "locating": row.get("locating", False),
                "uplink": row.get("uplink"),
                "role": meta.get("role") or self._infer_device_role(row),
                "room": meta.get("room"),
                "portable": bool(meta.get("portable", False)),
                "critical": bool(meta.get("critical", self._is_critical_device(row))),
                "mapped": bool(meta),
            })
        return out

    def _normalize_clients(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for row in rows:
            mac = row.get("mac")
            meta = self._get_asset_meta("clients", mac)

            rx_bytes = row.get("rx_bytes")
            tx_bytes = row.get("tx_bytes")

            out.append({
                "name": meta.get("name") or row.get("name") or row.get("hostname") or row.get("oui") or "unknown-client",
                "hostname": row.get("hostname"),
                "mac": mac,
                "ip": row.get("ip"),
                "network": row.get("network"),
                "ap_mac": row.get("ap_mac"),
                "sw_mac": row.get("sw_mac"),
                "sw_port": row.get("sw_port"),
                "is_wired": row.get("is_wired"),
                "last_seen": row.get("last_seen"),
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
                "total_bytes": (rx_bytes or 0) + (tx_bytes or 0),
                "signal": row.get("signal"),
                "satisfaction": row.get("satisfaction"),
                "role": meta.get("role") or self._infer_client_role(row),
                "room": meta.get("room"),
                "portable": bool(meta.get("portable", meta.get("room") == "all")),
                "critical": bool(meta.get("critical", self._is_critical_client(row))),
                "mapped": bool(meta),
            })
        return out

    def _build_summary(
        self,
        health_rows: List[Dict[str, Any]],
        sysinfo_rows: List[Dict[str, Any]],
        devices: List[Dict[str, Any]],
        clients: List[Dict[str, Any]],
        alarms: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        online_devices = sum(1 for d in devices if d["state"] == "online")
        offline_devices = sum(1 for d in devices if d["state"] != "online")
        critical_offline = [d["name"] for d in devices if d["critical"] and d["state"] != "online"]

        top_clients = sorted(
            clients,
            key=lambda x: x.get("total_bytes", 0),
            reverse=True
        )[:5]

        return {
            "overall": "warning" if critical_offline or alarms else "ok",
            "site_health_rows": health_rows,
            "sysinfo_rows": sysinfo_rows,
            "device_count_total": len(devices),
            "device_count_online": online_devices,
            "device_count_offline": offline_devices,
            "client_count_active": len(clients),
            "alarm_count": len(alarms),
            "critical_offline": critical_offline,
            "mapped_clients": sum(1 for c in clients if c.get("mapped")),
            "mapped_devices": sum(1 for d in devices if d.get("mapped")),
            "top_clients": [
                {
                    "name": c["name"],
                    "ip": c["ip"],
                    "mac": c["mac"],
                    "total_bytes": c.get("total_bytes", 0),
                }
                for c in top_clients
            ],
        }

    def _build_topology_lite(self, devices: List[Dict[str, Any]], clients: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "infra_devices": [
                {
                    "name": d["name"],
                    "type": d["type"],
                    "ip": d["ip"],
                    "mac": d["mac"],
                    "state": d["state"],
                    "room": d.get("room"),
                    "role": d.get("role"),
                }
                for d in devices
            ],
            "clients": [
                {
                    "name": c["name"],
                    "ip": c["ip"],
                    "mac": c["mac"],
                    "ap_mac": c["ap_mac"],
                    "sw_mac": c["sw_mac"],
                    "sw_port": c["sw_port"],
                    "room": c.get("room"),
                    "role": c.get("role"),
                }
                for c in clients
            ],
        }

    def _infer_device_role(self, row: Dict[str, Any]) -> str:
        model = str(row.get("model", "")).lower()
        typ = str(row.get("type", "")).lower()
        if "gateway" in model or typ in ("ugw", "uxg", "udm", "ucg"):
            return "gateway"
        if typ in ("usw", "switch"):
            return "switch"
        if typ in ("uap", "ap"):
            return "access_point"
        return "infrastructure"

    def _infer_client_role(self, row: Dict[str, Any]) -> str:
        name = f"{row.get('name', '')} {row.get('hostname', '')}".lower()
        if "deskpi" in name:
            return "voice_node"
        if "truenas" in name or "nas" in name:
            return "storage"
        if "printer" in name or "epson" in name or "hewlett packard" in name:
            return "printer"
        if "ai-server" in name:
            return "ai_server"
        return "client"

    def _is_critical_device(self, row: Dict[str, Any]) -> bool:
        name = f"{row.get('name', '')} {row.get('hostname', '')}".lower()
        return any(token in name for token in ["gateway", "switch", "ap", "core"])

    def _is_critical_client(self, row: Dict[str, Any]) -> bool:
        name = f"{row.get('name', '')} {row.get('hostname', '')}".lower()
        return any(token in name for token in ["deskpi", "ai-server", "truenas", "printer", "loxone"])

    def get_cache(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.cache)


collector = UniFiCollector()
