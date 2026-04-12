#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-/home/jnoppe/house-agent}"
KNOW_DIR="$PROJECT_ROOT/house-ai-knowledge"
SNAP_DIR="$KNOW_DIR/_snapshots"

mkdir -p "$SNAP_DIR"

DATE_TAG="$(date +%Y%m%d_%H%M%S)"

find "$PROJECT_ROOT" \
  -path "$PROJECT_ROOT/.git" -prune -o \
  -path "$PROJECT_ROOT/venv" -prune -o \
  -path "$PROJECT_ROOT/.venv" -prune -o \
  -path "$PROJECT_ROOT/node_modules" -prune -o \
  -path "$PROJECT_ROOT/__pycache__" -prune -o \
  -path "$PROJECT_ROOT/backups" -prune -o \
  -path "$PROJECT_ROOT/data/voice_uploads" -prune -o \
  -path "$PROJECT_ROOT/house-ai-knowledge" -prune -o \
  -type f -print | sort > "$SNAP_DIR/file_list_$DATE_TAG.txt"

{
  echo "PROJECT TREE"
  echo "============"
  echo
  find "$PROJECT_ROOT" \
    -path "$PROJECT_ROOT/.git" -prune -o \
    -path "$PROJECT_ROOT/venv" -prune -o \
    -path "$PROJECT_ROOT/.venv" -prune -o \
    -path "$PROJECT_ROOT/node_modules" -prune -o \
    -path "$PROJECT_ROOT/__pycache__" -prune -o \
    -path "$PROJECT_ROOT/backups" -prune -o \
    -path "$PROJECT_ROOT/data/voice_uploads" -prune -o \
    -path "$PROJECT_ROOT/house-ai-knowledge" -prune -o \
    -print | sort
} > "$SNAP_DIR/project_tree_$DATE_TAG.txt"

echo "Knowledge snapshot updated:"
echo "$SNAP_DIR/file_list_$DATE_TAG.txt"
echo "$SNAP_DIR/project_tree_$DATE_TAG.txt"
echo
echo "Now review and update the markdown docs in $KNOW_DIR"
