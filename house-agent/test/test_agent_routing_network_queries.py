from services.agent_router_bridge import _match_safe_action


def _assert_house_state_route(question: str):
    result = _match_safe_action(question)

    assert result is not None
    assert result["type"] == "route"
    assert result["target"] == "/ai/house_state"
    assert result["reason"] == "interpreted_house_state_query"
    assert result["params"] == {}


def test_network_okay_routes_to_house_state():
    _assert_house_state_route("is the network okay")


def test_clients_active_routes_to_house_state():
    _assert_house_state_route("how many clients are active")


def test_wan_latency_routes_to_house_state():
    _assert_house_state_route("what is the wan latency")


def test_network_freshness_routes_to_house_state():
    _assert_house_state_route("how fresh is the network data")
