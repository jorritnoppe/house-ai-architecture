from __future__ import annotations

import os
from typing import Any, Dict, Optional


def log_voice_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Writes one point into Influx bucket 'home_automation'.

    Measurement:
      voice_requests

    Tags:
      node_id, source_room, resolved_room, audio_target,
      requested_output_target, action_type, action_target, status

    Fields:
      confidence, presence_active, presence_recent,
      user_text, spoken_answer, mode
    """
    try:
        from influxdb_client import InfluxDBClient, Point, WritePrecision
        from influxdb_client.client.write_api import SYNCHRONOUS
    except Exception as exc:
        return {"status": "error", "message": f"influx client import failed: {exc}"}

    influx_url = os.getenv("INFLUX_URL")
    influx_token = os.getenv("INFLUX_TOKEN")
    influx_org = os.getenv("INFLUX_ORG")
    influx_bucket = "home_automation"

    if not influx_url or not influx_token or not influx_org:
        return {
            "status": "error",
            "message": "missing INFLUX_URL / INFLUX_TOKEN / INFLUX_ORG"
        }

    try:
        point = Point("voice_requests")

        def _tag(name: str, value: Optional[Any]):
            if value is not None and str(value).strip():
                point.tag(name, str(value))

        def _field(name: str, value: Optional[Any]):
            if value is None:
                return
            if isinstance(value, bool):
                point.field(name, value)
            elif isinstance(value, (int, float)):
                point.field(name, float(value))
            else:
                point.field(name, str(value))

        _tag("node_id", event.get("node_id"))
        _tag("source_room", event.get("source_room"))
        _tag("resolved_room", event.get("resolved_room"))
        _tag("audio_target", event.get("audio_target"))
        _tag("requested_output_target", event.get("requested_output_target"))
        _tag("action_type", event.get("action_type"))
        _tag("action_target", event.get("action_target"))
        _tag("status", event.get("status"))

        _field("confidence", event.get("confidence"))
        _field("presence_active", event.get("presence_active"))
        _field("presence_recent", event.get("presence_recent"))
        _field("user_text", event.get("user_text"))
        _field("spoken_answer", event.get("spoken_answer"))
        _field("mode", event.get("mode"))

        with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=influx_bucket, org=influx_org, record=point, write_precision=WritePrecision.NS)

        return {"status": "ok"}

    except Exception as exc:
        return {"status": "error", "message": str(exc)}
