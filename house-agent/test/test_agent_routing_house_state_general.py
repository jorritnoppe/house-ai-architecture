from services.agent_router_bridge import _match_safe_action


def _assert_house_state_route(question: str, reason: str = "interpreted_house_state_query"):
    result = _match_safe_action(question)

    assert result is not None
    assert result["type"] == "route"
    assert result["target"] == "/ai/house_state"
    assert result["reason"] == reason
    assert result["params"] == {}


def _assert_daily_summary_route(question: str):
    result = _match_safe_action(question)

    assert result is not None
    assert result["type"] == "route"
    assert result["target"] == "/ai/daily_house_summary"
    assert result["reason"] == "daily_house_summary_query"
    assert result["params"] == {}


def test_is_anyone_home_routes_to_house_state():
    _assert_house_state_route("is anyone home")


def test_which_rooms_are_occupied_routes_to_house_state():
    _assert_house_state_route("which rooms are occupied")


def test_is_the_house_quiet_routes_to_house_state():
    _assert_house_state_route("is the house quiet")


def test_are_any_voice_nodes_offline_routes_to_house_state():
    _assert_house_state_route("are any voice nodes offline")


def test_which_rooms_are_active_routes_to_house_state():
    _assert_house_state_route("which rooms are active")


def test_anything_unusual_routes_to_house_state():
    _assert_house_state_route("anything unusual right now", reason="interpreted_house_state_unusual_query")


def test_house_status_now_routes_to_daily_house_summary():
    result = _match_safe_action("house status now")

    assert result is not None
    assert result["type"] == "route"
    assert result["target"] == "/ai/daily_house_summary"
    assert result["reason"] == "daily_house_summary_query"
    assert result["params"] == {}


def test_house_summary_routes_to_daily_house_summary():
    _assert_daily_summary_route("house summary")


def test_current_house_status_routes_to_daily_house_summary():
    _assert_daily_summary_route("current house status")
