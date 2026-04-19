from flask import Blueprint, jsonify, request

from services.agent_router_bridge import handle_house_or_ai_question
from services.experimental_approval_service import (
    parse_experimental_approval_question,
    execute_experimental_approval,
)

openai_bp = Blueprint("openai", __name__)


@openai_bp.route("/v1/models", methods=["GET"])
def openai_models():
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "house-agent-router",
                "object": "model",
                "created": 1772971895,
                "owned_by": "house-agent",
            }
        ],
    })


@openai_bp.route("/v1/chat/completions", methods=["POST"])
def openai_chat_completions():
    body = request.get_json(silent=True) or {}

    model = body.get("model", "house-agent-router")
    messages = body.get("messages", [])

    question = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            question = str(msg.get("content", "")).strip()
            break

    # Experimental approval flow first
    approval = parse_experimental_approval_question(question, messages=messages)
    if approval is not None:
        if not approval.get("ok"):
            answer = approval.get("error", "Experimental approval could not be processed.")
            return jsonify({
                "id": "chatcmpl-experimental-approval-error",
                "object": "chat.completion",
                "created": 1772971895,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": answer,
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                "house_agent_meta": {
                    "mode": "experimental_tool_approval_error",
                    "intents": [],
                    "used_tools": [],
                    "tool_data": {},
                },
            })

        execution = execute_experimental_approval(
            tool_name=approval["tool_name"],
            args=approval.get("args", {}),
            admin_password=approval["admin_password"],
        )

        if execution.get("ok"):
            payload = execution.get("payload", {})
            result = payload.get("result", {})
            answer = result.get("answer", f"Experimental tool {approval['tool_name']} executed.")
            return jsonify({
                "id": "chatcmpl-experimental-approved",
                "object": "chat.completion",
                "created": 1772971895,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": answer,
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                "house_agent_meta": {
                    "mode": "experimental_tool_executed",
                    "intents": ["experimental_tool_approval"],
                    "used_tools": [approval["tool_name"]],
                    "tool_data": {
                        "experimental_tool_execution": payload
                    },
                },
            })

        answer = execution.get("error", "Experimental tool execution failed.")
        return jsonify({
            "id": "chatcmpl-experimental-exec-error",
            "object": "chat.completion",
            "created": 1772971895,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": answer,
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "house_agent_meta": {
                "mode": "experimental_tool_execution_error",
                "intents": ["experimental_tool_approval"],
                "used_tools": [approval["tool_name"]],
                "tool_data": {},
            },
        })

    result = handle_house_or_ai_question(question)
    return jsonify({
        "id": "chatcmpl-house-agent",
        "object": "chat.completion",
        "created": 1772971895,
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": result.get("answer", ""),
                },
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "house_agent_meta": {
            "mode": result.get("mode", "unknown"),
            "intents": result.get("intents", []),
            "used_tools": result.get("used_tools", []),
            "tool_data": result.get("tool_data", {}),
        },
    })
