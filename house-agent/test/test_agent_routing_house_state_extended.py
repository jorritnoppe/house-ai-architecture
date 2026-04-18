from services.agent_router_bridge import _match_safe_action


def _assert_house_state_route(question: str, reason: str = "interpreted_house_state_query"):
    result = _match_safe_action(question)

    assert result is not None
    assert result["type"] == "route"
    assert result["target"] == "/ai/house_state"
    assert result["reason"] == reason
    assert result["params"] == {}


def test_house_occupied_routes_to_house_state():
    _assert_house_state_route("house occupied")


def test_current_house_state_routes_to_house_state():
    _assert_house_state_route("current house state")


def test_current_state_of_the_house_routes_to_house_state():
    _assert_house_state_route("current state of the house")


def test_house_status_now_routes_to_daily_house_summary():
    result = _match_safe_action("house status now")

    assert result is not None
    assert result["type"] == "route"
    assert result["target"] == "/ai/daily_house_summary"
    assert result["reason"] == "daily_house_summary_query"
    assert result["params"] == {}


def test_which_nodes_are_offline_routes_to_house_state():
    _assert_house_state_route("which nodes are offline")


def test_what_nodes_are_offline_routes_to_house_state():
    _assert_house_state_route("what nodes are offline")


def test_are_any_services_unhealthy_routes_to_house_state():
    _assert_house_state_route("are any services unhealthy")


def test_which_services_are_unhealthy_routes_to_house_state():
    _assert_house_state_route("which services are unhealthy")


def test_is_solar_covering_the_house_load_routes_to_house_state():
    _assert_house_state_route("is solar covering the house load")


def test_are_we_importing_from_the_grid_right_now_routes_to_house_state():
    _assert_house_state_route("are we importing from the grid right now")


def test_current_house_load_routes_to_house_state():
    _assert_house_state_route("current house load")


def test_house_power_usage_routes_to_house_state():
    _assert_house_state_route("house power usage")


def test_which_monitoring_nodes_are_unavailable_routes_to_house_state():
    _assert_house_state_route("which monitoring nodes are unavailable")


def test_what_monitoring_nodes_are_unavailable_routes_to_house_state():
    _assert_house_state_route("what monitoring nodes are unavailable")


def test_which_voice_nodes_are_online_routes_to_house_state():
    _assert_house_state_route("which voice nodes are online")


def test_are_any_voice_nodes_online_routes_to_house_state():
    _assert_house_state_route("are any voice nodes online")


def test_is_the_house_mostly_idle_right_now_routes_to_house_state():
    _assert_house_state_route("is the house mostly idle right now")


def test_what_warnings_should_i_care_about_routes_to_house_state():
    _assert_house_state_route("what warnings should i care about")


def test_is_anything_important_wrong_right_now_routes_to_house_state():
    _assert_house_state_route("is anything important wrong right now")
