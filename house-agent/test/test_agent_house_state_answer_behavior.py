from __future__ import annotations

from services.agent_router_bridge import handle_house_or_ai_question


def _assert_safe_house_state_answer(question: str):
    result = handle_house_or_ai_question(question)

    assert isinstance(result, dict)
    assert result.get("status") == "ok"
    assert result.get("mode") == "safe_executor"

    action = result.get("executor_action") or {}
    assert action.get("type") == "route"
    assert action.get("target") == "/ai/house_state"
    assert action.get("reason") in {
        "interpreted_house_state_query",
        "interpreted_house_state_unusual_query",
    }

    auth = result.get("auth_result") or {}
    assert auth.get("allowed") is True
    assert auth.get("auth_level") == "safe_read"

    executor_result = result.get("executor_result") or {}
    assert executor_result.get("status") == "ok"

    payload = executor_result.get("data") or {}
    assert isinstance(payload, dict)

    answer = str(result.get("answer") or "").strip()
    assert answer != ""
    return result, payload, answer.lower()


def test_is_anyone_home_returns_house_state_answer():
    result, payload, answer = _assert_safe_house_state_answer("is anyone home")
    summary = payload.get("summary") or {}
    assert "occupied_room_count" in summary
    assert ("home" in answer) or ("occupied" in answer) or ("room" in answer)


def test_which_rooms_are_occupied_returns_house_state_answer():
    result, payload, answer = _assert_safe_house_state_answer("which rooms are occupied")
    summary = payload.get("summary") or {}
    assert "occupied_rooms" in summary
    assert ("occupied" in answer) or ("room" in answer)


def test_is_the_house_quiet_returns_house_state_answer():
    result, payload, answer = _assert_safe_house_state_answer("is the house quiet")
    summary = payload.get("summary") or {}
    assert "quiet_now" in summary
    assert ("quiet" in answer) or ("not fully quiet" in answer)


def test_are_any_voice_nodes_offline_returns_house_state_answer():
    result, payload, answer = _assert_safe_house_state_answer("are any voice nodes offline")
    summary = payload.get("summary") or {}
    assert "voice_nodes_online" in summary
    assert ("voice" in answer) or ("node" in answer) or ("offline" in answer)


def test_anything_unusual_right_now_returns_house_state_answer():
    result, payload, answer = _assert_safe_house_state_answer("anything unusual right now")
    summary = payload.get("summary") or {}
    assert "warning_nodes_count" in summary
    assert answer != ""
