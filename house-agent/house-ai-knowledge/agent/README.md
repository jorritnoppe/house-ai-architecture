# Agent Layer

This folder contains machine-readable policy and mapping files that influence how the house AI selects and executes actions.

## Reading Order
1. `../INDEX.md`
2. `../ai_capabilities.md`
3. `../ai_prompt_contract.md`
4. `action_policy.json`
5. `intent_tool_map.json`
6. `tool_registry.json`

## Notes
- Read routes are preferred over action routes.
- Action routes should usually fall into a review lane unless clearly low-risk.
- The autonomous agent must not recursively call `/agent/query`.
- Protected audio paths must remain on the service-layer controlled flow.
