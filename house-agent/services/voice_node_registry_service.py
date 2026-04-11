from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Dict


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


class VoiceNodeRegistryService:
    def __init__(self, stale_after_seconds: int = 45, offline_after_seconds: int = 180) -> None:
        self._lock = RLock()
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self.stale_after_seconds = int(stale_after_seconds)
        self.offline_after_seconds = int(offline_after_seconds)

    def _classify_status(self, last_seen_iso: str | None) -> str:
        if not last_seen_iso:
            return "unknown"

        try:
            last_seen = datetime.fromisoformat(last_seen_iso)
        except Exception:
            return "unknown"

        age = (_utc_now() - last_seen).total_seconds()

        if age <= self.stale_after_seconds:
            return "online"
        if age <= self.offline_after_seconds:
            return "stale"
        return "offline"

    def heartbeat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        node_id = str(payload.get("node_id") or "").strip()
        if not node_id:
            raise ValueError("Missing node_id")

        room_id = str(payload.get("room_id") or "").strip() or None
        node_type = str(payload.get("node_type") or payload.get("type") or "voice_node").strip()
        ip = str(payload.get("ip") or "").strip() or None
        version = str(payload.get("version") or "").strip() or None

        capabilities = payload.get("capabilities") or {}
        health = payload.get("health") or {}
        audio = payload.get("audio") or {}
        mic = payload.get("mic") or {}
        errors = payload.get("errors") or []

        with self._lock:
            existing = self._nodes.get(node_id, {})
            merged = {
                "node_id": node_id,
                "room_id": room_id,
                "node_type": node_type,
                "ip": ip,
                "version": version,
                "capabilities": capabilities if isinstance(capabilities, dict) else {},
                "health": health if isinstance(health, dict) else {},
                "audio": audio if isinstance(audio, dict) else {},
                "mic": mic if isinstance(mic, dict) else {},
                "errors": errors if isinstance(errors, list) else [],
                "uptime_seconds": payload.get("uptime_seconds"),
                "last_seen": _utc_now_iso(),
                "first_seen": existing.get("first_seen") or _utc_now_iso(),
                "status": "online",
            }
            self._nodes[node_id] = merged
            return deepcopy(merged)

    def get_node(self, node_id: str) -> Dict[str, Any] | None:
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return None
            result = deepcopy(node)
            result["status"] = self._classify_status(result.get("last_seen"))
            return result

    def get_all_nodes(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            result = deepcopy(self._nodes)

        for node in result.values():
            node["status"] = self._classify_status(node.get("last_seen"))
        return result

    def get_summary(self) -> Dict[str, Any]:
        nodes = self.get_all_nodes()

        summary = {
            "total_nodes": len(nodes),
            "online": 0,
            "stale": 0,
            "offline": 0,
            "unknown": 0,
        }

        for node in nodes.values():
            status = node.get("status", "unknown")
            if status not in summary:
                status = "unknown"
            summary[status] += 1

        return {
            "status": "ok",
            "generated_at": _utc_now_iso(),
            "summary": summary,
            "nodes": list(nodes.values()),
        }


_registry_singleton: VoiceNodeRegistryService | None = None
_registry_lock = RLock()


def get_voice_node_registry() -> VoiceNodeRegistryService:
    global _registry_singleton
    with _registry_lock:
        if _registry_singleton is None:
            _registry_singleton = VoiceNodeRegistryService()
        return _registry_singleton
