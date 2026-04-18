from services.agent_router_bridge import _match_safe_action


def test_unknown_devices_routes_to_house_state():
    result = _match_safe_action("any unknown devices on the network")

    assert result is not None
    assert result["type"] == "route"
    assert result["target"] == "/ai/house_state"
    assert result["reason"] == "interpreted_house_state_query"
    assert result["params"] == {}
