from __future__ import annotations

import os
from flask import Blueprint, current_app, jsonify, request

from services.conversation_manager import ConversationManager
from services.agent_query_service import run_agent_query
from services.audio_orchestrator import announce as announce_audio
from services.voice_output_router import extract_output_target
from services.voice_presence_service import build_presence_validation
from services.automation_influx_logger import log_voice_request
from services.device_registry import get_audio_target_config
from services.feedback_probe_client import (
    probe_audio_window,
    probe_save_window,
    transcribe_saved_probe_file,
    score_probe_capture,
    update_probe_metadata,
    flag_probe_capture,
)




conversation_bp = Blueprint("conversation", __name__)

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_VOICE_NODES_PATH = os.path.join(_BASE_DIR, "house-ai-knowledge", "devices", "voice_nodes.json")


def get_conversation_manager() -> ConversationManager:
    manager = current_app.config.get("conversation_manager")
    if manager is None:
        manager = ConversationManager(voice_nodes_path=_VOICE_NODES_PATH)
        current_app.config["conversation_manager"] = manager
    return manager


@conversation_bp.route("/voice/nodes", methods=["GET"])
def voice_nodes():
    manager = get_conversation_manager()
    return jsonify({
        "status": "ok",
        "nodes": manager.get_nodes()
    })


@conversation_bp.route("/voice/sessions", methods=["GET"])
def voice_sessions():
    manager = get_conversation_manager()
    return jsonify({
        "status": "ok",
        "sessions": manager.get_sessions()
    })


@conversation_bp.route("/voice/playback_state", methods=["GET"])
def voice_playback_state():
    manager = get_conversation_manager()
    return jsonify({
        "status": "ok",
        "playback_state": manager.get_playback_state()
    })


@conversation_bp.route("/voice/reload_nodes", methods=["POST"])
def voice_reload_nodes():
    manager = get_conversation_manager()
    nodes = manager.load_voice_nodes()
    return jsonify({
        "status": "ok",
        "nodes": nodes
    })


@conversation_bp.route("/voice/reset", methods=["POST"])
def voice_reset():
    manager = get_conversation_manager()
    result = manager.reset_state()
    return jsonify(result)


