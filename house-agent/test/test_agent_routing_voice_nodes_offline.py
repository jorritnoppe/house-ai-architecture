from services.agent_router_bridge import _match_safe_action


def _assert_house_state_route(question: str):
    result = _match_safe_action(question)

    assert result is not None
    assert result["type"] == "route"
    assert result["target"] == "/ai/house_state"
    assert result["reason"] == "interpreted_house_state_query"
    assert result["params"] == {}


def test_are_any_voice_nodes_offline_routes_to_house_state():
    _assert_house_state_route("are any voice nodes offline")


def test_which_voice_nodes_are_offline_routes_to_house_state():
    _assert_house_state_route("which voice nodes are offline")


def test_what_voice_nodes_are_offline_routes_to_house_state():
    _assert_house_state_route("what voice nodes are offline")
