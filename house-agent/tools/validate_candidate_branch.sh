#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/path_policy.sh"

LIVE_REPO="${LIVE_REPO:-$HOME/house-agent}"
PUBLIC_REPO="${PUBLIC_REPO:-$HOME/house-ai-architecture}"
PUBLIC_REMOTE="${PUBLIC_REMOTE:-origin}"
PUBLIC_SUBDIR="${PUBLIC_SUBDIR:-house-agent}"
BRANCH="${1:-}"
BASE_REF="${BASE_REF:-$PUBLIC_REMOTE/main}"
LOG_DIR_REL="${LOG_DIR_REL:-validation_logs}"
STAMP="$(date +%Y%m%d_%H%M%S)"

if [ -z "$BRANCH" ]; then
  cat <<'EOF'
Usage:
  bash tools/validate_candidate_branch.sh <candidate-branch>
EOF
  exit 1
fi

if [ ! -d "$LIVE_REPO/.git" ]; then
  echo "ERROR: live repo not found at $LIVE_REPO" >&2
  exit 1
fi

if [ ! -d "$PUBLIC_REPO/.git" ]; then
  echo "ERROR: public repo not found at $PUBLIC_REPO" >&2
  exit 1
fi

cd "$LIVE_REPO"
mkdir -p "$LOG_DIR_REL"

SAFE_BRANCH_NAME="$(printf '%s' "$BRANCH" | tr '/ ' '__')"
LOG_FILE="$LIVE_REPO/$LOG_DIR_REL/candidate_${SAFE_BRANCH_NAME}_${STAMP}.log"

exec > >(tee "$LOG_FILE") 2>&1

echo "===== CANDIDATE VALIDATION ====="
echo "branch=$BRANCH"
echo "live_repo=$LIVE_REPO"
echo "public_repo=$PUBLIC_REPO"
echo "base_ref=$BASE_REF"
echo "log=$LOG_FILE"
echo

fail_validation() {
  local step="$1"
  local reason="$2"

  echo
  echo "CANDIDATE VALIDATION: FAILED"
  echo "branch: $BRANCH"
  echo "classification: ${CLASSIFICATION:-unknown}"
  echo "failed_step: $step"
  echo "reason: $reason"
  echo "log: $LOG_FILE"
  echo
  echo "----- LOG TAIL -----"
  tail -n 60 "$LOG_FILE" || true
  exit 1
}

