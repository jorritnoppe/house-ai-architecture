# Executor Policy

This is the final baseline policy for the local house AI executor.

## Allowed without confirmation

- Read-only sensor and status routes in `safe_route_allowlist.json`
- Read-only data tools in `safe_tool_allowlist.json`

## Requires manual review before broader AI use

- Loxone structure/introspection routes
- Any route/tool not explicitly allowlisted

## Blocked from normal autonomous execution

- Audio switching routes
- Speak/announce routes
- Generic tool execution routes
- Proposed tool generation / promotion / package install routes
- Experimental execution routes
- Network scanning tools

## Important project rule

As the project expands, regenerate the policy files and review all new routes and tools before exposing them to the LLM.

## Suggested runtime behavior

1. LLM first tries allowlisted read routes.
2. If not found, LLM may use allowlisted read tools.
3. If action is outside allowlist, return explanation instead of executing.
4. High-risk actions must go through a separate approval workflow.