@conversation_bp.route("/voice/event", methods=["POST"])
def voice_event():
    manager = get_conversation_manager()
    payload = request.get_json(silent=True) or {}

    node_id = None
    try:
        event = payload.get("event") or payload
        node_id = event.get("node_id")
        node = manager.get_node(node_id) if node_id else None
        node_room = (node or {}).get("room")

        manual_presence_snapshot = payload.get("presence_snapshot") or {}
        presence_validation = build_presence_validation(node_room, minutes=15)

        # Combine manual test snapshot with auto validation snapshot.
        # Manual payload wins only for explicit test injection.
        auto_snapshot = presence_validation.get("snapshot", {})
        presence_snapshot = {**auto_snapshot, **manual_presence_snapshot}

        result = manager.handle_voice_event(
            event=event,
            presence_snapshot=presence_snapshot
        )

        event_type = event.get("event_type")
        if event_type != "transcript":
            return jsonify({
                **result,
                "presence_validation": presence_validation
            })

        session = result["session"]
        session_id = session["session_id"]
        question = (event.get("text") or "").strip()
        if not question:
            return jsonify({
                "status": "error",
                "error": "Transcript event missing text",
                "session": session
            }), 400

        agent_result = run_agent_query(question)

        requested_output_target = extract_output_target(question)
        audio_target = requested_output_target or session.get("speaker_target") or "desk"

        try:
            audio_cfg = get_audio_target_config(audio_target)
            target_room = audio_cfg.get("room") or audio_target
        except Exception:
            target_room = audio_target



        feedback_probe = None

        answer_preview = (agent_result.get("answer") or "").lower()
        mode = (agent_result.get("mode") or "").lower()

        should_probe_feedback = (
            mode == "fallback_model"
            or "could you clarify" in answer_preview
            or "i'm a bit unsure" in answer_preview
            or "i am a bit unsure" in answer_preview
            or "i'm not sure" in answer_preview
            or "i am not sure" in answer_preview
        )

        if should_probe_feedback:
            try:
                feedback_probe = {
                    "status": "ok",
                    "window": probe_audio_window(seconds_back=6),
                    "saved": probe_save_window(
                        seconds_back=8,
                        label="auto_clarification_probe",
                        metadata={
                            "session_id": session_id,
                            "node_id": node_id,
                            "question": question,
                            "answer": agent_result.get("answer"),
                            "mode": agent_result.get("mode"),
                            "source_room": node_room,
                            "resolved_room": result.get("room_resolution", {}).get("resolved_room"),
                            "requested_output_target": requested_output_target,
                            "audio_target": audio_target,
                        },
                    ),
                }
            except Exception as exc:
                feedback_probe = {
                    "status": "error",
                    "error": str(exc),
                }



        answer = (agent_result.get("answer") or "").strip()
        if not answer:
            answer = "I processed your request, but I do not yet have a spoken answer."


        mark_result = manager.mark_ai_response(
            session_id=session_id,
            ai_text=answer,
            expected_duration_seconds=8,
            target_room=target_room,
            target_player=audio_target,
        )

        audio_result = announce_audio(
            text=answer,
            target=audio_target,
            priority="normal",
            source="conversation_manager",
            level="attention",
            volume=40,
        )

        finish_result = manager.mark_playback_finished(session_id=session_id)
        updated_session = manager.get_sessions().get(session_id)
        feedback_window = (feedback_probe or {}).get("window", {}) if isinstance(feedback_probe, dict) else {}
        feedback_saved = (feedback_probe or {}).get("saved", {}) if isinstance(feedback_probe, dict) else {}
        probe_analysis = None
        try:
            saved_info = (feedback_probe or {}).get("saved") or {}
            saved_path = saved_info.get("saved_to")
            saved_rms = saved_info.get("rms")

            if saved_path:
                probe_transcribe = transcribe_saved_probe_file(saved_path)
                if probe_transcribe.get("status") == "ok":
                    probe_score = score_probe_capture(
                        main_transcript=question,
                        probe_transcript=probe_transcribe.get("transcript", ""),
                        rms=saved_rms,
                    )

                    probe_patch = {
                        "main_transcript": question,
                        "probe_transcript": probe_transcribe.get("transcript", ""),
                        "probe_score": probe_score,
                    }
                    probe_metadata_update = update_probe_metadata(saved_path, probe_patch)

                    probe_flag = None
                    if probe_score.get("classification") in {
                        "low_signal",
                        "empty_probe_transcript",
                        "possible_stt_mismatch",
                    }:
                        probe_flag = flag_probe_capture(saved_path, probe_score["classification"])

                    probe_analysis = {
                        "status": "ok",
                        "transcribe": probe_transcribe,
                        "score": probe_score,
                        "metadata_update": probe_metadata_update,
                        "flag": probe_flag,
                    }
                else:
                    probe_analysis = {
                        "status": "error",
                        "transcribe": probe_transcribe,
                    }
        except Exception as exc:
            probe_analysis = {
                "status": "error",
                "error": str(exc),
            }

        influx_log = log_voice_request({
            "node_id": node_id,
            "source_room": node_room,
            "resolved_room": result.get("room_resolution", {}).get("resolved_room"),
            "audio_target": audio_target,
            "requested_output_target": requested_output_target,
            "action_type": (agent_result.get("executor_action") or {}).get("type"),
            "action_target": (agent_result.get("executor_action") or {}).get("target"),
            "status": agent_result.get("status", "ok"),
            "confidence": result.get("room_resolution", {}).get("confidence"),
            "presence_active": presence_validation.get("presence_active"),
            "presence_recent": presence_validation.get("presence_recent"),
            "user_text": question,
            "spoken_answer": answer,
            "mode": agent_result.get("mode"),
            "feedback_probe_used": bool(feedback_probe),
            "feedback_probe_status": (feedback_probe or {}).get("status") if isinstance(feedback_probe, dict) else None,
            "feedback_probe_rms": feedback_window.get("rms"),
            "feedback_probe_seconds": feedback_window.get("seconds"),
            "feedback_probe_saved_to": feedback_saved.get("saved_to"),
            "feedback_probe_classification": ((probe_analysis or {}).get("score") or {}).get("classification") if isinstance(probe_analysis, dict) else None,
            "feedback_probe_similarity": ((probe_analysis or {}).get("score") or {}).get("similarity") if isinstance(probe_analysis, dict) else None,
            "feedback_probe_transcript": ((probe_analysis or {}).get("transcribe") or {}).get("transcript") if isinstance(probe_analysis, dict) else None,
        })

        return jsonify({
            "status": "ok",
            "room_resolution": result.get("room_resolution"),
            "presence_validation": presence_validation,
            "session": updated_session,
            "agent_result": agent_result,
            "spoken_answer": answer,
            "requested_output_target": requested_output_target,
            "audio_target": audio_target,
            "mark_result": mark_result,
            "audio_result": audio_result,
            "finish_result": finish_result,
            "influx_log": influx_log,
            "feedback_probe": feedback_probe,
            "probe_analysis": probe_analysis,
        })

    except Exception as exc:
        error_log = log_voice_request({
            "node_id": node_id,
            "status": "error",
            "user_text": (payload.get("event") or payload).get("text") if isinstance((payload.get("event") or payload), dict) else None,
            "spoken_answer": None,
            "mode": "conversation_error",
        })
        return jsonify({
            "status": "error",
            "error": str(exc),
            "influx_log": error_log,
        }), 400


@conversation_bp.route("/voice/mark_response", methods=["POST"])
def voice_mark_response():
    manager = get_conversation_manager()
    payload = request.get_json(silent=True) or {}

    try:
        session_id = payload["session_id"]
        ai_text = payload["ai_text"]
        expected_duration_seconds = int(payload.get("expected_duration_seconds", 8))
        target_room = payload.get("target_room")
        target_player = payload.get("target_player")

        result = manager.mark_ai_response(
            session_id=session_id,
            ai_text=ai_text,
            expected_duration_seconds=expected_duration_seconds,
            target_room=target_room,
            target_player=target_player,
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 400


@conversation_bp.route("/voice/mark_playback_finished", methods=["POST"])
def voice_mark_playback_finished():
    manager = get_conversation_manager()
    payload = request.get_json(silent=True) or {}

    try:
        session_id = payload.get("session_id")
        result = manager.mark_playback_finished(session_id=session_id)
        return jsonify(result)
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 400
