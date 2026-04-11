from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.voice_node_registry_service import get_voice_node_registry


def _nodes() -> List[Dict[str, Any]]:
    data = get_voice_node_registry().get_summary()
    return list(data.get("nodes", []) or [])


def get_online_nodes() -> List[Dict[str, Any]]:
    return [n for n in _nodes() if n.get("status") == "online"]


def get_nodes_by_room(room_id: str) -> List[Dict[str, Any]]:
    room_id = str(room_id or "").strip().lower()
    return [
        n for n in get_online_nodes()
        if str(n.get("room_id") or "").strip().lower() == room_id
    ]


def get_nodes_by_type(node_type: str) -> List[Dict[str, Any]]:
    node_type = str(node_type or "").strip().lower()
    return [
        n for n in get_online_nodes()
        if str(n.get("node_type") or "").strip().lower() == node_type
    ]


def get_best_mic_node(room_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    candidates = get_online_nodes()

    if room_id:
        room_nodes = get_nodes_by_room(room_id)
        mic_room_nodes = [
            n for n in room_nodes
            if ((n.get("capabilities") or {}).get("mic") is True)
        ]
        if mic_room_nodes:
            return mic_room_nodes[0]

    mic_nodes = [
        n for n in candidates
        if ((n.get("capabilities") or {}).get("mic") is True)
    ]
    return mic_nodes[0] if mic_nodes else None


def get_best_speaker_node(room_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    candidates = get_online_nodes()

    if room_id:
        room_nodes = get_nodes_by_room(room_id)
        speaker_room_nodes = [
            n for n in room_nodes
            if ((n.get("capabilities") or {}).get("speaker") is True)
        ]
        if speaker_room_nodes:
            return speaker_room_nodes[0]

    speaker_nodes = [
        n for n in candidates
        if ((n.get("capabilities") or {}).get("speaker") is True)
    ]
    return speaker_nodes[0] if speaker_nodes else None


def get_playback_reporting_nodes() -> List[Dict[str, Any]]:
    return [
        n for n in get_online_nodes()
        if ((n.get("capabilities") or {}).get("playback_state") is True)
    ]


def build_node_capability_summary() -> Dict[str, Any]:
    nodes = get_online_nodes()

    rooms = {}
    for node in nodes:
        room_id = node.get("room_id") or "unknown"
        rooms.setdefault(room_id, {
            "room_id": room_id,
            "nodes": [],
            "mic_present": False,
            "speaker_present": False,
            "playback_reporting_present": False,
        })

        caps = node.get("capabilities") or {}
        rooms[room_id]["nodes"].append({
            "node_id": node.get("node_id"),
            "node_type": node.get("node_type"),
            "status": node.get("status"),
            "capabilities": caps,
        })

        if caps.get("mic") is True:
            rooms[room_id]["mic_present"] = True
        if caps.get("speaker") is True:
            rooms[room_id]["speaker_present"] = True
        if caps.get("playback_state") is True:
            rooms[room_id]["playback_reporting_present"] = True

    return {
        "status": "ok",
        "online_node_count": len(nodes),
        "room_count": len(rooms),
        "rooms": list(rooms.values()),
    }
