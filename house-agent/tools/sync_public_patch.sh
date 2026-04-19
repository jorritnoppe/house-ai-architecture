#!/usr/bin/env bash
set -euo pipefail

LIVE_REPO="${LIVE_REPO:-$HOME/house-agent}"
PUBLIC_REPO="${PUBLIC_REPO:-$HOME/house-ai-architecture}"
PUBLIC_SUBDIR="${PUBLIC_SUBDIR:-house-agent}"

cd "$LIVE_REPO"

if [ ! -d "$PUBLIC_REPO/.git" ]; then
  echo "ERROR: public repo not found at $PUBLIC_REPO"
  exit 1
fi

if [ "$#" -eq 0 ]; then
  cat <<'EOF'
Usage:
  bash tools/sync_public_patch.sh <relative-path> [more paths...]

Examples:
  bash tools/sync_public_patch.sh \
    services/agent_router_bridge.py \
    services/house_state_service.py \
    tools/validate_live.sh \
    SYNC_WORKFLOW.md
EOF
  exit 1
fi

is_blocked_path() {
  local p="$1"

  case "$p" in
    .env|.env.*)
      return 0
      ;;
    secrets/*|data/*|runtime/*|logs/*|validation_logs/*|tmp/*|run/*)
      return 0
      ;;
    *secrets*|*secret*|*token*|*credential*|*credentials*)
      return 0
      ;;
    *.db|*.sqlite|*.sqlite3|*.pem|*.key|*.crt|*.p12|*.pfx)
      return 0
      ;;
    *__pycache__/*|__pycache__/*|*.pyc|*.bak|*.save|*pre_fix*|*.log)
      return 0
      ;;
    .git/*)
      return 0
      ;;
  esac

  return 1
}

for rel in "$@"; do
  if is_blocked_path "$rel"; then
    echo "REFUSING blocked path: $rel" >&2
    exit 1
  fi
done



copy_one() {
  local rel="$1"
  local src="$LIVE_REPO/$rel"
  local dst

  if [ "$rel" = "SYNC_WORKFLOW.md" ]; then
    dst="$PUBLIC_REPO/$rel"
  else
    dst="$PUBLIC_REPO/$PUBLIC_SUBDIR/$rel"
  fi

  if is_blocked_path "$rel"; then
    echo "BLOCKED: $rel"
    return 1
  fi

  if [ ! -e "$src" ]; then
    echo "MISSING: $rel"
    return 1
  fi

  mkdir -p "$(dirname "$dst")"
  rsync -a --delete --checksum "$src" "$dst"
  echo "COPIED: $rel -> $dst"
}

echo "===== SYNC PUBLIC PATCH ====="
echo "LIVE_REPO=$LIVE_REPO"
echo "PUBLIC_REPO=$PUBLIC_REPO"
echo "PUBLIC_SUBDIR=$PUBLIC_SUBDIR"
echo

FAILED=0

for rel in "$@"; do
  if ! copy_one "$rel"; then
    FAILED=1
  fi
done

echo
echo "===== PUBLIC DIFF REVIEW ====="
cd "$PUBLIC_REPO"
git status
echo
git diff --stat
echo
git diff

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "SYNC COMPLETED WITH BLOCKED OR FAILED PATHS"
  exit 1
fi

echo
echo "SYNC OK - REVIEW THE PUBLIC DIFF BEFORE COMMITTING"
