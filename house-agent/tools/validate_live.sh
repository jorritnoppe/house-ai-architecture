#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "===== HOUSE AGENT LIVE VALIDATION ====="
echo "ROOT_DIR=$ROOT_DIR"
echo

if [ -f "venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTEST_BIN="${PYTEST_BIN:-python3 -m pytest}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
LOG_DIR="${LOG_DIR:-validation_logs}"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/live_validation_${STAMP}.log"

mkdir -p "$LOG_DIR"

exec > >(tee "$LOG_FILE") 2>&1

echo "===== 1) PYTHON COMPILE CHECK ====="
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  mapfile -t PY_FILES < <(git ls-files '*.py')
else
  mapfile -t PY_FILES < <(find . -type f -name '*.py' | sort)
fi

if [ "${#PY_FILES[@]}" -eq 0 ]; then
  echo "ERROR: no Python files found"
  exit 1
fi

"$PYTHON_BIN" -m py_compile "${PY_FILES[@]}"

echo
echo "===== 2) ROUTING TEST SUITE ====="
# id="rte4k2"
eval "$PYTEST_BIN -q \
  test/test_agent_routing_network_stale.py \
  test/test_agent_routing_unknown_devices.py \
  test/test_agent_routing_network_queries.py \
  test/test_agent_routing_house_state_general.py \
  test/test_agent_routing_house_state_extended.py \
  test/test_agent_routing_voice_nodes_offline.py \
  test/test_agent_house_state_answer_behavior.py \
  -v"

echo
echo "===== 3) DIRECT PROBE QUESTIONS ====="

probe_question() {
  local q="$1"
  local response
  local status
  local mode

  echo
  echo "--- PROBE: $q ---"

  response="$(curl -fsS -X POST "$BASE_URL/agent/query" \
    -H "Content-Type: application/json" \
    -d "{\"question\":\"$q\"}")"

  echo "$response" | python3 -c '
import json, sys
data = json.load(sys.stdin)
compact = {
    "question": data.get("question"),
    "status": data.get("status"),
    "mode": data.get("mode"),
    "answer": data.get("answer"),
}
print(json.dumps(compact, indent=2))
'

  status="$(echo "$response" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("status", ""))')"
  mode="$(echo "$response" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("mode", ""))')"

  if [ "$status" != "ok" ]; then
    echo
    echo "VALIDATION FAILED: probe returned non-ok status for: $q" >&2
    exit 1
  fi

  if [ -z "$mode" ]; then
    echo
    echo "VALIDATION FAILED: probe returned empty mode for: $q" >&2
    exit 1
  fi
}


probe_question "is anyone home"
probe_question "is the house quiet"
probe_question "are any voice nodes offline"
probe_question "anything unusual right now"
probe_question "is network data stale"

echo
echo "===== VALIDATION OK ====="
echo "Log saved to: $LOG_FILE"
