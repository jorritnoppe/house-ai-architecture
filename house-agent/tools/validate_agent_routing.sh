#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://127.0.0.1:8000"

run_test() {
  local question="$1"
  echo
  echo "============================================================"
  echo "QUESTION: $question"
  curl -s -X POST "$BASE_URL/agent/query" \
    -H "Content-Type: application/json" \
    -d "{\"question\":\"$question\"}" | python3 -m json.tool
}

echo "=== Buderus / Boiler ==="
run_test "what is the boiler doing"
run_test "what is the boiler status"
run_test "is the heating running"
run_test "is heating on"
run_test "is the boiler heating water"
run_test "is hot water active"
run_test "what is the boiler pressure"
run_test "any boiler errors"

echo
echo "=== Butler / House ==="
run_test "give me the house summary"
run_test "give me my morning briefing"
run_test "give me my evening briefing"
run_test "what is the waste schedule"
run_test "is there garbage tomorrow"

echo
echo "=== Telemetry ==="
run_test "what is the temperature in the house"
run_test "what is the humidity in the house"
run_test "which rooms are occupied"
run_test "what is happening in the deskroom"

echo
echo "=== Energy ==="
run_test "how much power are we using"
run_test "how much solar are we making"
run_test "how much solar are we producing"
run_test "what is solar producing now"

