#!/usr/bin/env bash
set -euo pipefail

cd /home/jnoppe/house-agent || exit 1

KNOW="house-ai-knowledge"
GEN="$KNOW/generated"

cp "$GEN/route_map.md" "$KNOW/api/15-generated-route-map.md"
cp "$GEN/service_map.md" "$KNOW/services/16-generated-service-map.md"
cp "$GEN/tool_map.md" "$KNOW/services/17-generated-tool-map.md"

cat > "$KNOW/api/02-route-inventory.md" <<'EOF'
# Route Inventory

This file is the human-maintained summary.
See also:
- `api/15-generated-route-map.md` for auto-detected route handlers
- `generated/route_map.json` for machine-readable data

## Route families
- health/status
- power / sma / water / pdata / price
- agent / house
- voice / voice input
- tools / openai / loxone / audio

## What to maintain here
- which routes are read-only
- which routes perform writes
- which routes are safe for AI invocation
- which routes require confirmation
EOF

cat > "$KNOW/services/03-service-inventory.md" <<'EOF'
# Service Inventory

This file is the human-maintained summary.
See also:
- `services/16-generated-service-map.md` for auto-detected functions/classes
- `generated/service_map.json` for machine-readable data

## Service groups
- agent and routing
- power / energy / sensor services
- voice / STT / announcement services
- Loxone / music / action services
- proposed / experimental tool lifecycle
- package install / approval services

## What to maintain here
- purpose of each service
- side effects
- safety classification
- main callers
EOF

cat > "$KNOW/services/05-tool-lifecycle.md" <<'EOF'
# Tool Lifecycle

This file is the human-maintained summary.
See also:
- `services/17-generated-tool-map.md`
- `generated/tool_map.json`

## Lifecycle
- production tools in `tools/`
- experimental tools in `experimental_tools/`
- proposed tools tracked in `data/proposed_tools.json`

## What to maintain here
- promotion rules
- validation path
- approval requirements
- audit files
- cooldown behavior
EOF

echo "Applied generated docs into knowledge pack."
