# Automation Safety

The system is designed so the AI does not directly execute arbitrary control logic.

## Safety principles
- explicit route allowlists
- bounded tool execution
- separation of reasoning and execution
- approval flow for sensitive operations
- read-versus-write distinction

## Why this matters
A useful house AI should assist and automate, but only within controlled boundaries. Safety is treated as part of the architecture, not as an afterthought.
