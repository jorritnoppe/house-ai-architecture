import logging
import os
from typing import Any, Dict, List, Optional

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    InfluxDBClient = None
    Point = None
    SYNCHRONOUS = None

log = logging.getLogger(__name__)


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default


def _to_bool_int(value: Any) -> int:
    return 1 if bool(value) else 0


class UniFiMetricsLogger:
    def __init__(self) -> None:
        self.enabled = os.getenv("UNIFI_INFLUX_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")

        self.url = os.getenv("INFLUX_URL", "").strip()
        self.token = os.getenv("INFLUX_TOKEN", "").strip()
        self.org = os.getenv("INFLUX_ORG", "").strip()
        self.bucket = os.getenv("UNIFI_INFLUX_BUCKET", "").strip()

        self.client = None
        self.write_api = None

        if self.enabled and InfluxDBClient is None:
            log.warning("UniFi Influx logging enabled but influxdb-client is not installed")
            self.enabled = False

        if self.enabled:
            missing = []
            if not self.url:
                missing.append("INFLUX_URL")
            if not self.token:
                missing.append("INFLUX_TOKEN")
            if not self.org:
                missing.append("INFLUX_ORG")
            if not self.bucket:
                missing.append("UNIFI_INFLUX_BUCKET or INFLUX_BUCKET")

            if missing:
                log.warning("UniFi Influx logging disabled, missing env vars: %s", ", ".join(missing))
                self.enabled = False

        if self.enabled:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            log.info("UniFi Influx logger enabled for bucket '%s'", self.bucket)

    def _extract_gateway_metrics(self, summary: Dict[str, Any]) -> Dict[str, Optional[float]]:
        gw_cpu = None
        gw_mem = None
        wan_latency = None
        wan_download = None
        wan_upload = None

        for row in summary.get("site_health_rows", []):
            subsystem = row.get("subsystem")
            if subsystem == "wan":
                gw_stats = row.get("gw_system-stats", {}) or {}
                gw_cpu = _to_float(gw_stats.get("cpu"))
                gw_mem = _to_float(gw_stats.get("mem"))
                wan_info = row.get("uptime_stats", {}).get("WAN", {}) or {}
                wan_latency = _to_float(wan_info.get("latency_average"))
            elif subsystem == "www":
                wan_download = _to_float(row.get("xput_down"))
                wan_upload = _to_float(row.get("xput_up"))

        return {
            "cpu_percent": gw_cpu,
            "mem_percent": gw_mem,
            "wan_latency_ms": wan_latency,
            "wan_download_mbps": wan_download,
            "wan_upload_mbps": wan_upload,
        }

    def write_snapshot(self, cache: Dict[str, Any]) -> None:
        if not self.enabled or not self.client or not self.write_api:
            return

        if cache.get("status") != "ok":
            log.info("Skipping UniFi metrics write because cache status is not ok")
            return

        summary = cache.get("summary", {})
        clients: List[Dict[str, Any]] = cache.get("clients", [])
        devices: List[Dict[str, Any]] = cache.get("devices", [])

        gateway = self._extract_gateway_metrics(summary)

        unknown_clients = [
            c for c in clients
            if c.get("role") == "unknown" or c.get("room") == "unknown"
        ]

        points = []

        p = Point("unifi_summary")
        p.field("devices_total", _to_int(summary.get("device_count_total", 0)))
        p.field("devices_online", _to_int(summary.get("device_count_online", 0)))
        p.field("devices_offline", _to_int(summary.get("device_count_offline", 0)))
        p.field("clients_active", _to_int(summary.get("client_count_active", 0)))
        p.field("alarms", _to_int(summary.get("alarm_count", 0)))
        p.field("mapped_clients", _to_int(summary.get("mapped_clients", 0)))
        p.field("mapped_devices", _to_int(summary.get("mapped_devices", 0)))
        p.field("unknown_clients", _to_int(len(unknown_clients)))
        points.append(p)

        gp = Point("unifi_gateway_health")
        has_gateway_field = False
        for key, value in gateway.items():
            if value is not None:
                gp.field(key, float(value))
                has_gateway_field = True
        if has_gateway_field:
            points.append(gp)

        for d in devices:
            p = Point("unifi_device_status")
            p.tag("name", str(d.get("name", "unknown")))
            p.tag("role", str(d.get("role", "unknown")))
            p.tag("room", str(d.get("room", "unknown")))
            p.tag("mac", str(d.get("mac", "unknown")))
            p.tag("type", str(d.get("type", "unknown")))
            p.field("online", _to_bool_int(d.get("state") == "online"))
            p.field("critical", _to_bool_int(d.get("critical")))
            p.field("mapped", _to_bool_int(d.get("mapped")))
            p.field("portable", _to_bool_int(d.get("portable")))
            points.append(p)

        for c in clients:
            p = Point("unifi_client_presence")
            p.tag("name", str(c.get("name", "unknown")))
            p.tag("role", str(c.get("role", "unknown")))
            p.tag("room", str(c.get("room", "unknown")))
            p.tag("mac", str(c.get("mac", "unknown")))
            p.tag("network", str(c.get("network", "unknown")))
            p.tag("link_type", "wired" if c.get("is_wired") else "wireless")
            p.field("online", _to_bool_int(bool(c.get("ip"))))
            p.field("critical", _to_bool_int(c.get("critical")))
            p.field("mapped", _to_bool_int(c.get("mapped")))
            p.field("portable", _to_bool_int(c.get("portable")))
            p.field("total_bytes", _to_int(c.get("total_bytes", 0)))
            points.append(p)



        log.info("Writing %d UniFi metric points to bucket '%s'", len(points), self.bucket)
        self.write_api.write(bucket=self.bucket, org=self.org, record=points)
        log.info("Wrote %d UniFi metric points to InfluxDB bucket '%s'", len(points), self.bucket)



unifi_metrics_logger = UniFiMetricsLogger()
