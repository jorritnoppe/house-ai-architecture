from __future__ import annotations

from services.agent_router_bridge import handle_house_or_ai_question


def test_network_data_stale_routes_to_house_state_and_summarizes():
    result = handle_house_or_ai_question("is network data stale")

    assert isinstance(result, dict)
    assert result.get("status") == "ok"
    assert result.get("mode") == "safe_executor"

    action = result.get("executor_action") or {}
    assert action.get("target") == "/ai/house_state"
    assert action.get("reason") == "interpreted_house_state_query"

    auth = result.get("auth_result") or {}
    assert auth.get("allowed") is True
    assert auth.get("auth_level") == "safe_read"

    answer = str(result.get("answer") or "").lower()
    assert answer
    assert "network data" in answer
    assert ("stale" in answer) or ("fresh" in answer) or ("aging" in answer)

    executor_result = result.get("executor_result") or {}
    assert executor_result.get("status") == "ok"

    payload = executor_result.get("data") or {}
    summary = payload.get("summary") or {}
    network_interpretation = (
        summary.get("network_interpretation")
        or payload.get("network_interpretation")
        or {}
    )

    assert isinstance(network_interpretation, dict)
    assert "freshness" in network_interpretation
    assert "is_stale" in network_interpretation
