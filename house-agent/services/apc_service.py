from config import INFLUX_ORG
from extensions import query_api
from services.apc_legacy_core import (
    APC_BUCKET_DEFAULT,
    APC_MEASUREMENTS_DEFAULT,
    handle_apc_question,
)


def _run_apc_question(question: str):
    result = handle_apc_question(
        question=question,
        query_api=query_api,
        org=INFLUX_ORG,
        bucket=APC_BUCKET_DEFAULT,
        measurements=APC_MEASUREMENTS_DEFAULT,
    )

    if result is None:
        return {
            "status": "no_match",
            "answer": "No APC intent matched.",
            "intents": [],
            "tool_data": {},
        }

    return {
        "status": "ok",
        "answer": result.get("answer"),
        "intents": result.get("intents", []),
        "tool_data": result.get("tool_data", {}),
    }


def get_apc_summary_data():
    return _run_apc_question("Give me my APC UPS summary")


def get_apc_on_battery_status_data():
    return _run_apc_question("Is my UPS on battery?")


def get_apc_highest_load_data():
    return _run_apc_question("Which APC UPS has the highest load?")


def get_apc_battery_health_data():
    return _run_apc_question("What is the battery health of my UPS?")


def get_apc_lowest_runtime_data():
    return _run_apc_question("Which APC UPS has the lowest runtime?")
