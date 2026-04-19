#!/usr/bin/env bash

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
