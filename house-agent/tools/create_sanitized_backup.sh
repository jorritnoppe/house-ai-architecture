#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$HOME/house-agent}"
BACKUP_DIR="/mnt/aiserver-backups"
STAMP="$(date +%Y%m%d_%H%M%S)"
PROJECT_NAME="$(basename "$PROJECT_DIR")"
WORK_DIR="/tmp/${PROJECT_NAME}_sanitized_${STAMP}"
STAGE_DIR="${WORK_DIR}/${PROJECT_NAME}"
ZIP_PATH="${BACKUP_DIR}/${PROJECT_NAME}_sanitized_${STAMP}.zip"

mkdir -p "$BACKUP_DIR"
mkdir -p "$WORK_DIR"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "ERROR: Project dir not found: $PROJECT_DIR"
  exit 1
fi

echo "==> Project: $PROJECT_DIR"
echo "==> Staging: $STAGE_DIR"
echo "==> Output : $ZIP_PATH"

echo "==> Copying project to staging area..."
rsync -a \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'venv/' \
  --exclude 'node_modules/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.mypy_cache/' \
  --exclude '.cache/' \
  --exclude '.idea/' \
  --exclude '.vscode/' \
  --exclude 'dist/' \
  --exclude 'build/' \
  --exclude 'backups/' \
  --exclude 'data/voice_uploads/' \
  --exclude '*.wav' \
  --exclude '*.mp3' \
  --exclude '*.tar.gz' \
  --exclude '*.zip' \
  --exclude '*.pyc' \
  --exclude '*.pyo' \
  --exclude '*.db' \
  --exclude '*.sqlite' \
  --exclude '*.sqlite3' \
  --exclude '*.log' \
  --exclude '*.jsonl' \
  --exclude 'logs/' \
  --exclude 'tmp/' \
  --exclude 'temp/' \
  --exclude '.DS_Store' \
  "$PROJECT_DIR/" "$STAGE_DIR/"
echo "==> Removing known sensitive files..."
find "$STAGE_DIR" -type f \( \
  -name ".env" -o \
  -name ".env.*" -o \
  -name "*.pem" -o \
  -name "*.key" -o \
  -name "*.crt" -o \
  -name "*.p12" -o \
  -name "*.pfx" -o \
  -name "id_rsa" -o \
  -name "id_ed25519" -o \
  -name "known_hosts" -o \
  -name "*.ovpn" -o \
  -name "*.kdbx" \
\) -print -delete || true

rm -rf "$STAGE_DIR/.git" || true
rm -rf "$STAGE_DIR/secrets" || true
rm -rf "$STAGE_DIR/secret" || true
rm -rf "$STAGE_DIR/private" || true
rm -rf "$STAGE_DIR/keys" || true
rm -rf "$STAGE_DIR/certs" || true

echo "==> Redacting secrets in text files..."

is_text_file() {
  local file="$1"

  case "$file" in
    *.py|*.sh|*.bash|*.zsh|*.js|*.ts|*.json|*.yaml|*.yml|*.toml|*.ini|*.cfg|*.conf|*.service|*.md|*.txt|*.csv|*.env|*.example|*.xml|*.html|*.css)
      return 0
      ;;
  esac

  if command -v file >/dev/null 2>&1; then
    file --brief --mime "$file" 2>/dev/null | grep -q '^text/' && return 0
    file --brief --mime "$file" 2>/dev/null | grep -q 'charset=' && return 0
  fi

  grep -Iq . "$file" 2>/dev/null && return 0

  return 1
}

redact_file() {
  local file="$1"

  if [ "$(stat -c%s "$file")" -gt 5242880 ]; then
    return 0
  fi

  python3 - "$file" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    text = path.read_text(encoding="utf-8", errors="ignore")
except Exception:
    sys.exit(0)

original = text

patterns = [
    (r'(?im)^(\s*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|PASS|PASSWD|DB_PASS|DB_PASSWORD|ACCESS_TOKEN|REFRESH_TOKEN|CLIENT_SECRET|WEBHOOK_SECRET|JWT_SECRET|PRIVATE_KEY|BITVAVO_API_KEY|BITVAVO_API_SECRET|OPENAI_API_KEY|OLLAMA_API_KEY)\s*[:=]\s*)(.+?)\s*$',
     r'\1[REDACTED]'),

    (r'(?im)("?(?:api[_-]?key|token|secret|password|passwd|client_secret|access_token|refresh_token|jwt_secret|private_key|bitvavo_api_key|bitvavo_api_secret|openai_api_key|ollama_api_key)"?\s*:\s*")([^"]+)(")',
     r'\1[REDACTED]\3'),

    (r'(?i)(Authorization\s*:\s*Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*',
     r'\1[REDACTED]'),

    (r'(?i)\b([a-z][a-z0-9+\-.]*://)([^:/\s]+):([^@/\s]+)@',
     r'\1[REDACTED]:[REDACTED]@'),

    (r'(?im)^(\s*INFLUXDB_TOKEN\s*[:=]\s*)(.+?)\s*$',
     r'\1[REDACTED]'),

    (r'(?i)(https?://)([^:/\s]+):([^@/\s]+)@',
     r'\1[REDACTED]:[REDACTED]@'),

    (r'-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----',
     '[REDACTED PRIVATE KEY BLOCK]'),

    (r'(?im)^(\s*(?:username|user)\s*[:=]\s*)(.+?)\s*$',
     r'\1[REDACTED_USER]'),
    (r'(?im)^(\s*(?:password|pass|passwd)\s*[:=]\s*)(.+?)\s*$',
     r'\1[REDACTED]'),
]

for pattern, repl in patterns:
    text = re.sub(pattern, repl, text, flags=re.DOTALL)

env_names = [
    "BITVAVO_API_KEY",
    "BITVAVO_API_SECRET",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "INFLUXDB_TOKEN",
    "INFLUX_TOKEN",
    "LOXONE_USER",
    "LOXONE_PASSWORD",
    "SMTP_PASSWORD",
    "MAIL_PASSWORD",
]
for name in env_names:
    text = re.sub(
        rf'(?m)^({re.escape(name)}\s*=\s*).*$',
        rf'\1[REDACTED]',
        text
    )

if text != original:
    path.write_text(text, encoding="utf-8")
PY
}

find "$STAGE_DIR" -type f | while read -r file; do
  if is_text_file "$file"; then
    redact_file "$file"
  fi
done

echo "==> Creating backup manifest..."
cat > "$STAGE_DIR/BACKUP_INFO.md" <<EOF
# Sanitized Backup Info

Created: $(date -Iseconds)
Original project: $PROJECT_DIR
Sanitized backup: $(basename "$ZIP_PATH")

## Notes
- Sensitive files like .env, keys, certs, git history, caches, logs, db files and venv folders were removed.
- Text-like files were scanned and likely secrets were redacted.
- Review before sharing if you want maximum certainty.
EOF

echo "==> Creating zip..."
cd "$WORK_DIR"
zip -r "$ZIP_PATH" "$PROJECT_NAME" > /dev/null

echo "==> Done"
echo "Backup created at:"
echo "$ZIP_PATH"

rm -rf "$WORK_DIR"
echo "==> Temporary staging removed"
