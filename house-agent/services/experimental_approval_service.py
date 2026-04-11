import os
import re
import requests
from typing import Any, Dict, Optional

EXPERIMENTAL_EXECUTE_URL = "http://127.0.0.1:8000/experimental-tools/execute"


def _extract_text_from_content(content) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(parts).strip()

    return ""


def _find_last_assistant_message(messages) -> str:
    if not messages:
        return ""

    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            return _extract_text_from_content(msg.get("content", ""))
    return ""


def _looks_like_password_only_message(question: str) -> bool:
    q = (question or "").strip()

    if not q:
        return False

    q_lower = q.lower()

    # Explicit admin format is still allowed
    if q_lower.startswith("admin approve pw:"):
        return False

    # Password-only message:
    # single token-ish line, no spaces, not too short
    if "\n" in q:
        return False

    if " " in q.strip():
        return False

    if len(q) < 4:
        return False

    # avoid accidentally treating normal short chat words as passwords
    blocked = {
        "yes", "ok", "okay", "approve", "approved", "run", "go", "execute",
        "test", "hello", "hi", "ping", "sure"
    }
    if q_lower in blocked:
        return False

    return True


def _extract_tool_name_from_assistant_text(text: str) -> Optional[str]:
    if not text:
        return None

    patterns = [
        r"experimental tool that may help:\s*([a-zA-Z0-9_]+)",
        r"approve execution for:\s*([a-zA-Z0-9_]+)",
        r"tool\s+([a-zA-Z0-9_]+)\s+requires explicit admin approval",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(1)

    return None


def _extract_args_from_assistant_text(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    args: Dict[str, Any] = {}

    # optional helper if assistant echoes a suggested message
    msg_match = re.search(
        r'message\s*[:=]\s*"([^"]+)"',
        text,
        flags=re.IGNORECASE,
    )
    if msg_match:
        args["message"] = msg_match.group(1)

    return args


def parse_experimental_approval_question(question: str, messages=None):
    q = (question or "").strip()
    if not q:
        return None

    q_lower = q.lower()

    # ------------------------------------------------------------
    # Flow 1: explicit admin approval format
    # Example:
    # "Admin approve pw:test1234"
    # "Admin approve pw:test1234 for experimental_test_ping"
    # ------------------------------------------------------------
    if q_lower.startswith("admin approve pw:"):
        m = re.match(
            r"^admin\s+approve\s+pw:(\S+)(?:\s+for\s+([a-zA-Z0-9_]+))?$",
            q,
            flags=re.IGNORECASE,
        )
        if not m:
            return {
                "ok": False,
                "error": "Could not parse admin approval. Use: Admin approve pw:YOURPASSWORD",
            }

        admin_password = m.group(1)
        tool_name = m.group(2)

        if not tool_name and messages:
            assistant_text = _find_last_assistant_message(messages)
            tool_name = _extract_tool_name_from_assistant_text(assistant_text)

        if not tool_name:
            return {
                "ok": False,
                "error": "Could not determine which experimental tool to approve.",
            }

        return {
            "ok": True,
            "tool_name": tool_name,
            "args": {},
            "admin_password": admin_password,
        }

    # ------------------------------------------------------------
    # Flow 2: password only, immediately after assistant suggestion
    # Example user reply:
    # "test1234"
    # ------------------------------------------------------------
    if _looks_like_password_only_message(q):
        if not messages:
            return None

        assistant_text = _find_last_assistant_message(messages)
        if not assistant_text:
            return None

        tool_name = _extract_tool_name_from_assistant_text(assistant_text)
        if not tool_name:
            return None

        return {
            "ok": True,
            "tool_name": tool_name,
            "args": _extract_args_from_assistant_text(assistant_text),
            "admin_password": q,
        }

    # ------------------------------------------------------------
    # Flow 3: older explicit approval sentence format
    # Example:
    # "Approve experimental_test_ping with message hello password test1234"
    # ------------------------------------------------------------
    if "approve" not in q_lower:
        return None

    tool_match = re.search(
        r"approve(?:\s+execution)?(?:\s+of)?\s+([a-zA-Z0-9_]+)",
        q,
        flags=re.IGNORECASE,
    )
    if not tool_match:
        return {
            "ok": False,
            "error": "Could not detect experimental tool name in approval request.",
        }

    tool_name = tool_match.group(1)

    password_match = re.search(
        r"(?:password|pw|passwd)\s*[:=]?\s*(\S+)",
        q,
        flags=re.IGNORECASE,
    )
    if not password_match:
        return {
            "ok": False,
            "error": "Admin password is required to approve experimental tool execution.",
        }

    admin_password = password_match.group(1)

    message_match = re.search(
        r"with\s+message\s+(.+?)\s+(?:password|pw|passwd)\b",
        q,
        flags=re.IGNORECASE,
    )

    args = {}
    if message_match:
        args["message"] = message_match.group(1).strip()

    return {
        "ok": True,
        "tool_name": tool_name,
        "args": args,
        "admin_password": admin_password,
    }


def execute_experimental_approval(tool_name: str, args=None, admin_password: str = ""):
    args = args or {}

    try:
        r = requests.post(
            EXPERIMENTAL_EXECUTE_URL,
            json={
                "tool_name": tool_name,
                "args": args,
                "approved": True,
                "admin_password": admin_password,
            },
            timeout=20,
        )
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to call experimental execution endpoint: {e}",
        }

    try:
        payload = r.json()
    except Exception:
        return {
            "ok": False,
            "error": f"Experimental execution returned non-JSON response with status {r.status_code}.",
        }

    if r.status_code >= 400:
        return {
            "ok": False,
            "error": payload.get("message", f"Experimental execution failed with status {r.status_code}."),
            "payload": payload,
        }

    if payload.get("status") != "ok":
        return {
            "ok": False,
            "error": payload.get("message", "Experimental execution was not accepted."),
            "payload": payload,
        }

    return {
        "ok": True,
        "payload": payload,
    }
