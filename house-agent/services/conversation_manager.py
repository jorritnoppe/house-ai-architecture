from __future__ import annotations

import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


class ConversationManager:
    """
    Central conversation/session orchestration for room-aware voice handling.

    Design goals:
    - Node-config driven
    - Multi-node ready
    - Explicit playback state tracking
    - Easy debug visibility
    - Simple current behavior for single-node setup
    """

    def __init__(self, voice_nodes_path: str, followup_seconds: int = 20) -> None:
        self.voice_nodes_path = voice_nodes_path
        self.followup_seconds = followup_seconds

        self._lock = threading.RLock()
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._playback_state: Dict[str, Any] = self._default_playback_state()

        self.load_voice_nodes()

    def _default_playback_state(self) -> Dict[str, Any]:
        return {
            "active": False,
            "session_id": None,
            "target_room": None,
            "target_player": None,
            "started_at": None,
            "expected_end_at": None,
            "last_text": None
        }

    def load_voice_nodes(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            if not os.path.exists(self.voice_nodes_path):
                raise FileNotFoundError(f"Voice node registry not found: {self.voice_nodes_path}")

            with open(self.voice_nodes_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            nodes = raw.get("nodes", [])
            loaded: Dict[str, Dict[str, Any]] = {}

            for node in nodes:
                node_id = node.get("node_id")
                if not node_id:
                    continue
                loaded[node_id] = node

            self._nodes = loaded
            return deepcopy(self._nodes)

    def get_nodes(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return deepcopy(self._nodes)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            node = self._nodes.get(node_id)
            return deepcopy(node) if node else None

    def resolve_room(self, node_id: str, presence_snapshot: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        """
        Current behavior:
        - primary source = node mapped room
        - optional presence snapshot can increase confidence

        Future behavior can add:
        - recent playback target
        - active session continuity
        - debug wearable influence
        """
        node = self.get_node(node_id)
        if not node:
            return {
                "resolved_room": None,
                "confidence": 0.0,
                "reasons": [f"unknown node_id: {node_id}"]
            }

        room = node.get("room")
        reasons = [f"node {node_id} mapped to room {room}"]
        confidence = 0.70

        if presence_snapshot and room in presence_snapshot:
            if presence_snapshot.get(room):
                confidence = 0.92
                reasons.append(f"presence active in {room}")
            else:
                confidence = 0.60
                reasons.append(f"presence inactive in {room}")

        return {
            "resolved_room": room,
            "confidence": round(confidence, 2),
            "reasons": reasons
        }

    def _make_session(self, node_id: str, room: str, speaker_target: str) -> Dict[str, Any]:
        now = utc_now()
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        return {
            "session_id": session_id,
            "node_id": node_id,
            "room": room,
            "speaker_target": speaker_target,
            "state": "listening",
            "started_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "last_user_text": None,
            "last_ai_text": None,
            "followup_until": (now + timedelta(seconds=self.followup_seconds)).isoformat(),
            "playback_active": False,
            "events": []
        }

    def _find_recent_session_for_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        now = utc_now()
        candidates = []

        for session in self._sessions.values():
            if session.get("node_id") != node_id:
                continue

            followup_until = session.get("followup_until")
            if not followup_until:
                continue

            try:
                followup_dt = datetime.fromisoformat(followup_until)
            except ValueError:
                continue

            if followup_dt >= now:
                candidates.append(session)

        if not candidates:
            return None

        candidates.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return deepcopy(candidates[0])

    def get_or_create_session(
        self,
        node_id: str,
        presence_snapshot: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        with self._lock:
            recent = self._find_recent_session_for_node(node_id)
            if recent:
                return recent

            room_info = self.resolve_room(node_id=node_id, presence_snapshot=presence_snapshot)
            room = room_info.get("resolved_room")
            node = self._nodes.get(node_id)

            if not node or not room:
                raise ValueError(f"Unable to resolve room for node_id={node_id}")
            speaker_target = node.get("default_output_target", room)
            session = self._make_session(node_id=node_id, room=room, speaker_target=speaker_target)
            session["events"].append({
                "timestamp": iso_now(),
                "event_type": "session_created",
                "room_resolution": room_info
            })

            self._sessions[session["session_id"]] = session
            return deepcopy(session)

    def append_event(self, session_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if session_id not in self._sessions:
                raise ValueError(f"Unknown session_id={session_id}")

            session = self._sessions[session_id]
            session["events"].append(event)
            session["updated_at"] = iso_now()
            return deepcopy(session)

    def handle_voice_event(
        self,
        event: Dict[str, Any],
        presence_snapshot: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """
        Supported incoming event_type:
        - speech_detected
        - transcript
        - wakeword_detected
        """
        event_type = event.get("event_type")
        node_id = event.get("node_id")

        if not event_type:
            raise ValueError("Missing event_type")
        if not node_id:
            raise ValueError("Missing node_id")

        node = self.get_node(node_id)
        if not node:
            raise ValueError(f"Unknown node_id={node_id}")
        if not node.get("enabled", False):
            raise ValueError(f"Node disabled: {node_id}")

        with self._lock:
            session = self.get_or_create_session(node_id=node_id, presence_snapshot=presence_snapshot)
            session_id = session["session_id"]

            stored_session = self._sessions[session_id]
            stored_session["updated_at"] = iso_now()
            stored_session["followup_until"] = (
                utc_now() + timedelta(seconds=self.followup_seconds)
            ).isoformat()

            normalized_event = {
                "timestamp": iso_now(),
                "event_type": event_type,
                "node_id": node_id,
                "payload": deepcopy(event)
            }

            if event_type == "transcript":
                stored_session["last_user_text"] = event.get("text")
                stored_session["state"] = "processing"

            elif event_type in ("speech_detected", "wakeword_detected"):
                stored_session["state"] = "listening"

            stored_session["events"].append(normalized_event)

            return {
                "status": "ok",
                "session": deepcopy(stored_session),
                "room_resolution": self.resolve_room(node_id=node_id, presence_snapshot=presence_snapshot),
                "playback_state": deepcopy(self._playback_state)
            }

    def mark_ai_response(
        self,
        session_id: str,
        ai_text: str,
        expected_duration_seconds: int = 8,
        target_room: str | None = None,
        target_player: str | None = None,
    ) -> Dict[str, Any]:

        with self._lock:
            if session_id not in self._sessions:
                raise ValueError(f"Unknown session_id={session_id}")

            session = self._sessions[session_id]

            room = target_room or session.get("room")
            player = target_player or session.get("speaker_target")



            session["last_ai_text"] = ai_text
            session["state"] = "responding"
            session["playback_active"] = True
            session["updated_at"] = iso_now()
            session["followup_until"] = (
                utc_now() + timedelta(seconds=self.followup_seconds)
            ).isoformat()

            self._playback_state = {
                "active": True,
                "session_id": session_id,
                "target_room": room,
                "target_player": player,
                "started_at": iso_now(),
                "expected_end_at": (utc_now() + timedelta(seconds=expected_duration_seconds)).isoformat(),
                "last_text": ai_text
            }

            session["events"].append({
                "timestamp": iso_now(),
                "event_type": "playback_started",
                "target_room": room,
                "target_player": player,
                "text": ai_text
            })

            return {
                "status": "ok",
                "session": deepcopy(session),
                "playback_state": deepcopy(self._playback_state)
            }

    def mark_playback_finished(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            active_session_id = self._playback_state.get("session_id")

            if session_id and active_session_id and session_id != active_session_id:
                raise ValueError(
                    f"Playback session mismatch: active={active_session_id}, provided={session_id}"
                )

            resolved_session_id = session_id or active_session_id

            if resolved_session_id and resolved_session_id in self._sessions:
                session = self._sessions[resolved_session_id]
                session["playback_active"] = False
                session["state"] = "awaiting_followup"
                session["updated_at"] = iso_now()
                session["followup_until"] = (
                    utc_now() + timedelta(seconds=self.followup_seconds)
                ).isoformat()
                session["events"].append({
                    "timestamp": iso_now(),
                    "event_type": "playback_finished"
                })

            self._playback_state = self._default_playback_state()

            return {
                "status": "ok",
                "session_id": resolved_session_id,
                "playback_state": deepcopy(self._playback_state)
            }

    def get_sessions(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return deepcopy(self._sessions)

    def get_playback_state(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._playback_state)

    def reset_state(self) -> Dict[str, Any]:
        with self._lock:
            self._sessions = {}
            self._playback_state = self._default_playback_state()
            return {
                "status": "ok",
                "message": "conversation manager state reset"
            }

