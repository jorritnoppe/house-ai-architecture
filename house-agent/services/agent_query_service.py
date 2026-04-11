from extensions import app, query_api
from apc_ai import handle_apc_question
from config import INFLUX_ORG
from services.agent_router_bridge import handle_house_or_ai_question


def run_agent_query(question: str) -> dict:
    question = (question or "").strip()
    if not question:
        return {
            "status": "error",
            "message": "missing 'question'",
        }

    result = None

    buderus = app.extensions["buderus_service"].handle_agent_question(question)
    if buderus is not None:
        result = buderus
    else:
        try:
            apc_result = handle_apc_question(
                question=question,
                query_api=query_api,
                org=INFLUX_ORG,
                bucket="apcdata",
                measurements=["apc_ups", "apc_ups2"],
            )

            if apc_result:
                result = {
                    "answer": apc_result["answer"],
                    "intents": apc_result["intents"],
                    "mode": "direct_tool",
                    "status": "ok",
                    "tool_data": apc_result["tool_data"],
                }
        except Exception as e:
            app.logger.exception("APC direct tool failed: %s", e)

        if result is None:
            result = handle_house_or_ai_question(question)

    return result