classify_changes() {
  local f
  local saw_routing=0
  local saw_executor=0
  local saw_docs_only=1

  for f in "${CHANGED_FILES[@]}"; do
    case "$f" in
      *.md)
        ;;
      *)
        saw_docs_only=0
        ;;
    esac

    case "$f" in
      services/agent_router_bridge.py|services/house_state_service.py|router_logic.py|services/agent_house.py|services/agent_service.py|app.py|routes/house_state_routes.py|test/test_agent_routing_*|test/test_agent_house_state_answer_behavior.py)
        saw_routing=1
        ;;
    esac

    case "$f" in
      services/internal_route_executor.py|services/safe_*|routes/*|house-ai-knowledge/policy/safe_route_allowlist.json|test/*action*|test/*executor*)
        saw_executor=1
        ;;
    esac
  done

  if [ "$saw_routing" -eq 1 ] && [ "$saw_executor" -eq 1 ]; then
    CLASSIFICATION="routing+executor"
  elif [ "$saw_routing" -eq 1 ]; then
    CLASSIFICATION="routing"
  elif [ "$saw_executor" -eq 1 ]; then
    CLASSIFICATION="executor"
  elif [ "$saw_docs_only" -eq 1 ]; then
    CLASSIFICATION="docs"
  else
    CLASSIFICATION="generic"
  fi
}

run_compile_check() {
  echo
  echo "===== COMPILE CHECK ====="

  if [ -f "venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "venv/bin/activate"
  fi

  PYTHON_BIN="${PYTHON_BIN:-python3}"

  mapfile -t PY_FILES < <(find . -type f -name '*.py' \
    -not -path './.git/*' \
    -not -path './venv/*' \
    -not -path './__pycache__/*' \
    -not -path './validation_logs/*' \
    -not -path './tmp/*' \
    -not -path './run/*' \
    | sort)

  if [ "${#PY_FILES[@]}" -eq 0 ]; then
    fail_validation "compile" "no Python files found in workspace"
  fi

  "$PYTHON_BIN" -m py_compile "${PY_FILES[@]}"
}



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
    fail_validation "direct_probe:$q" "probe returned non-ok status"
  fi

  if [ -z "$mode" ]; then
    fail_validation "direct_probe:$q" "probe returned empty mode"
  fi
}

run_routing_validation() {
  echo
  echo "===== ROUTING VALIDATION ====="

  if [ -f "venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "venv/bin/activate"
  fi

  BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

  python3 -m pytest -q \
    test/test_agent_routing_network_stale.py \
    test/test_agent_routing_unknown_devices.py \
    test/test_agent_routing_network_queries.py \
    test/test_agent_routing_house_state_general.py \
    test/test_agent_routing_house_state_extended.py \
    test/test_agent_routing_voice_nodes_offline.py \
    test/test_agent_house_state_answer_behavior.py \
    -v || fail_validation "routing_pytest" "routing benchmark suite failed"

  probe_question "is anyone home"
  probe_question "is the house quiet"
  probe_question "are any voice nodes offline"
  probe_question "anything unusual right now"
  probe_question "is network data stale"
}

run_executor_validation() {
  echo
  echo "===== EXECUTOR VALIDATION ====="
  echo "Executor-specific smoke checks not added yet in v1."
}

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/house_agent_candidate_${STAMP}_XXXXXX")"
cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT



echo "===== FETCH CANDIDATE BRANCH ====="
cd "$PUBLIC_REPO"
git fetch "$PUBLIC_REMOTE" "$BRANCH" || fail_validation "fetch" "unable to fetch candidate branch"
git fetch "$PUBLIC_REMOTE" main || fail_validation "fetch_base" "unable to fetch public main"

CANDIDATE_COMMIT="$(git rev-parse "$PUBLIC_REMOTE/$BRANCH")" || fail_validation "candidate_commit" "unable to resolve candidate branch commit"
BASE_COMMIT="$(git rev-parse "$BASE_REF")" || fail_validation "base_commit" "unable to resolve base ref commit"

echo "candidate_commit=$CANDIDATE_COMMIT"
echo "base_commit=$BASE_COMMIT"

mapfile -t PUBLIC_CHANGED < <(git diff --name-only "$BASE_COMMIT" "$CANDIDATE_COMMIT")



if [ "${#PUBLIC_CHANGED[@]}" -eq 0 ]; then
  fail_validation "diff" "candidate branch has no changed files vs base"
fi

echo
echo "===== PUBLIC CHANGED FILES ====="
printf '%s\n' "${PUBLIC_CHANGED[@]}"

CHANGED_FILES=()
for f in "${PUBLIC_CHANGED[@]}"; do
  case "$f" in
    "$PUBLIC_SUBDIR"/*)
      rel="${f#"$PUBLIC_SUBDIR"/}"
      ;;
    SYNC_WORKFLOW.md)
      rel="$f"
      ;;
    *)
      fail_validation "path_scope" "public change outside allowed sanitized scope: $f"
      ;;
  esac

  if is_blocked_path "$rel"; then
    fail_validation "blocked_path" "candidate touched blocked path: $rel"
  fi

  CHANGED_FILES+=("$rel")
done

classify_changes

echo
echo "===== CLASSIFICATION ====="
echo "classification=$CLASSIFICATION"

echo
echo "===== BUILD TEMP WORKSPACE ====="
rsync -a --delete \
  --exclude '.git' \
  --exclude 'validation_logs' \
  --exclude 'tmp' \
  --exclude 'run' \
  "$LIVE_REPO/" "$WORKDIR/workspace/"

echo "workspace=$WORKDIR/workspace"

for rel in "${CHANGED_FILES[@]}"; do
  src="$PUBLIC_REPO/$PUBLIC_SUBDIR/$rel"
  dst="$WORKDIR/workspace/$rel"

  if [ "$rel" = "SYNC_WORKFLOW.md" ]; then
    continue
  fi

  if [ ! -e "$src" ]; then
    fail_validation "overlay" "candidate file missing from public repo: $rel"
  fi

  mkdir -p "$(dirname "$dst")"
  rsync -a --checksum "$src" "$dst"
  echo "overlayed=$rel"
done

cd "$WORKDIR/workspace"

run_compile_check

case "$CLASSIFICATION" in
  routing)
    run_routing_validation
    ;;
  executor)
    run_executor_validation
    ;;
  routing+executor)
    run_routing_validation
    run_executor_validation
    ;;
  docs)
    echo
    echo "Docs-only candidate: compile/test execution skipped."
    ;;
  generic)
    echo
    echo "Generic candidate: compile check completed."
    ;;
  *)
    fail_validation "classification" "unknown classification: $CLASSIFICATION"
    ;;
esac

echo
echo "CANDIDATE VALIDATION: OK"
echo "branch: $BRANCH"
echo "commit: $CANDIDATE_COMMIT"
echo "classification: $CLASSIFICATION"
echo "log: $LOG_FILE"
