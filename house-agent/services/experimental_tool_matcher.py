import re
from typing import Any


STOP_WORDS = {
    "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "with",
    "my", "me", "give", "show", "what", "which", "is", "are", "do", "does",
    "get", "tool", "tools", "summary", "overview", "status", "please",
}


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    parts = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return {p for p in parts if p and p not in STOP_WORDS and len(p) > 1}


def find_best_experimental_tool_match(question: str, experimental_tool_registry: Any):
    specs = experimental_tool_registry.list_tool_specs()
    if not specs:
        return None

    q_tokens = _tokenize(question)
    if not q_tokens:
        return None

    best = None
    best_score = 0

    for spec in specs:
        name = spec.get("name", "")
        description = spec.get("description", "")
        module_name = spec.get("module_name", "")

        tool_tokens = set()
        tool_tokens |= _tokenize(name.replace("_", " "))
        tool_tokens |= _tokenize(description)
        tool_tokens |= _tokenize(module_name.replace(".", " "))

        overlap = q_tokens & tool_tokens
        score = len(overlap)

        if score > best_score:
            best_score = score
            best = {
                "tool_name": name,
                "description": description,
                "module_name": module_name,
                "score": score,
                "matched_tokens": sorted(list(overlap)),
                "spec": spec,
            }

    if best_score <= 0:
        return None

    return best
